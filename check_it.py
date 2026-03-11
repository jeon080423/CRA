import ast
import traceback

files = ['app.py', 'utils/matcher.py', 'api/fss_api.py', 'api/nps_api.py']

for f_path in files:
    print(f"Checking {f_path}...")
    try:
        with open(f_path, 'r', encoding='utf-8') as f:
            content = f.read()
            ast.parse(content)
        print(f"  ✅ {f_path}: Syntax OK")
    except SyntaxError as e:
        print(f"  ❌ {f_path}: Syntax Error: {e.msg}")
        print(f"     Line: {e.lineno}, Offset: {e.offset}")
        if e.text:
            print(f"     Text: {e.text.strip()}")
    except Exception as e:
        print(f"  ❌ {f_path}: Error: {e}")
        # traceback.print_exc()
