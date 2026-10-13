"""v2: frames needed per shot (timeline_v2) vs EXR frames rendered. python tools/check_renders_v2.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import timeline_v2 as TL  # noqa: E402

total_need = total_have = 0
for sid, b0, b1, *_ in TL.SHOTS:
    need = TL.shot_frames(sid)
    d = ROOT / "renders" / sid
    have = len(list(d.glob("*.exr"))) if d.exists() else 0
    total_need += need
    total_have += min(have, need)
    flag = "OK" if have >= need else ("--" if have == 0 else f"{100 * have // need}%")
    print(f"{sid}  bars {b0:3d}-{b1:3d}  {have:4d}/{need:4d}  {flag}")
print(f"total {total_have}/{total_need} ({100 * total_have // total_need}%)")
