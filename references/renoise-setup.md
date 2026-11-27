# 安装和连接 Renoise MCP

已有 Renoise 工具时，先调用 `get_account` 和 `list_models` 验证。能读到账户和模型即可使用当前连接。

## Codex 桌面端安装官方插件

1. 在 Codex 对话里发送 Renoise 官方安装指令。

   ```text
   Install plugin from the repo https://github.com/renoise-ai/renoise-plugins-official
   ```

2. 安装后重启 Codex。在 **Plugins** 中打开 Renoise 并连接账号。登录和 OAuth 授权由账号持有人在浏览器里完成。
3. 新开会话，调用 `get_account` 和 `list_models` 检查连接。生成前另外核对余额与报价。

[Renoise 官方安装步骤](https://renoise.ai/docs/codex) · [官方插件的 Codex 安装说明](https://github.com/renoise-ai/renoise-plugins-official/blob/main/README.md#codex--chatgpt-desktop)

## 直接连接远程 MCP

在 Codex 桌面端进入 **Settings → MCP servers**，添加名为 `renoise` 的 Streamable HTTP 服务。填入 `https://renoise.ai/api/public/mcp`，保存后重启并选择认证。

用 Codex CLI 时，在自己的终端运行下列命令。如果添加服务时已经完成浏览器授权，就可以直接检查连接。

```powershell
codex mcp add renoise --url https://renoise.ai/api/public/mcp
codex mcp login renoise
codex mcp list
```

Renoise 使用浏览器 OAuth。账号凭证留在授权页面。配置就绪后，在要使用的项目里新开会话，再用 `get_account` 和 `list_models` 验证。

[Renoise 官方 MCP 清单](https://github.com/renoise-ai/renoise-plugins-official/blob/main/mcp.json) · [Codex 桌面 MCP 配置](https://learn.chatgpt.com/docs/extend/mcp?surface=desktop) · [Codex CLI MCP 配置](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
