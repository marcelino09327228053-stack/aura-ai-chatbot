"""Run every unittest module in isolation and provide a compact summary."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
failed = []
total = 0
for path in sorted((ROOT / "tests").glob("test_*.py")):
    module = f"tests.{path.stem}"
    result = subprocess.run([sys.executable, "-m", "unittest", module], cwd=ROOT,
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    match = re.search(r"Ran (\d+) test", (result.stdout or "") + (result.stderr or ""))
    count = int(match.group(1)) if match else 0
    total += count
    status = "PASS" if result.returncode == 0 else "FAIL"
    print(f"{status} {path.name}: {count}")
    if result.returncode:
        failed.append(path.name)
        print(((result.stdout or "") + (result.stderr or ""))[-3000:])
print(f"TOTAL PASSED: {total if not failed else total - len(failed)}")
if failed: print("FAILED MODULES: " + ", ".join(failed))
raise SystemExit(1 if failed else 0)
