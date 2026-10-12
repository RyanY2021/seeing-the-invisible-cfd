"""List, per shot, which source frames the edit needs and which are still missing.
Run: .venv\\Scripts\\python.exe tools\\check_renders.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from common import FPS, RENDERS  # noqa: E402
import timeline as TL  # noqa: E402

ok_all = True
for i, (sid, start, end, rdir, src0, _, tr) in enumerate(TL.SHOTS):
    nxt_tr = TL.SHOTS[i + 1][6] if i + 1 < len(TL.SHOTS) else 0.0
    need0 = src0
    need1 = src0 + int(round((end - start + nxt_tr) * FPS))
    d = RENDERS / rdir
    have = {int(p.stem) for p in d.glob("*.png")} if d.exists() else set()
    missing = [n for n in range(need0, need1 + 1) if n not in have]
    status = "OK" if not missing else f"missing {len(missing)} (e.g. {missing[:3]})"
    ok_all &= not missing
    print(f"{sid}: need {need0}..{need1} ({need1 - need0 + 1} f), have {len(have)} -> {status}")
print("ALL READY" if ok_all else "NOT READY")
