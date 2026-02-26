# Claude Code 配置备份仓库

本仓库备份 Claude Code 的核心配置文件，支持跨设备迁移和版本管理。

## 仓库内容

| 文件/目录 | 说明 |
|-----------|------|
| `settings.json` | 主配置（模型、权限、MCP 服务器） |
| `settings.local.json` | 本地扩展权限规则 |
| `CLAUDE.md` | 全局用户指令（专利律师角色定义） |
| `config.json` | Claude Code 附加配置 |
| `agents/` | 自定义代理（patent-document-expert、patent-examiner-agent） |
| `hooks/` | 钩子脚本（claudeception-activator） |
| `mcp-servers/` | MCP 服务器实现（paddleocr/server.py） |

> **skills/** 单独管理，见 → https://github.com/0okay/Ookay-skills

---

## 新电脑恢复

### Windows

```powershell
# 一行克隆到正确位置
git clone https://github.com/0okay/claude-config.git $env:USERPROFILE\.claude
```

### macOS

```bash
git clone https://github.com/0okay/claude-config.git ~/.claude

# 赋予 hooks 执行权限
chmod +x ~/.claude/hooks/*.sh
```

### 恢复后必做

```bash
# 1. 安装 Claude Code（如尚未安装）
npm install -g @anthropic-ai/claude-code

# 2. 重新登录（凭证不跨账号，需重新认证）
claude

# 3. 克隆 skills 仓库
git clone https://github.com/0okay/Ookay-skills.git ~/.claude/skills   # macOS
git clone https://github.com/0okay/Ookay-skills.git $env:USERPROFILE\.claude\skills  # Windows

# 4. 重新安装 MCP 依赖（PaddleOCR）
pip install paddlepaddle paddleocr

# 5. 验证
claude --version
```

---

## 日常维护

在 `.claude` 目录执行：

```powershell
git add -A
git commit -m "update: 更新配置"
git push
```

---

## ZIP 便携备份

如需生成可离线使用的 ZIP 备份（含 `.cc-mirror`、`skills` 等完整内容）：

```powershell
# 运行桌面备份脚本（Windows）
.\backup-claude-config.ps1

# 含命令历史
.\backup-claude-config.ps1 -IncludeHistory
```

ZIP 文件生成于桌面，约 70–80 MB。

---

## 注意事项

- `.credentials.json` **未纳入版本控制**，新电脑需重新运行 `claude` 登录
- `skills/` **未纳入**本仓库，通过 [Ookay-skills](https://github.com/0okay/Ookay-skills) 单独管理
- macOS 恢复后需将 `settings.json` 中的 Windows 路径替换为 Mac 路径（或使用 `restore-macos.sh` 自动处理）
