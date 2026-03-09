import ast

try:
    with open(r"k:\app\1.보고서 분석기\app.py", "r", encoding="utf-8") as f:
        ast.parse(f.read())
    print("Syntax OK")
except SyntaxError as e:
    print(f"Syntax Error: {e}")
    print(f"Line: {e.lineno}, Offset: {e.offset}, Text: {e.text}")
except Exception as e:
    print(f"Error: {e}")
