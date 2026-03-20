#!/usr/bin/env python3
"""
PreToolUse hook: 在 plan 文件被覆写前自动存档（递增 -v{N} 版本号）。

触发条件：Write 工具写入 .plans/ 目录下的文件
存档条件：目标文件已存在且有实质内容（≥50字符）且新旧内容不同

版本命名：与 plan-rename.py 的 -v{N} 后缀体系统一
  计划：标号重排-20260316-v1.md   ← 第1版存档
  计划：标号重排-20260316-v2.md   ← 第2版存档
  计划：标号重排-20260316-v3.md   ← 第3版存档（当前版本，即将被覆写）

工作流：
  1. 解析当前文件的 base（去掉 -v{N}）
  2. 扫描同目录下同 base 的最大版本号
  3. 将当前内容存档为 {base}-v{max+1}.md
  4. 返回 allow，让 Write 覆写原文件
"""
import json, sys, io, os, re, shutil
from pathlib import Path
from datetime import datetime

# Windows stdin/stdout 强制 UTF-8
for stream_name in ('stdin', 'stdout', 'stderr'):
    stream = getattr(sys, stream_name)
    if hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8')
    elif hasattr(stream, 'buffer'):
        setattr(sys, stream_name, io.TextIOWrapper(stream.buffer, encoding='utf-8'))

ALLOW = json.dumps({"decision": "allow"})


def get_h1(text):
    """提取 markdown 中第一个 H1 标题。"""
    if not text:
        return None
    for line in text.split('\n'):
        if line.startswith('# '):
            return line[2:].strip()
    return None


def resolve_symlink(p):
    """解析符号链接，返回实际文件路径。"""
    p = Path(p)
    try:
        if os.path.islink(str(p)):
            target = Path(os.readlink(str(p)))
            if not target.is_absolute():
                target = p.parent / target
            return target
    except Exception:
        pass
    return p


def is_plans_file(file_path):
    """判断路径是否在 .plans/ 目录下。"""
    normalized = file_path.replace('\\', '/')
    return '/.plans/' in normalized


def split_base_version(stem):
    """
    从文件名中分离 base 和版本号。
      '计划：标号重排-20260316-v1' → ('计划：标号重排-20260316', 1)
      '计划：标号重排-20260316'    → ('计划：标号重排-20260316', 0)
    """
    m = re.match(r'^(.+)-v(\d+)$', stem)
    if m:
        return m.group(1), int(m.group(2))
    return stem, 0


def find_next_version(actual_path):
    """
    扫描目录中同 base 的所有 -v{N}.md 文件，返回下一个版本号和对应路径。
    """
    base, current_v = split_base_version(actual_path.stem)
    parent = actual_path.parent

    # 找出同 base 下的最大版本号
    max_v = current_v
    pattern = re.compile(rf'^{re.escape(base)}-v(\d+)\.md$')
    try:
        for f in parent.iterdir():
            m = pattern.match(f.name)
            if m:
                max_v = max(max_v, int(m.group(1)))
    except Exception:
        pass

    next_v = max_v + 1
    return next_v, parent / f"{base}-v{next_v}.md"


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        print(ALLOW)
        return

    tool_name = data.get('tool_name', '')
    tool_input = data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')
    new_content = tool_input.get('content', '')

    # 只拦截 Write 到 .plans/ 的操作
    if tool_name != 'Write' or not is_plans_file(file_path):
        print(ALLOW)
        return

    # 解析符号链接，获取实际文件路径
    actual_path = resolve_symlink(file_path)

    # 目标文件不存在 → 首次写入，无需存档
    if not actual_path.exists():
        print(ALLOW)
        return

    # 读取现有内容
    try:
        existing_content = actual_path.read_text(encoding='utf-8')
    except Exception:
        print(ALLOW)
        return

    # 现有内容太短（<50字符）→ 无实质内容，无需存档
    if len(existing_content.strip()) < 50:
        print(ALLOW)
        return

    # 新旧内容完全相同 → 无变化，无需存档
    if existing_content.strip() == new_content.strip():
        print(ALLOW)
        return

    # ✅ 存档：递增版本号
    next_v, archive_path = find_next_version(actual_path)

    existing_h1 = get_h1(existing_content)
    new_h1 = get_h1(new_content)
    same_plan = (existing_h1 and new_h1 and existing_h1 == new_h1)

    try:
        shutil.copy2(str(actual_path), str(archive_path))
        # 写入日志
        log_path = actual_path.parent / '.plan-archive.log'
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        reason = "迭代更新" if same_plan else "不同plan覆写"
        with open(str(log_path), 'a', encoding='utf-8') as log:
            log.write(f"[{timestamp}] {actual_path.name} → {archive_path.name} ({reason})\n")
    except Exception as e:
        try:
            log_path = actual_path.parent / '.plan-archive.log'
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            with open(str(log_path), 'a', encoding='utf-8') as log:
                log.write(f"[{timestamp}] FAILED: {actual_path.name}: {e}\n")
        except Exception:
            pass

    print(ALLOW)


if __name__ == '__main__':
    main()
