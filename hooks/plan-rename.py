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

    if not path.exists() or os.path.islink(str(path)):
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

    # Try to keep original path accessible so Claude can still reference it.
    # symlink requires Developer Mode on Windows; fall back to hard link; silently skip if both fail.
    try:
        os.symlink(new_path.name, str(path))
    except (OSError, NotImplementedError):
        try:
            os.link(str(new_path), str(path))
        except (OSError, NotImplementedError):
            pass

    return new_path


def handle_post_tool_use(data):
    """Handle PostToolUse(Write) event - rename the specific file just written."""
    if data.get('tool_name') != 'Write':
        return

    tool_input = data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')
    content = tool_input.get('content', '')

    path = Path(file_path)
    if '.plans' not in path.parts:
        return

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
