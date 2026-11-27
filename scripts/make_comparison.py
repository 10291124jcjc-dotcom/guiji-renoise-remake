"""Render an original and its AI remake side by side in a shareable MP4."""

import argparse
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory


FPS = 30
MAX_PANEL_EDGE = 1280


def probe(path):
    info = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(path),
    ]))
    video = next((stream for stream in info["streams"]
                  if stream["codec_type"] == "video"
                  and not stream.get("disposition", {}).get("attached_pic")), None)
    if video is None:
        raise ValueError(f"找不到视频画面：{path}")
    audio = next((stream for stream in info["streams"]
                  if stream["codec_type"] == "audio"), None)
    length = metadata_number(video.get("duration")) or metadata_number(info["format"].get("duration"))
    if length <= 0:
        raise ValueError(f"读不到视频时长：{path}")
    ratio = Fraction(video["width"], video["height"])
    sar = video.get("sample_aspect_ratio", "1:1")
    if sar not in ("N/A", "0:1", "0:0"):
        ratio *= Fraction(sar.replace(":", "/"))
    rotation = next((item["rotation"] for item in video.get("side_data_list", [])
                     if "rotation" in item), video.get("tags", {}).get("rotate", 0))
    if abs(round(float(rotation) / 90)) % 2:
        ratio = 1 / ratio
    return video, audio, length, ratio


def metadata_number(value):
    return float(value) if value not in (None, "N/A", "") else 0.0


def find_font(explicit):
    if explicit:
        return explicit.resolve(strict=True)
    windows_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    candidates = (
        windows_fonts / "msyhbd.ttc",
        windows_fonts / "msyh.ttc",
        windows_fonts / "simhei.ttf",
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
    )
    for path in candidates:
        if path.is_file():
            return path
    raise ValueError("找不到可用中文字体，请通过 --font 指定字体文件。")


def fit(ratio, width, height):
    if ratio >= Fraction(width, height):
        return width, max(2, 2 * round(width / ratio / 2))
    return max(2, 2 * round(height * ratio / 2)), height


def render(args, output):
    original, remake = (path.resolve(strict=True) for path in (args.original, args.ai))
    sources = [probe(original), probe(remake)]
    common_length = min(source[2] for source in sources)
    if args.duration is None:
        frames = math.floor(common_length * FPS + 0.0001)
    else:
        if not math.isfinite(args.duration) or not 0 < args.duration <= common_length + 1 / FPS + 0.0001:
            raise ValueError("指定时长须为正数，且最多比两条视频的共同长度多一帧。")
        frames = round(args.duration * FPS)
    if frames < 1:
        raise ValueError("两条视频没有足够的共同播放时长。")
    duration = f"{frames / FPS:.9f}"
    width, height = fit(sources[0][3], MAX_PANEL_EDGE, MAX_PANEL_EDGE)
    font = find_font(args.font)

    with TemporaryDirectory(prefix="video-comparison-") as temporary:
        stage = Path(temporary)
        font_name = "label-font" + font.suffix
        shutil.copyfile(font, stage / font_name)
        filters = []
        for index, (label, source) in enumerate(zip(("原视频", "AI"), sources)):
            label_name = f"label-{index}.txt"
            (stage / label_name).write_text(label, encoding="utf-8")
            content_width, content_height = fit(source[3], width, height)
            filters.append(
                f"[{index}:{source[0]['index']}]setpts=PTS-STARTPTS,fps={FPS},"
                f"tpad=stop_mode=clone:stop=1,trim=end_frame={frames},"
                f"scale={content_width}:{content_height}:flags=lanczos,setsar=1,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
                f"drawtext=fontfile={font_name}:textfile={label_name}:fontsize=34:fontcolor=white:"
                f"box=1:boxcolor=black@0.80:boxborderw=10:x=40:y=37[panel{index}]"
            )
        filters.append(
            f"[panel0][panel1]hstack=inputs=2:shortest=1,"
            f"drawbox=x={width - 1}:y=0:w=2:h=ih:color=white@0.86:t=fill[video]"
        )
        maps = ["-map", "[video]"]
        if args.audio != "none":
            index = 0 if args.audio == "original" else 1
            video, audio, _, _ = sources[index]
            if audio:
                offset = metadata_number(audio.get("start_time")) - metadata_number(video.get("start_time"))
                filters.append(
                    f"[{index}:{audio['index']}]asetpts=PTS-STARTPTS+({offset:.9f})/TB,"
                    f"aresample=async=1:first_pts=0,apad,atrim=duration={duration}[audio]"
                )
                maps.extend(["-map", "[audio]", "-c:a", "aac", "-b:a", "160k"])
        rendered = stage / "comparison.mp4"
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
            "-i", str(original), "-i", str(remake), "-filter_complex_threads", "1",
            "-filter_complex", ";".join(filters), *maps,
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", "-t", duration, str(rendered),
        ], cwd=stage, check=True)
        with rendered.open("rb") as source:
            destination = output.open("xb")
            try:
                with destination:
                    shutil.copyfileobj(source, destination)
            except OSError:
                output.unlink()
                raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path, help="左侧原视频")
    parser.add_argument("ai", type=Path, help="右侧 AI 复刻视频")
    parser.add_argument("output", type=Path, help="新的 MP4 文件路径")
    parser.add_argument("--duration", type=float, help="指定输出秒数，默认取两条视频的共同长度")
    parser.add_argument("--audio", choices=("original", "ai", "none"), default="original")
    parser.add_argument("--font", type=Path, help="可选的中文字体文件")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.suffix.lower() != ".mp4" or output.exists():
        parser.error("输出必须为尚未存在的 .mp4 文件。")
    try:
        render(args, output)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"无法生成对照视频：{error}\n")
    print(output)


if __name__ == "__main__":
    main()
