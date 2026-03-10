#!/usr/bin/env python3
"""
Plan rename hook - handles both PostToolUse(Write) and Stop events.

When Claude writes a plan to .plans/random-name.md, this hook:
1. Extracts the H1 title from the plan content
2. Converts it to a kebab-case filename with date + version suffix
3. Renames the file
4. Tries to create a link at the original path so Claude can still reference it

Triggered by:
- PostToolUse(Write): when Claude explicitly writes a plan file
- Stop: scans cwd/.plans/ for any unprocessed random-named files
"""
import json, sys, os, re
from pathlib import Path
from datetime import date


def rename_plan_file(path, content=None):
    """Rename a single plan file. Returns new path or None if skipped."""
    path = Path(path)

    # If path is a symlink, unlink it so we treat the content as a fresh file
    if os.path.islink(str(path)):
        os.unlink(str(path))
        return None

    if not path.exists():
        return None

    basename = path.name

    # Must match random name pattern: exactly 3 lowercase alpha word groups
    # e.g. fizzy-giggling-cake.md, composed-seeking-sonnet.md
    if not re.match(r'^[a-z]+(-[a-z]+){2}\.md$', basename):
        return None

    # Read content if not provided
    if content is None:
        try:
            content = path.read_text(encoding='utf-8')
        except Exception:
            return None

    # Extract first H1 heading
    title = None
    for line in content.split('\n'):
        if line.startswith('# '):
            title = line[2:].strip()
            break

    if not title:
        return None

    # Build filename: title + date + version
    title_part = re.sub(r'[\s/\\:*?"<>|]+', '-', title)[:50].strip('-')
    today = date.today().strftime('%Y%m%d')
    base_name = f'{title_part}-{today}'

    if not base_name or len(base_name) < 2:
        return None

    dir_path = path.parent

    version = 1
    while (dir_path / f'{base_name}-v{version}.md').exists():
        version += 1
    new_path = dir_path / f'{base_name}-v{version}.md'

    if path.resolve() == new_path.resolve():
        return None

    os.rename(str(path), str(new_path))
    return new_path


def handle_post_tool_use(data):
    """Handle PostToolUse(Write|Edit) event - rename the specific file just written/edited."""
    tool_name = data.get('tool_name', '')
    if tool_name not in ('Write', 'Edit'):
        return

    tool_input = data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    path = Path(file_path)
    if '.plans' not in path.parts:
        return

    # For Write: content is available directly; for Edit: read from disk after modification
    if tool_name == 'Write':
        content = tool_input.get('content', '')
    else:
        content = None  # rename_plan_file will read from disk

    rename_plan_file(file_path, content)


def handle_stop():
    """Handle Stop event - scan cwd/.plans/ for any unprocessed random-named files."""
    cwd = Path(os.getcwd())
    plans_dir = cwd / '.plans'

    if not plans_dir.exists():
        return

    for md_file in sorted(plans_dir.glob('*.md')):
        rename_plan_file(md_file)


# Main
try:
    data = json.load(sys.stdin)
except Exception:
    data = {}

# Distinguish event type by data shape:
# PostToolUse data has 'tool_name'; Stop data has 'session_id'/'transcript_path'
if 'tool_name' in data:
    handle_post_tool_use(data)
else:
    handle_stop()
