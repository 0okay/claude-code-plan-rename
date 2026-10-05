#!/usr/bin/env python3
"""
PostToolUse hook: rename random plan file names to reflect plan content.

When Claude writes a plan to .plans/random-name.md, this hook:
1. Extracts the H1 title from the plan content
2. Converts it to a kebab-case filename with date + version suffix
3. Renames the file
4. Tries to create a link at the original path so Claude can still reference it
"""
import json, sys, os, re
from pathlib import Path
from datetime import date

data = json.load(sys.stdin)

if data.get('tool_name') != 'Write':
    sys.exit(0)

tool_input = data.get('tool_input', {})
file_path = tool_input.get('file_path', '')
content = tool_input.get('content', '')

# Must be in a .plans/ directory
# Use Path.parts for cross-platform robustness (handles C:\... and relative paths)
path = Path(file_path)
if '.plans' not in path.parts:
    sys.exit(0)

basename = path.name

# Must match random name pattern: exactly 3 lowercase alpha word groups
# e.g. fizzy-giggling-cake.md, composed-seeking-sonnet.md
if not re.match(r'^[a-z]+(-[a-z]+){2}\.md$', basename):
    sys.exit(0)

# A symlink already identifies a renamed plan.
if os.path.islink(file_path):
    sys.exit(0)

if not os.path.exists(file_path):
    sys.exit(0)

# A hard-link fallback is not a symlink. Recognize an existing semantic
# alias by file identity, not just link count (unrelated links may exist).
for sibling in path.parent.glob('*-v*.md'):
    if sibling == path or not re.search(r'-v\d+\.md$', sibling.name):
        continue
    try:
        if path.samefile(sibling):
            sys.exit(0)
    except OSError:
        continue

# Extract first H1 heading from content
title = None
for line in content.split('\n'):
    if line.startswith('# '):
        title = line[2:].strip()
        break

if not title:
    sys.exit(0)

# Build filename: title + date + version
# Preserve Chinese and other Unicode, strip only filesystem-unsafe chars
title_part = re.sub(r'[\s/\\:*?"<>|]+', '-', title)[:50].strip('-')
today = date.today().strftime('%Y%m%d')
base_name = f'{title_part}-{today}'

if not base_name or len(base_name) < 2:
    sys.exit(0)

dir_path = path.parent

# Always include version number, increment on conflict
version = 1
while (dir_path / f'{base_name}-v{version}.md').exists():
    version += 1
new_path = dir_path / f'{base_name}-v{version}.md'

if path.resolve() == new_path.resolve():
    sys.exit(0)

os.rename(file_path, new_path)

# Try to keep original path accessible so Claude can still reference it.
# symlink requires Developer Mode on Windows; fall back to hard link; silently skip if both fail.
try:
    os.symlink(new_path.name, file_path)
except (OSError, NotImplementedError):
    try:
        os.link(new_path, file_path)
    except (OSError, NotImplementedError):
        pass
