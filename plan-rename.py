#!/usr/bin/env python3
"""
PostToolUse hook: rename random plan file names to reflect plan content.

When Claude writes a plan to .plans/random-name.md, this hook:
1. Extracts the H1 title from the plan content
2. Converts it to a kebab-case filename
3. Renames the file
4. Creates a symlink at the original path so Claude can still reference it
"""
import json, sys, os, re
from datetime import date

data = json.load(sys.stdin)

if data.get('tool_name') != 'Write':
    sys.exit(0)

tool_input = data.get('tool_input', {})
file_path = tool_input.get('file_path', '')
content = tool_input.get('content', '')

# Must be in a .plans/ directory (normalize Windows backslashes)
normalized = file_path.replace('\\', '/')
if '/.plans/' not in normalized:
    sys.exit(0)

basename = os.path.basename(file_path)

# Must match random name pattern: exactly 3 lowercase alpha word groups
# e.g. fizzy-giggling-cake.md, composed-seeking-sonnet.md
if not re.match(r'^[a-z]+(-[a-z]+){2}\.md$', basename):
    sys.exit(0)

# Skip if already a symlink (renamed in a previous Write call this session)
if os.path.islink(file_path):
    sys.exit(0)

if not os.path.exists(file_path):
    sys.exit(0)

# Extract first H1 heading from content
title = None
for line in content.split('\n'):
    if line.startswith('# '):
        title = line[2:].strip()
        break

if not title:
    sys.exit(0)

# Build filename: title + date suffix
# Preserve Chinese and other Unicode characters, strip only filesystem-unsafe chars
title_part = re.sub(r'[\s/\\:*?"<>|]+', '-', title)[:50].strip('-')
today = date.today().strftime('%Y%m%d')
new_name = f'{title_part}-{today}'

if not new_name or len(new_name) < 2:
    sys.exit(0)

dir_path = os.path.dirname(file_path)

# Always include version number, increment on conflict
version = 1
while os.path.exists(os.path.join(dir_path, f'{new_name}-v{version}.md')):
    version += 1
new_path = os.path.join(dir_path, f'{new_name}-v{version}.md')

if file_path == new_path:
    sys.exit(0)

os.rename(file_path, new_path)
# Symlink original path → renamed file so Claude can still reference it
os.symlink(os.path.basename(new_path), file_path)
