"""Original procedural score for "Seeing the Invisible" (72 BPM, D minor -> F major), timed to src/timeline.py.

python music.py  -> audio/score.wav (48 kHz stereo float) + audio/stems/*.wav
Acts (bars): I wonder 0-6 | II equations 6-13 | III the idea 13-26 | IV turbulence 26-32 | V everywhere 32-42 | VI close 42-46
"""
from __future__ import annotations

import math

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

from common import AUDIO
from timeline import BAR, BPM, END

SR = 48000
BEAT = 60.0 / BPM
DUR = END + 6.0
N = int(DUR * SR)
rng = np.random.default_rng(72)


def t_of(bar, beat=0.0):
    return bar * BAR + beat * BEAT


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


class Bus:
    def __init__(self, name, rev=0.3):
        self.name = name
        self.L = np.zeros(N, np.float32)
        self.R = np.zeros(N, np.float32)
        self.rev = rev

    def add(self, t0, sig, pan=0.0, gain=1.0):
        i0 = int(t0 * SR)
        if i0 >= N:
            return
        sig = sig[: N - i0] * gain
        gl = math.cos((pan + 1) * math.pi / 4)
        gr = math.sin((pan + 1) * math.pi / 4)
        self.L[i0:i0 + len(sig)] += sig * gl
        self.R[i0:i0 + len(sig)] += sig * gr


def env_adsr(n, a, d, s, r, sr=SR):
    na, nd, nr = int(a * sr), int(d * sr), int(r * sr)
    ns = max(n - na - nd, 0)
    e = np.concatenate([np.linspace(0, 1, max(na, 1), endpoint=False), np.linspace(1, s, max(nd, 1), endpoint=False),
                        np.full(ns, s), np.linspace(s, 0, max(nr, 1))]).astype(np.float32)
    return e


# ------------------------------------------------------------------ instruments
def pad_note(m, dur, bright=0.35, detune=0.07, voices=3, attack=1.6, release=2.4, lfo=0.13):
    n = int((dur + release) * SR)
    t = np.arange(n, dtype=np.float32) / SR
    f0 = mtof(m)
    out = np.zeros(n, np.float32)
    fc = f0 * (2.0 + 6.0 * bright) * (1 + 0.35 * np.sin(2 * np.pi * lfo * t + rng.uniform(0, 6)))
    nh = int(min(14, 16000 / f0))
    for v in range(voices):
        dt = (v - (voices - 1) / 2) * detune / max(voices - 1, 1) * 2
        fv = f0 * 2 ** (dt / 12)
        ph0 = rng.uniform(0, 2 * np.pi)
        for h in range(1, nh + 1):
            amp = (1.0 / h) / (1 + (h * fv / fc) ** 2)
            out += amp * np.sin(2 * np.pi * fv * h * t + ph0 * h)
    out /= voices
    e = env_adsr(n, attack, 0.5, 0.85, release)
    return out * e[:n] * 0.18


def bell(m, dur=4.0, amp=1.0):
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    f0 = mtof(m)
    ratios = [1.0, 2.0, 3.01, 4.17, 5.43, 6.79]
    amps = [1.0, 0.45, 0.25, 0.16, 0.09, 0.05]
    decs = [3.2, 1.9, 1.2, 0.8, 0.5, 0.35]
    out = np.zeros(n, np.float32)
    for r, a, d in zip(ratios, amps, decs):
        if f0 * r < 18000:
            out += a * np.sin(2 * np.pi * f0 * r * t) * np.exp(-t / d)
    att = np.clip(t / 0.003, 0, 1)
    return out * att * 0.22 * amp


def piano(m, dur=3.0, vel=0.8):
    n = int((dur + 1.2) * SR)
    t = np.arange(n, dtype=np.float32) / SR
    f0 = mtof(m)
    B = 0.00035
    out = np.zeros(n, np.float32)
    for h in range(1, 13):
        fh = h * f0 * math.sqrt(1 + B * h * h)
        if fh > 16000:
            break
        a = vel ** (0.5 + 0.1 * h) / h ** 1.15
        tau = 3.2 / (1 + 0.45 * h) * (220 / max(f0, 110)) ** 0.3
        out += a * np.sin(2 * np.pi * fh * t + rng.uniform(0, 6)) * (0.7 * np.exp(-t / tau) + 0.3 * np.exp(-t / (tau * 4)))
    # damper at note end
    rel = np.ones(n, np.float32)
    i_off = int(dur * SR)
    if i_off < n:
        rel[i_off:] = np.exp(-(t[i_off:] - t[i_off]) / 0.25)
    # hammer
    hn = rng.standard_normal(int(0.012 * SR)).astype(np.float32) * np.exp(-np.arange(int(0.012 * SR)) / (0.003 * SR))
    out[: len(hn)] += 0.08 * vel * hn
    att = np.clip(t / 0.002, 0, 1)
    return out * rel * att * 0.25


def pluck(m, dur=0.9, vel=0.8, ratio=2.0, index=2.2):
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    f0 = mtof(m)
    I = index * np.exp(-t / 0.12) * vel
    mod = np.sin(2 * np.pi * f0 * ratio * t)
    out = np.sin(2 * np.pi * f0 * t + I * mod) * np.exp(-t / (0.35 + 0.25 * vel))
    att = np.clip(t / 0.003, 0, 1)
    return (out * att * 0.16 * vel).astype(np.float32)


def bass(m, dur, vel=0.8):
    n = int((dur + 0.4) * SR)
    t = np.arange(n, dtype=np.float32) / SR
    f0 = mtof(m)
    s = np.sin(2 * np.pi * f0 * t) + 0.25 * np.sin(4 * np.pi * f0 * t) + 0.08 * np.sin(6 * np.pi * f0 * t)
    s = np.tanh(1.3 * s)
    e = env_adsr(n, 0.04, 0.3, 0.75, 0.4)
    return (s * e[:n] * 0.22 * vel).astype(np.float32)


def kick(vel=0.8, deep=False):
    n = int(0.9 * SR)
    t = np.arange(n, dtype=np.float32) / SR
    f = (34 if deep else 46) + (60 if deep else 80) * np.exp(-t / (0.06 if deep else 0.035))
    ph = 2 * np.pi * np.cumsum(f) / SR
    out = np.sin(ph) * np.exp(-t / (0.55 if deep else 0.28))
    out[: int(0.002 * SR)] += 0.3
    return (out * 0.5 * vel).astype(np.float32)


def noise_swell(dur, lo=300, hi=3000, shape="rise", amp=0.3):
    n = int(dur * SR)
    x = rng.standard_normal(n).astype(np.float32)
    sos = butter(2, [lo, hi], btype="band", fs=SR, output="sos")
    x = sosfilt(sos, x).astype(np.float32)
    u = np.linspace(0, 1, n, dtype=np.float32)
    if shape == "rise":
        e = u ** 2.2
    elif shape == "fall":
        e = (1 - u) ** 2
    else:
        e = np.clip(np.sin(np.pi * u), 0, 1) ** 1.5
    return x * e * amp


def tick(vel=0.5):
    n = int(0.06 * SR)
    x = rng.standard_normal(n).astype(np.float32)
    sos = butter(2, 6000, btype="high", fs=SR, output="sos")
    x = sosfilt(sos, x).astype(np.float32) * np.exp(-np.arange(n) / (0.012 * SR))
    return x * 0.05 * vel


# ------------------------------------------------------------------ harmony
CH = {
    "Dm": [38, 50, 57, 62, 65, 69, 76],
    "Bb": [34, 46, 53, 58, 62, 65, 72],
    "F": [29, 41, 53, 60, 65, 69, 79],
    "C": [36, 48, 55, 60, 64, 67, 74],
    "Gm": [31, 43, 50, 55, 58, 62, 69],
    "A": [33, 45, 52, 57, 61, 64, 71],
    "Asus": [33, 45, 52, 57, 62, 64, 71],
    "Bb#11": [34, 46, 53, 57, 62, 64, 72],
    "Gm9": [31, 43, 50, 53, 58, 62, 69],
    "A7b9": [33, 45, 52, 55, 58, 61, 67],
    "Fadd9": [29, 41, 53, 60, 65, 67, 69, 72],
}


def main():
    pad = Bus("pad", 0.45)
    keys = Bus("keys", 0.4)
    arp = Bus("arp", 0.35)
    low = Bus("low", 0.12)
    drums = Bus("drums", 0.15)
    fx = Bus("fx", 0.5)

    # ---------------- Act I: wonder (bars 0-6)
    dr = int((t_of(6) + 3) * SR)
    tt = np.arange(dr, dtype=np.float32) / SR
    drone = (np.sin(2 * np.pi * mtof(38) * tt) + 0.5 * np.sin(2 * np.pi * mtof(45) * tt + 1.0)
             + 0.25 * np.sin(2 * np.pi * mtof(50) * tt * 1.0007))
    drone *= np.clip(tt / 4.0, 0, 1) * np.clip((t_of(6) + 3 - tt) / 3.0, 0, 1) * (0.85 + 0.15 * np.sin(2 * np.pi * 0.07 * tt))
    low.add(0.0, drone * 0.10)
    for m in (62, 65, 69, 76):
        pad.add(0.8, pad_note(m, t_of(6) - 0.8, bright=0.15, attack=4.0, release=3.0), pan=rng.uniform(-0.5, 0.5),
                gain=0.55)
    for bar, beat, m in ((0.6, 0, 81), (1.4, 0, 77), (2.0, 2, 76), (2.9, 0, 74), (3.5, 1, 81), (4.0, 0, 86),
                         (4.4, 2, 81), (4.9, 1, 77), (5.4, 0, 76), (5.8, 2, 74)):
        keys.add(t_of(bar, beat), bell(m, 5.0, 0.8), pan=rng.uniform(-0.6, 0.6))
    # ember crackle (first ~12 s)
    for _ in range(70):
        t0 = rng.uniform(0.3, 12.5)
        n = int(0.004 * SR)
        c = rng.standard_normal(n).astype(np.float32) * np.exp(-np.arange(n) / (0.0008 * SR))
        fx.add(t0, c * 0.05 * rng.uniform(0.2, 1.0), pan=rng.uniform(-0.2, 0.2))
    # title swell + boom at bar 4
    fx.add(t_of(4) - 2.4, noise_swell(2.4, 500, 6000, "rise", 0.12), pan=0)
    drums.add(t_of(4), kick(0.9, deep=True))
    for m in (74, 81, 86):
        keys.add(t_of(4), bell(m, 6.0, 0.6), pan=rng.uniform(-0.7, 0.7))

    # ---------------- Act II: the rules (bars 6-13)
    prog2 = ["Dm", "Bb", "F", "C", "Dm", "Bb", "Asus"]
    for i, c in enumerate(prog2):
        bar = 6 + i
        notes = CH[c]
        for m in notes[2:6]:
            pad.add(t_of(bar), pad_note(m, BAR + 0.3, bright=0.25 + 0.03 * i), pan=rng.uniform(-0.6, 0.6), gain=0.7)
        if bar >= 8:
            low.add(t_of(bar), bass(notes[1], BAR - 0.1, 0.6))
    low.add(t_of(12.5), bass(45, BAR / 2, 0.6))
    pad.add(t_of(12.5), pad_note(61, BAR / 2 + 0.3, bright=0.3), gain=0.6)
    mel2 = [(6, 0, 74, 1.6), (6, 2, 77, 1.6), (7, 0, 76, 1.6), (7, 2, 72, 2.4), (8, 0, 72, 1.6), (8, 2, 77, 1.6),
            (9, 0, 76, 1.0), (9, 1.5, 79, 0.8), (9, 2, 76, 2.0), (10, 0, 74, 1.6), (10, 2, 81, 1.6), (11, 0, 79, 1.2),
            (11, 2, 77, 1.2), (11, 3, 74, 1.0), (12, 0, 76, 2.4), (12, 2, 73, 2.0)]
    for bar, beat, m, d in mel2:
        keys.add(t_of(bar, beat), piano(m, d, 0.62), pan=0.15)
        keys.add(t_of(bar, beat), piano(m - 12, d, 0.35), pan=-0.15)
    for bar in range(10, 13):
        for k in range(8):
            drums.add(t_of(bar, k * 0.5), tick(0.35 + 0.15 * (k % 2 == 0)), pan=0.3 * ((-1) ** k))

    # ---------------- Act III: the idea (bars 13-26) -- arpeggio ostinato = time stepping
    prog3 = ["Dm", "Bb", "F", "C", "Dm", "Bb", "F", "C", "Gm", "Bb", "Dm", "Gm", "A"]
    pattern = [0, 2, 3, 4, 3, 2, 1, 2, 0, 2, 3, 5, 3, 2, 1, 2]
    for i, c in enumerate(prog3):
        bar = 13 + i
        notes = CH[c][1:]
        build = min(1.0, 0.45 + 0.05 * i)
        for k in range(16):
            m = notes[pattern[k] % len(notes)] + 12
            vel = build * (0.9 if k % 4 == 0 else 0.62)
            arp.add(t_of(bar, k * 0.25), pluck(m, 0.8, vel), pan=0.35 * math.sin(k * 0.7))
            if bar >= 20:
                arp.add(t_of(bar, k * 0.25 + 0.125), pluck(m + 12, 0.5, vel * 0.35), pan=-0.4 * math.sin(k * 0.7))
        for m in CH[c][2:5]:
            pad.add(t_of(bar), pad_note(m, BAR + 0.2, bright=0.2), pan=rng.uniform(-0.6, 0.6), gain=0.45)
        if bar >= 17:
            low.add(t_of(bar), bass(CH[c][1] - 12 if CH[c][1] > 40 else CH[c][1], BAR * 0.48, 0.7))
            low.add(t_of(bar, 2), bass(CH[c][1] - 12 if CH[c][1] > 40 else CH[c][1], BAR * 0.45, 0.6))
        if bar >= 20:
            drums.add(t_of(bar), kick(0.55))
            drums.add(t_of(bar, 2), kick(0.45))
            keys.add(t_of(bar), bell(CH[c][5] + 12, 3.0, 0.45), pan=rng.uniform(-0.5, 0.5))
    fx.add(t_of(24.5), noise_swell(t_of(26) - t_of(24.5), 400, 5000, "rise", 0.14))

    # ---------------- Act IV: turbulence (bars 26-32)
    prog4 = ["Dm", "Bb#11", "Gm9", "A7b9", "Gm9", "Gm9"]
    for i, c in enumerate(prog4):
        bar = 26 + i
        notes = CH[c]
        calm = bar >= 30
        for m in notes[2:6]:
            pad.add(t_of(bar), pad_note(m, BAR + 0.4, bright=0.45 if not calm else 0.2, detune=0.18), pan=rng.uniform(-0.8, 0.8),
                    gain=0.6)
        low.add(t_of(bar), bass(notes[0] + 12, BAR - 0.1, 0.75 if not calm else 0.5))
        nsteps = 24 if not calm else 6
        for k in range(nsteps):
            beat = k * 4.0 / nsteps + rng.uniform(-0.03, 0.03)
            m = int(rng.choice(notes[2:])) + 12 * int(rng.integers(0, 2))
            arp.add(t_of(bar, beat), pluck(m, 0.6, rng.uniform(0.35, 0.7), ratio=3.5 if not calm else 2.0,
                                           index=3.0 if not calm else 1.5), pan=rng.uniform(-0.9, 0.9))
        if not calm:
            fx.add(t_of(bar), noise_swell(BAR, 150 + 120 * i, 1500 + 600 * i, "arch", 0.10), pan=rng.uniform(-0.5, 0.5))
            drums.add(t_of(bar), kick(0.7, deep=True))
    fx.add(t_of(31), noise_swell(BAR, 600, 8000, "rise", 0.12))

    # ---------------- Act V: everywhere (bars 32-42)
    prog5 = ["F", "C", "Dm", "Bb", "F", "C", "Dm", "Bb", "Gm", "C"]
    mel5 = {32: [81, 84, 86, 84], 33: [79, 76, 79, 81], 34: [77, 81, 84, 86], 35: [84, 82, 81, 77],
            36: [81, 84, 86, 89], 37: [88, 86, 84, 79], 38: [81, 84, 86, 84], 39: [82, 81, 77, 74],
            40: [79, 77, 74, 74], 41: [76, 79, 84, 88]}
    for i, c in enumerate(prog5):
        bar = 32 + i
        notes = CH[c]
        heart = bar >= 40
        for m in notes[2:7]:
            pad.add(t_of(bar), pad_note(m, BAR + 0.3, bright=0.4, voices=4, detune=0.1), pan=rng.uniform(-0.8, 0.8),
                    gain=0.62)
        for k in range(8):
            low.add(t_of(bar, k * 0.5), bass(notes[1], 0.36, 0.55 if k % 2 else 0.75))
        for k in range(16):
            m = notes[2 + pattern[k] % 4] + 12
            arp.add(t_of(bar, k * 0.25), pluck(m, 0.6, 0.55 if k % 4 else 0.75), pan=0.4 * math.sin(k * 0.6))
        for k, m in enumerate(mel5[bar]):
            keys.add(t_of(bar, k), piano(m, 0.9, 0.7), pan=0.1)
            keys.add(t_of(bar, k), bell(m, 2.5, 0.3), pan=-0.2)
        if not heart:
            for k in range(4):
                drums.add(t_of(bar, k), kick(0.55 if k % 2 == 0 else 0.4))
            for k in range(16):
                drums.add(t_of(bar, k * 0.25), tick(0.45 if k % 2 else 0.25), pan=0.25)
        else:  # heartbeat at 72 bpm under the blood-flow shot
            for k in range(4):
                drums.add(t_of(bar, k), kick(0.75))
                drums.add(t_of(bar, k) + 0.19, kick(0.5))

    # ---------------- Act VI: close (bars 42-46.2)
    for bar, c, ln in ((42, "Bb", BAR), (43, "C", BAR), (44, "Fadd9", t_of(46.2) - t_of(44) + 1.0)):
        for m in CH[c][2:]:
            pad.add(t_of(bar), pad_note(m, ln, bright=0.32, voices=4, attack=0.8, release=4.5), pan=rng.uniform(-0.8, 0.8),
                    gain=0.7)
        low.add(t_of(bar), bass(CH[c][1], ln, 0.7))
    fx.add(t_of(43), noise_swell(BAR, 500, 7000, "rise", 0.12))
    drums.add(t_of(44), kick(1.0, deep=True))
    for bar, beat, m, d in ((42, 0, 77, 1.5), (42, 2, 81, 1.5), (43, 0, 79, 1.5), (43, 2, 84, 1.5), (44, 0, 81, 5.0),
                            (45, 0, 77, 2.0), (45, 2, 72, 5.0)):
        keys.add(t_of(bar, beat), piano(m, d, 0.65), pan=0.1)
    for m in (89, 84, 93):
        keys.add(t_of(44), bell(m, 7.0, 0.5), pan=rng.uniform(-0.7, 0.7))

    # ------------------------------------------------------------------ reverb + mix
    buses = [pad, keys, arp, low, drums, fx]
    gains = {"pad": 0.9, "keys": 0.95, "arp": 0.8, "low": 1.0, "drums": 0.8, "fx": 0.9}
    ir_n = int(4.5 * SR)
    ti = np.arange(ir_n, dtype=np.float32) / SR
    irs = []
    for ch in range(2):
        nz = rng.standard_normal(ir_n).astype(np.float32)
        lo_ = sosfilt(butter(2, 600, "low", fs=SR, output="sos"), nz) * np.exp(-ti / 1.1)
        mi_ = sosfilt(butter(2, [600, 4000], "band", fs=SR, output="sos"), nz) * np.exp(-ti / 0.85)
        hi_ = sosfilt(butter(2, 4000, "high", fs=SR, output="sos"), nz) * np.exp(-ti / 0.4)
        ir = (lo_ + mi_ + 0.6 * hi_).astype(np.float32)
        ir[: int(0.025 * SR)] = 0
        irs.append(ir / np.sqrt((ir ** 2).sum()))
    send_L = np.zeros(N, np.float32)
    send_R = np.zeros(N, np.float32)
    mixL = np.zeros(N, np.float32)
    mixR = np.zeros(N, np.float32)
    stems = AUDIO / "stems"
    stems.mkdir(parents=True, exist_ok=True)
    from scipy.io import wavfile

    for bsn in buses:
        g = gains[bsn.name]
        mixL += bsn.L * g
        mixR += bsn.R * g
        send_L += bsn.L * g * bsn.rev
        send_R += bsn.R * g * bsn.rev
        wavfile.write(stems / f"{bsn.name}.wav", SR, np.stack([bsn.L * g, bsn.R * g], -1).astype(np.float32))
    wetL = fftconvolve(send_L, irs[0])[:N].astype(np.float32)
    wetR = fftconvolve(send_R, irs[1])[:N].astype(np.float32)
    L = mixL + 0.9 * wetL
    R = mixR + 0.9 * wetR
    # gentle bus compression (slow RMS follower) + soft clip
    x = np.stack([L, R], -1)
    rms = np.sqrt(sosfilt(butter(1, 3.0, "low", fs=SR, output="sos"), (x ** 2).mean(-1)) + 1e-9)
    thr = np.percentile(rms, 90)
    gain = np.where(rms > thr, (thr / rms) ** 0.35, 1.0).astype(np.float32)
    x = x * gain[:, None]
    x = x / (np.abs(x).max() + 1e-9) * 0.95
    x = np.tanh(x * 1.1) / np.tanh(1.1)
    # fades
    fi = int(0.05 * SR)
    x[:fi] *= np.linspace(0, 1, fi)[:, None]
    fo0 = int((END + 1.0) * SR)
    x[fo0:] *= np.linspace(1, 0, N - fo0)[:, None] ** 2
    x = x / (np.abs(x).max() + 1e-9) * 0.89  # -1 dBFS
    AUDIO.mkdir(parents=True, exist_ok=True)
    wavfile.write(AUDIO / "score.wav", SR, x.astype(np.float32))
    print("score written", DUR, "s")


if __name__ == "__main__":
    main()
