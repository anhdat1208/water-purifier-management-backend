import re
import sys
from pathlib import Path

plan_path = Path(sys.argv[1])
n = int(sys.argv[2])
out_path = Path(sys.argv[3])

plan = plan_path.read_text(encoding="utf-8")
lines = plan.splitlines(True)
out = []
infence = False
intask = False
for line in lines:
    if line.startswith("```"):
        infence = not infence
    if not infence and re.match(r"^#+[ \t]+Task[ \t]+\d+", line):
        intask = bool(re.match(rf"^#+[ \t]+Task[ \t]+{n}([^0-9]|$)", line))
    if intask:
        out.append(line)

if not out:
    raise SystemExit(f"task {n} not found")

out_path.write_text("".join(out), encoding="utf-8")
print(f"wrote {out_path}: {len(out)} lines")
