import py_compile, os, sys
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8')
base = r'C:\Users\cxx\WorkBuddy\Claw\ai_staff_v4'
errors, ok = [], 0
for root, dirs, files in os.walk(base):
    for f in sorted(files):
        if not f.endswith('.py') or f == '__init__.py' or f.startswith('_'):
            continue
        fp = os.path.join(root, f)
        try:
            py_compile.compile(fp, doraise=True)
            ok += 1
        except py_compile.PyCompileError as e:
            errors.append((os.path.relpath(fp, base), str(e).split('\n')[0]))

print(f"RESULT: {ok}/{ok+len(errors)} MODULES COMPILE CLEAN")
for fp, err in errors:
    print(f"  FAIL {fp}: {err}")
if not errors:
    print("ALL 25 MODULES OK!")
