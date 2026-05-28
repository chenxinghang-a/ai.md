#!/usr/bin/env python
"""Smart splitter: auto-detects class boundaries by finding @dataclass/class patterns."""
import os, re, sys

SRC = r'C:\Users\cxx\.workbuddy\skills\ai-staff\scripts\ai_staff.py'
DST = r'C:\Users\cxx\WorkBuddy\Claw\ai_staff_v4'

with open(SRC, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Source: {len(lines)} lines")

# Find all class/function top-level definitions with their line numbers
defs = []  # (line_no_1indexed, name, type)
for i, line in enumerate(lines):
    stripped = line.strip()
    m = re.match(r'^class\s+(\w+)', stripped)
    if m and not line[0].isspace():
        defs.append((i+1, m.group(1), 'class'))
        continue
    m = re.match(r'^def\s+(\w+)', stripped)
    if m and not line[0].isspace() and not line[0] == '':
        defs.append((i+1, m.group(1), 'def'))

print(f"\nFound {len(defs)} top-level definitions:")
for ln, name, typ in defs:
    print(f"  L{ln:4d} {typ:5s} {name}")

# Define modules by START class name (inclusive) and END class name (exclusive)
# Format: (output_path, start_class_name, end_class_name_or_None)
MODULE_DEFS = [
    ('core/events.py',         'EventType',          'BudgetConfig'),
    ('core/budget.py',         'BudgetConfig',       'ExpertConfig'),
    ('core/memory.py',         'MemorySystem',       'TaskStrategy'),
    ('core/validation.py',     'ValidationResult',   'AgentState'),
    ('core/checkpoint.py',     'CheckpointManager',  'LLMClient'),
    ('experts/registry.py',    'ExpertConfig',       'MemorySystem'),
    ('experts/classifier.py',  'TaskStrategy',       'ValidationResult'),
    ('agents/types.py',        'AgentState',         'BaseAgent'),
    ('agents/base.py',         'BaseAgent',          'CoTAgent'),
    ('agents/cot.py',          'CoTAgent',           'ExecutorAgent'),
    ('agents/executor.py',     'ExecutorAgent',      'ReviewAgent'),
    ('agents/reviewer.py',     'ReviewAgent',        'MemoryAgent'),
    ('agents/memory_agent.py', 'MemoryAgent',        'WorkflowStep'),
    ('agents/workflow.py',     'WorkflowStep',       'CheckpointManager'),
    ('backends/client.py',     'LLMClient',          'BackendProfile'),
    ('backends/profile.py',    'BackendProfile',     'ModelRouter'),
    ('backends/router.py',     'ModelRouter',        'FallbackManager'),
    ('backends/fallback.py',   'FallbackManager',    'MultiLLMClient'),
    ('backends/multi_client.py','MultiLLMClient',    'AIStaff'),
    ('main_mod/staff.py',      'AIStaff',            'ImprovementRecord'),
    ('self_improve/types.py',  'ImprovementRecord',  'SelfImprovementEngine'),
    ('self_improve/engine.py', 'SelfImprovementEngine', 'WorkflowNodeV2'),
    ('workflow_v2/types.py',   'WorkflowNodeV2',     'WorkflowGeneratorV2'),
    ('workflow_v2/generator.py','WorkflowGeneratorV2', 'WorkflowExecutorV2'),
    ('workflow_v2/executor.py', 'WorkflowExecutorV2', None),  # rest of file
]

# Build lookup: class_name -> line_number
class_lines = {name: ln for ln, name, typ in defs}

HEADER = '''from __future__ import annotations
import sys, os, json, time, io, re, hashlib, argparse
from collections import deque
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import httpx

'''

if sys.platform == 'win32':
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

ok = 0
for mod_path, start_cls, end_cls in MODULE_DEFS:
    out = os.path.join(DST, *mod_path.split('/'))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    
    start_ln = class_lines.get(start_cls)
    end_ln = class_lines.get(end_cls, len(lines)) if end_cls else len(lines)
    
    if start_ln is None:
        print(f"  SKIP {mod_path}: start class '{start_cls}' not found")
        continue
    if end_ln <= start_ln:
        print(f"  WARN {mod_path}: L{start_ln}-L{end_ln} invalid range")
        continue
    
    code = ''.join(lines[start_ln-1:end_ln-1])  # up to but NOT including next section
    
    with open(out, 'w', encoding='utf-8') as f:
        f.write(HEADER + code)
    
    ok += 1
    print(f"  OK {mod_path:<30s} {start_cls:<25s} -> L{start_ln:4d}-L{end_ln-1:4d} ({end_ln-start_ln:3d} lines)")

print(f"\nDone! {ok} modules extracted")
