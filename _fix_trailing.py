#!/usr/bin/env python
"""Post-processor: strip orphaned trailing section headers from extracted modules."""
import os, re, sys

if sys.platform == 'win32':
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

BASE = r'C:\Users\cxx\WorkBuddy\Claw\ai_staff_v4'

# Patterns that indicate start of next section (should be stripped from end)
SECTION_HEADER_PATTERNS = [
    re.compile(r'^# \u2500{10,}'),       # ════════ section divider
    re.compile(r'^# \w.*\u2500{3,}'),     # # SECTION NAME ———
    re.compile(r'^@\w+$'),                # Orphaned @dataclass / @property etc at end of file
]

fixed = 0
for root, dirs, files in os.walk(BASE):
    for f in files:
        if not f.endswith('.py') or f == '__init__.py':
            continue
        
        fp = os.path.join(root, f)
        with open(fp, 'r', encoding='utf-8') as fh:
            lines = fh.readlines()
        
        if len(lines) < 5:
            continue
        
        # Find where to cut: last meaningful line before a section header
        cut = len(lines)
        for i in range(len(lines) - 1, max(len(lines) - 20, -1), -1):
            stripped = lines[i].strip()
            is_blank = stripped == ''
            is_section = any(p.match(stripped) for p in SECTION_HEADER_PATTERNS)
            is_comment_only = stripped.startswith('#') and not is_section
            
            if is_section:
                cut = i  # Cut here (exclude this line and everything after)
                break
            elif i < len(lines) - 3 and is_comment_only:
                # Check if this blank+comment block precedes an @decorator or class
                pass  # Keep going back
        
        if cut < len(lines):
            original = len(lines)
            lines = lines[:cut]
            # Also strip trailing blank lines
            while lines and lines[-1].strip() == '':
                lines.pop()
            with open(fp, 'w', encoding='utf-8') as fh:
                fh.writelines(lines)
            rel = os.path.relpath(fp, BASE)
            print(f'  FIXED {rel}: {original} -> {len(lines)} lines (-{original-len(lines)})')
            fixed += 1

print(f'\nDone! Fixed {fixed} modules')
