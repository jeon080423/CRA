import ast
import sys

def check_file(path):
    print(f"--- Checking {path} ---")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content, filename=path)
        print(f"  ✅ {path}: Syntax OK")
        return True
    except SyntaxError as e:
        print(f"  ❌ {path}: Syntax Error: {e.msg}")
        print(f"     Line: {e.lineno}, Offset: {e.offset}")
        if e.text:
            print(f"     Context: {e.text.strip()}")
            # Show position
            if e.offset:
                print(f"              {' ' * (e.offset - 1)}^")
        return False
    except Exception as e:
        print(f"  ❌ {path}: Unexpected error: {e}")
        return False

# Specifically for app.py and matcher.py
results = [check_file('app.py'), check_file('utils/matcher.py')]

if all(results):
    print("\nSUCCESS: All files passed syntax check.")
    sys.exit(0)
else:
    print("\nFAILURE: Some files have syntax errors.")
    sys.exit(1)
