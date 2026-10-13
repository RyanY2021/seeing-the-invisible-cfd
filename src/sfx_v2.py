"""v2 sound effects, synthesised from the cue lists the shots export (renders/<shot>/clawd_track.json) plus the
edit's transitions and the neon switch-ons. Writes audio/sfx_v2.wav and the final audio/mix_v2.wav
(score + sfx, -14 LUFS, true peak < -1 dB).

  python sfx_v2.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "score"))
import timeline_v2 as TL  # noqa: E402
from common import AUDIO, RENDERS  # noqa: E402

SR = 48000
rng = np.random.default_rng(7)
PENTA = [0, 2, 4, 7, 9]                     # E major pentatonic around the score's key


def tone(f, dur, kind="square", att=0.003, dec=None, duty=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = np.broadcast_to(np.asarray(f, np.float64), (n,)) if np.ndim(f) else np.full(n, f)
    ph = np.cumsum(f) / SR
    if kind == "square":
        y = np.where((ph % 1.0) < duty, 1.0, -1.0)
        y = signal.lfilter([0.35, 0.35], [1, -0.3], y)           # soften the edges a little
    elif kind == "tri":
        y = 2 * np.abs(2 * (ph % 1.0) - 1) - 1
    else:
        y = np.sin(2 * np.pi * ph)
    env = np.minimum(t / att, 1.0)
    env *= np.exp(-t / dec) if dec else np.clip((dur - t) / 0.01, 0, 1)
    return y * env


def noise(dur, lo, hi, dec):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = signal.sosfilt(signal.butter(2, [lo, hi], "bandpass", fs=SR, output="sos"), rng.standard_normal(n))
    return y * np.exp(-t / dec) * np.minimum(t / 0.002, 1)


def add(*xs):
    """sum signals of different lengths (zero-padded)"""
    n = max(len(x) for x in xs)
    out = np.zeros(n)
    for x in xs:
        out[:len(x)] += x
    return out


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def babble(text):
    """Clawd 'speaks': a short run of 8-bit syllables, pitch contour rising on '?' and '!'"""
    syl = max(2, min(9, len(text.replace(" ", "")) // 2))
    out = []
    base = 76 + rng.integers(-2, 3)
    for k in range(syl):
        m = base + PENTA[rng.integers(0, 5)] + (5 if (k == syl - 1 and text.strip()[-1:] in "?!") else 0)
        d = rng.uniform(0.045, 0.075)
        out.append(tone(midi(m), d, "square", dec=d * 0.8, duty=rng.choice([0.25, 0.5])) * 0.5)
        out.append(np.zeros(int(rng.uniform(0.01, 0.03) * SR)))
    return np.concatenate(out)


def sweep(f0, f1, dur, kind="square", dec=None):
    n = int(dur * SR)
    f = f0 * (f1 / f0) ** (np.arange(n) / n)
    return tone(f, dur, kind, dec=dec)


FX = {
    "hop": lambda: sweep(380, 980, 0.09, "square", 0.06) * 0.35,
    "land": lambda: add(sweep(140, 55, 0.12, "sine", 0.06) * 0.9, noise(0.05, 800, 3000, 0.01) * 0.2),
    "surprise": lambda: np.concatenate([tone(midi(83), 0.05, dec=0.04), tone(midi(90), 0.08, dec=0.06)]) * 0.4,
    "wave": lambda: np.concatenate([tone(midi(m), 0.05, "tri", dec=0.04) for m in (79, 83, 86, 91)]) * 0.35,
    "walk": lambda: np.concatenate([np.concatenate([noise(0.02, 1500, 5000, 0.006) * 0.12, np.zeros(int(0.105 * SR))])
                                    for _ in range(8)]),
    "thump": lambda: add(sweep(120, 40, 0.25, "sine", 0.12) * 1.0, noise(0.15, 200, 900, 0.05) * 0.5),
    "burst": lambda: add(*[np.pad(tone(midi(rng.integers(72, 96)), 0.04, "square", dec=0.03) * 0.25,
                                  (int(k * 0.018 * SR), 0)) for k in range(14)]),
    "chime": lambda: add(tone(midi(88), 1.2, "sine", dec=0.5), 0.5 * tone(midi(100), 0.8, "sine", dec=0.25)) * 0.25,
    "shutter": lambda: add(noise(0.05, 2000, 9000, 0.008) * 0.8, np.pad(noise(0.04, 1500, 6000, 0.01) * 0.5,
                                                                         (int(0.06 * SR), 0))),
    "squash": lambda: sweep(300, 120, 0.15, "tri", 0.1) * 0.5,
    "zap": lambda: add(sweep(1600, 120, 0.35, "square", 0.25) * 0.35, noise(0.3, 2000, 8000, 0.1) * 0.15),
    "blip": lambda: tone(midi(91), 0.08, "square", dec=0.06) * 0.35,
    "ripple": lambda: add(*[np.pad(tone(midi(76 + 3 * k), 0.4, "sine", dec=0.2) * 0.15, (int(k * 0.05 * SR), 0))
                            for k in range(8)]),
    "whoosh": lambda: noise(0.6, 300, 4000, 0.25) * np.sin(np.linspace(0, np.pi, int(0.6 * SR))) * 0.35,
    "glitch": lambda: np.concatenate([noise(0.03, 800, 8000, 0.02) * (0.5 if k % 2 else 0.2) for k in range(10)]),
    "neon": lambda: add(noise(0.12, 2000, 9000, 0.03) * 0.25, tone(120, 0.5, "square", dec=0.25, duty=0.5) * 0.06),
}
GAIN = {"walk": 0.5}


def main():
    total = int(TL.TOTAL / TL.FPS * SR) + SR
    out = np.zeros((2, total))

    def put(kind, frame, pan=0.0, gain=1.0, text=None):
        y = babble(text) if kind == "say" else FX[kind]()
        y = np.asarray(y, np.float64) * gain * GAIN.get(kind, 1.0)
        i0 = int(frame / TL.FPS * SR)
        if i0 >= total:
            return
        n = min(len(y), total - i0)
        a = (pan + 1) * np.pi / 4
        out[0, i0:i0 + n] += y[:n] * np.cos(a)
        out[1, i0:i0 + n] += y[:n] * np.sin(a)

    # Clawd's actions, per shot (screen x -> stereo pan)
    for sid, b0, b1, (kind, n), _ in TL.SHOTS:
        p = RENDERS / sid / "clawd_track.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        frames = {int(k): v for k, v in d["frames"].items()}
        S = b0 * TL.BAR
        for cf, c in d["cues"]:
            F = S + cf - 1
            if F >= b1 * TL.BAR:
                continue
            pan = 0.0
            if cf in frames:
                pan = float(np.clip((frames[cf][0] / 1920 - 0.5) * 1.4, -0.8, 0.8))
            if c.startswith("say:"):
                put("say", F, pan, 0.8, text=c.split(":", 2)[2])
            elif c in FX:
                put(c, F, pan)
    # transitions
    for sid, b0, b1, (kind, n), _ in TL.SHOTS:
        if kind == "flash":
            put("whoosh", b0 * TL.BAR - 8, 0.0, 0.8)
        elif kind == "pixel":
            put("glitch", b0 * TL.BAR - 4, 0.0, 0.6)
    # neon switch-ons (V01 tubes, V03 title words) and the switch-off in V26
    for f in (22, 60, 84):
        put("neon", f, -0.3 if f == 22 else 0.3)
    for f in (4, 16, 28):
        put("neon", 10 * TL.BAR + f, 0.0, 1.2)
    put("neon", 136 * TL.BAR + 250, 0.0, 1.0)
    out = np.tanh(out * 0.9) * 0.6
    sf.write(AUDIO / "sfx_v2.wav", out.T.astype(np.float32), SR, subtype="FLOAT")
    # final mix: score + sfx (sfx ducked under the score's level), loudness -14 LUFS
    score, sr = sf.read(AUDIO / "score_v2.wav", always_2d=True)
    assert sr == SR
    score = score.T
    n = max(score.shape[1], out.shape[1])
    mix = np.zeros((2, n))
    mix[:, :score.shape[1]] += score
    mix[:, :out.shape[1]] += out * 0.55
    import prism_arcade as P
    P.SR = SR
    lufs = P.lufs(mix)
    mix *= 10 ** ((-14.0 - lufs) / 20)
    pk = np.abs(mix).max()
    if pk > 0.89:
        mix *= 0.89 / pk
    sf.write(AUDIO / "mix_v2.wav", mix.T, SR, subtype="PCM_24")
    print(f"sfx + mix written ({mix.shape[1] / SR:.1f}s, was {lufs:.1f} LUFS)")


if __name__ == "__main__":
    main()
