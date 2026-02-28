# Claude Code Plan 文件语义命名

## 问题背景

Claude Code 进入 plan 模式时，会自动生成随机三词组合作为计划文件名，例如：

```
fizzy-giggling-cake.md
composed-seeking-sonnet.md
eager-launching-kernighan.md
```

这些名字对人毫无语义，积累多个计划后无法分辨内容，难以管理。

---

## 为什么不能直接配置命名规则

**时序问题是根本原因：**

```
Claude Code 启动 plan 模式
        ↓
系统先生成随机文件名（内部行为）
        ↓
把完整路径写入 system message 告诉 Claude：
"请把计划写到 .plans/fizzy-giggling-cake.md"
        ↓
Claude 才开始理解需求、写计划内容
```

文件名在 Claude 还不知道任务是什么时就已经确定，所以无法根据任务内容命名。`settings.json` 只提供 `plansDirectory`（控制目录），没有命名模板配置项。这是 Claude Code 的已知缺陷，对应 GitHub issue [#12619](https://github.com/anthropics/claude-code/issues/12619) 和 [#18596](https://github.com/anthropics/claude-code/issues/18596)，短期内不会修复。

---

## 解决思路：PostToolUse Hook

Claude 写入计划文件时会调用 `Write` 工具。Claude Code 的 hook 机制允许在工具调用完成后执行自定义脚本，并通过 stdin 传入完整的工具调用信息（包括文件路径和写入内容）。

**利用这个时机：**

1. Hook 从 stdin 的 `tool_input.content` 中直接读取刚写入的内容
2. 提取第一个 H1 标题（`# 标题`）
3. 以标题 + 日期为新文件名，用 `os.rename()` 重命名
4. 在原随机路径创建软链接，保证 Claude 后续引用不报错

**关键优势：零 token 消耗** —— 整个过程是纯本地 Python 脚本，不调用任何 LLM 或网络请求。`os.rename()` 是 OS 级目录项修改，等同于 `mv`，不复制文件内容。

---

## 文件结构

```
~/.claude/
├── hooks/
│   └── plan-rename.py       # PostToolUse hook 脚本
└── settings.json            # 含 plansDirectory 和 hook 注册
```

---

## settings.json 关键配置

```json
{
  "plansDirectory": ".plans",
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/plan-rename.py"
          }
        ]
      }
    ]
  }
}
```

- `plansDirectory: ".plans"` — 计划文件存入项目根目录的 `.plans/` 子目录，不污染项目根目录
- `PostToolUse` + `matcher: "Write"` — 仅在 Write 工具调用后触发

---

## Hook 脚本逻辑

```python
# 1. 过滤条件（不符合则直接退出）
- tool_name 必须是 "Write"
- file_path 必须包含 "/.plans/"
- 文件名必须匹配随机三词模式：^[a-z]+(-[a-z]+){2}\.md$
- 文件路径不能是软链接（避免重复处理）

# 2. 提取标题
从 content 逐行扫描，找第一个以 "# " 开头的行

# 3. 构造新文件名
去除文件系统不安全字符（/\:*?"<>|），保留中文等 Unicode 字符
格式：{标题}-{YYYYMMDD}.md
例如：实现用户认证模块-20260223.md

# 4. 冲突处理
若目标文件已存在，自动追加 -2、-3 …

# 5. 重命名 + 软链接
os.rename(原路径, 新路径)
os.symlink(新文件名, 原路径)   ← 软链接保证 Claude 引用不断
```

---

## 命名效果对比

| 之前 | 之后 |
|------|------|
| `fizzy-giggling-cake.md` | `实现用户认证模块-20260223.md` |
| `composed-seeking-sonnet.md` | `修复支付流程-20260223.md` |
| `eager-launching-kernighan.md` | `重构数据库层-20260201.md` |

---

## 边界情况测试

| 用例 | 行为 |
|------|------|
| 中文标题 | 保留中文，追加日期 |
| 英文标题 | 保留原大小写，空格转连字符 |
| 无 H1 标题 | 保留原随机名，不触发重命名 |
| 非 `.plans/` 路径 | 不触发 |
| 同天同名冲突 | 自动加 `-2`、`-3` 后缀 |

---

## 注意事项

- 建议将 `.plans` 加入项目的 `.gitignore`，避免计划文件进入版本库
- 访达中查看 `.plans` 隐藏目录：`Command + Shift + .`
