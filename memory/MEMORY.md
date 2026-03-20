# Claude Code 全局记忆

## 文档解析工作流（/parse skill）

**已配置（2026-03-13）**：
- Skill: `C:\Users\Administrator\.claude\skills\parse\SKILL.md`
- MineRU 客户端: `C:\Users\Administrator\.claude\skills\parse\scripts\mineru_client.py`
- `MINERU_API_KEY` 已写入 `settings.json` env 字段
- PaddleOCR MCP 已加入 `.codex\config.toml`
- 项目级路由规则: `E:\QvQ\OneDrive - 2077\data\AI\project\文档解析\CLAUDE.md`

**路由决策**：
| 类型 | 方法 |
|------|------|
| .docx | pandoc |
| .xlsx | pandas |
| 文字型 PDF（首页>50字符） | pdfplumber |
| 扫描型 PDF | `mineru_client.py --model vlm` |
| 单图 | PaddleOCR MCP `ocr_pdf` |
| 多图/.pptx | `mineru_client.py --model pipeline` |

## 关键路径

- settings.json: `C:\Users\Administrator\.claude\settings.json`
- PaddleOCR server: `C:\Users\Administrator\.claude\mcp-servers\paddleocr\server.py`
- Codex config: `C:\Users\Administrator\.codex\config.toml`

## 用户偏好

- 语言：简体中文
- **思维链（thinking）必须全程使用中文**，不得使用英文
- OS：Windows 11，Shell：bash（Unix 路径语法）
- 不新增 MineRU MCP / Excel MCP（节省常驻 token 开销）
