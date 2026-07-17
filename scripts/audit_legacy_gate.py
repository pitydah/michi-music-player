"""Gate: fail if new functions are added to legacy_widgets."""
import os, sys, ast
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY = os.path.join(BASE, "legacy_widgets")
REF_FILE = os.path.join(BASE, "docs", "legacy_method_count.txt")

def count_methods():
    if not os.path.isdir(LEGACY):
        return 0
    count = 0
    for root, dirs, files in os.walk(LEGACY):
        for f in files:
            if not f.endswith('.py') or f.startswith('__'):
                continue
            with open(os.path.join(root, f)) as fh:
                try:
                    tree = ast.parse(fh.read())
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            count += 1
                except SyntaxError:
                    pass
    return count

def main():
    count = count_methods()
    if os.path.isfile(REF_FILE):
        ref = int(open(REF_FILE).read().strip())
        if count > ref:
            print(f"FAIL: legacy_widgets grew from {ref} to {count} methods")
            sys.exit(1)
        print(f"OK: {count} methods (reference: {ref})")
    else:
        with open(REF_FILE, 'w') as f:
            f.write(str(count))
        print(f"Reference set: {count} methods")
    sys.exit(0)

if __name__ == "__main__":
    main()
