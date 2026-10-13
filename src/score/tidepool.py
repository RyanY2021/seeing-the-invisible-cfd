"""(Copied from D:/Creative/Colorbass Test for the CFD v2 score: SR 48 kHz, 120 BPM. Otherwise unchanged.)

TIDEPOOL  -  a short "liquid" colorbass demo (150 BPM, E major), built on the prism_arcade.py engine.

The water vocabulary:
  droplets    sine "plinks" whose pitch chirps upward (that is how a real drop rings), tuned to the key:
              they play the melody, the rain arps and even the hi-hats
  bubbles     random streams of tiny droplets -> a babbling-brook bed, and a "boiling" riser
  flow        colorbass chords that glide voice-by-voice into each other, plus a gliding sub
  wetness     bubbling oo/oh formant + resonant filter, flanger and phaser movement, ripple delay
  underwater  the intro sits under a low-pass that "surfaces" into the build, and sinks again at the end
  splash      snares layered with a falling noise splash and a spray of droplets; the drop ends in a drain

    python tidepool.py   ->  out/Tidepool.{wav,mp3} + out/Tidepool_overview.png
"""
import os
import time

import numpy as np
import soundfile as sf
from numba import njit
from scipy import signal

import prism_arcade as P
from prism_arcade import SR, STEP, BAR, T, mtof, osc_saw, osc_pulse, filt, sos, ramp_env, formant_bank

N_BARS = 24
TAIL = 3.5
N = int((N_BARS * BAR + TAIL) * SR)
P.N = N          # the shared Mix / sidechain / reverb / delay helpers size their buffers from this
NAME = "Tidepool"
rng = np.random.default_rng(2026)


# =====================================================================================
#  NEW DSP: flanger, phaser, bubbling random LFO
# =====================================================================================
@njit(cache=True)
def flanger(x, delay_ms, fb, mix):
    n = x.shape[0]
    L = 2048
    buf = np.zeros(L)
    y = np.empty(n)
    w = 0
    for i in range(n):
        rp = w - delay_ms[i] * SR / 1000.0
        if rp < 0:
            rp += L
        i0 = int(rp)
        fr = rp - i0
        s = buf[i0 % L] * (1.0 - fr) + buf[(i0 + 1) % L] * fr
        buf[w] = x[i] + fb * s
        y[i] = (1.0 - mix) * x[i] + mix * s
        w += 1
        if w == L:
            w = 0
    return y


@njit(cache=True)
def phaser(x, fc, stages, fb, mix):
    n = x.shape[0]
    x1 = np.zeros(stages)
    y1 = np.zeros(stages)
    y = np.empty(n)
    last = 0.0
    for i in range(n):
        tn = np.tan(np.pi * fc[i] / SR)
        a = (tn - 1.0) / (tn + 1.0)
        s = x[i] + fb * last
        for k in range(stages):
            o = a * s + x1[k] - a * y1[k]
            x1[k] = s
            y1[k] = o
            s = o
        last = s
        y[i] = (1.0 - mix) * x[i] + mix * s
    return y


def bubble_lfo(n, rate):
    """Smooth random modulation in [0,1]; rate (Hz) may be an array (e.g. accelerating)."""
    phase = np.cumsum(P.arr(rate, n)) / SR
    pts = rng.random(int(phase[-1]) + 3)
    i = phase.astype(int)
    w = (1 - np.cos(np.pi * (phase - i))) / 2
    return pts[i] * (1 - w) + pts[i + 1] * w


def peq(x, f0, gain_db, q=0.8):
    """RBJ peaking EQ on a (2, n) signal."""
    A = 10 ** (gain_db / 40)
    w = 2 * np.pi * f0 / SR
    al = np.sin(w) / (2 * q)
    b = np.array([1 + al * A, -2 * np.cos(w), 1 - al * A])
    a = np.array([1 + al / A, -2 * np.cos(w), 1 - al / A])
    return signal.lfilter(b / a[0], a / a[0], x, axis=1)


def pan2(sig, p):
    a = (p + 1.0) * np.pi / 4.0
    return np.vstack([sig * np.cos(a), sig * np.sin(a)]) * np.sqrt(2.0)


def place(dst, sig, i0):
    if i0 >= dst.shape[1]:
        return
    n = min(sig.shape[1], dst.shape[1] - i0)
    dst[:, i0:i0 + n] += sig[:, :n]


# =====================================================================================
#  WATER INSTRUMENTS
# =====================================================================================
def droplet(f_end, decay=0.05, chirp=0.7, tau=0.01, bright=0.15):
    """A water drop: a sine whose pitch rises quickly (chirp, in octaves) and dies away."""
    n = int((decay * 7 + 0.01) * SR)
    t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(f_end * 2.0 ** (-chirp * np.exp(-t / tau))) / SR
    y = np.sin(ph) + bright * np.sin(2 * ph)
    env = (1 - np.exp(-t / 0.0008)) * np.exp(-t / decay)
    env[-64:] *= np.linspace(1, 0, 64)
    return y * env


def drop_lead(note, dur, vel=1.0):
    """Tuned, glassy droplet for melodies: upward chirp + a touch of FM + delayed vibrato."""
    f = float(mtof(note))
    n = int((dur + 0.6) * SR)
    t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.12) / 0.1, 0, 1)
    ph = 2 * np.pi * np.cumsum(f * 2.0 ** (-0.5 * np.exp(-t / 0.012)) * vib) / SR
    y = np.sin(ph + 0.4 * np.exp(-t / 0.06) * np.sin(2 * ph)) + 0.1 * np.sin(3 * ph) * np.exp(-t / 0.04)
    env = (1 - np.exp(-t / 0.001)) * np.exp(-t / (0.15 + 0.35 * dur))
    n_on = int(dur * SR)
    env[n_on:] *= np.exp(-(t[n_on:] - dur) / 0.07)
    env[-256:] *= np.linspace(1, 0, 256)
    return y * env * vel


def brook(L, rate=25.0, rising=False, wash=0.12):
    """Babbling water: a wandering band-passed noise wash + a Poisson stream of bubbles.
    rising=True packs the bubbles denser and higher over time (the 'boiling' riser)."""
    n = int(L * SR)
    out = np.zeros((2, n))
    for ch in range(2):
        nz = rng.standard_normal(n)
        for _ in range(3):
            fc = np.exp(np.log(400) + (np.log(2500) - np.log(400)) * bubble_lfo(n, 0.6))
            out[ch] += filt(nz, fc, 3.0, 1) * wash
    u = rng.random(int(L * rate))
    for tt in (L * np.sqrt(u) if rising else L * u):
        x = tt / L
        f = np.exp(rng.uniform(np.log(300), np.log(1400))) * (2 ** (2.2 * x) if rising else 1.0)
        d = droplet(f, decay=rng.uniform(0.012, 0.045), chirp=rng.uniform(0.3, 1.0), tau=rng.uniform(0.003, 0.01), bright=0.05)
        amp = rng.random() ** 2 * ((0.3 + 0.7 * x) if rising else 1.0)
        place(out, pan2(d * amp, rng.uniform(-0.8, 0.8)), int(tt * SR))
    fade = int(0.3 * SR)
    out[:, :fade] *= np.linspace(0, 1, fade)
    out[:, -fade:] *= np.linspace(1, 0, fade)
    return out


def splash(vel=1.0, big=False):
    n = int((1.0 if big else 0.45) * SR)
    t = np.arange(n) / SR
    out = np.zeros((2, n))
    for ch in range(2):
        fc = 900 + 5500 * np.exp(-t / (0.12 if big else 0.06))
        out[ch] = filt(rng.standard_normal(n), fc, 1.1, 1) * np.exp(-t / (0.2 if big else 0.09)) * np.minimum(t / 0.002, 1)
    for _ in range(16 if big else 7):
        d = droplet(rng.uniform(1400, 5200), decay=rng.uniform(0.01, 0.03), chirp=rng.uniform(0.4, 0.9), tau=0.004)
        place(out, pan2(d * rng.uniform(0.15, 0.5), rng.uniform(-0.9, 0.9)), int(rng.uniform(0.005, 0.3 if big else 0.12) * SR))
    body = np.sin(2 * np.pi * np.cumsum(70 + 90 * np.exp(-t / 0.03)) / SR) * np.exp(-t / 0.05) * 0.4
    out += body
    out[:, -256:] *= np.linspace(1, 0, 256)
    return out * vel


def rush(L, vel=1.0):
    """Rushing-water riser: band-passed noise sweeping up through a closing flanger + boiling bubbles."""
    n = int(L * SR)
    t = np.arange(n) / SR
    x = t / L
    fc = 300 * (9000 / 300) ** (x ** 1.4)
    out = np.zeros((2, n))
    for ch in range(2):
        s = filt(rng.standard_normal(n), fc, 1.5, 1)
        out[ch] = flanger(s, 0.6 + 4.5 * (1 - x) + 0.3 * ch, 0.7, 0.5)
    out *= (x ** 2 + 0.01) * 0.6
    out += 0.9 * brook(L, rate=45, rising=True, wash=0.0)
    out[:, -64:] *= np.linspace(1, 0, 64)
    return out * vel


# ----------------------------------------------------------------- liquid colorbass
CH = {
    "A":   dict(root=9,  sub=33, pcs=[9, 1, 4, 8, 11],  pad=[57, 61, 64, 68, 71, 75]),   # Amaj9(#11), lydian shimmer
    "G#m": dict(root=8,  sub=32, pcs=[8, 11, 3, 6],     pad=[56, 59, 63, 66, 71]),       # G#m7
    "C#m": dict(root=1,  sub=37, pcs=[1, 4, 8, 11, 3],  pad=[56, 61, 64, 71, 75]),       # C#m9
    "B":   dict(root=11, sub=35, pcs=[11, 3, 6, 8, 1],  pad=[54, 59, 63, 68, 73]),       # B6/9
    "E":   dict(root=4,  sub=40, pcs=[4, 8, 11, 6, 3],  pad=[52, 59, 63, 66, 68, 71]),   # Emaj9
    "E/G#": dict(root=8, sub=32, pcs=[4, 8, 11, 6, 3],  pad=[56, 59, 64, 66, 71, 75]),   # Emaj9 over G#
    "C":   dict(root=0,  sub=36, pcs=[0, 4, 7, 11, 2],  pad=[55, 59, 62, 64, 71]),       # Cmaj9: borrowed bVI, "deep water"
}


def harmonize(top, chord):
    pcs = set(CH[chord]["pcs"])
    out = [top]
    m = top - 3
    while len(out) < 3 and m > top - 14:
        if m % 12 in pcs and all(abs(m - x) >= 3 for x in out):
            out.append(m)
        m -= 1
    while len(out) < 3:
        out.append(out[-1] - 12)
    return sorted(out)


def tones_in(chord, lo, hi):
    return [m for m in range(lo, hi) if m % 12 in CH[chord]["pcs"]]


def liquid_stab(chord, top, dur, vel=1.0, prev=None, rate=11.0, v0="u", v1="o", bright=1.0, bend=0.0, drain=False):
    """Colorbass hit, water edition. Downbeats start with a droplet 'bloop' (upward pitch chirp);
    inner notes glide voice-by-voice from the previous chord (flow). A random 'bubbling' LFO drives
    an oo/oh formant bank and a resonant low-pass on the growl."""
    env = ramp_env(dur, 0.05, att=0.003)
    n = env.shape[0]
    t = np.arange(n) / SR
    gr = 36 + CH[chord]["root"]
    voices = [gr, gr + 7, gr + 12] + harmonize(top, chord)
    base = np.zeros(n)
    if bend:
        base += bend * np.clip((t - dur * 0.25) / (dur * 0.75), 0, 1) ** 2
    if drain:
        base += -24.0 * np.clip(t / dur, 0, 1) ** 1.5
    motion = []
    for i, v in enumerate(voices):
        if prev is not None:
            motion.append(base + (prev[i] - v) * np.exp(-t / 0.03))
        else:
            motion.append(base - 9.0 * np.exp(-t / 0.018))
    m = bubble_lfo(n, rate * (1 + 3.0 * np.clip(t / dur, 0, 1)) if drain else rate)
    out = np.zeros((2, n))
    for ch in range(2):
        sg = 1.0 if ch == 0 else -1.0
        acc = np.zeros(n)
        for i in range(3):
            f = mtof(voices[i] + motion[i])
            ph = np.cumsum(f) / SR + rng.random()
            fm = np.sin(2 * np.pi * ph + (0.7 + 1.6 * m) * np.sin(2 * np.pi * ph))
            sw = osc_saw(f * 2 ** (sg * 0.06 / 12), rng.random())
            acc += np.tanh(1.8 * (0.8 * fm + 0.3 * sw)) * (1.0 if i == 0 else 0.7)
        fo = formant_bank(acc, v0, v1, m, shift=1.15, qs=(7.0, 9.0, 11.0), gains=(1.0, 0.8, 0.45))
        res = filt(acc, 300 + 3500 * bright * m + 3500 * bright * np.exp(-t / 0.02), 6.0, 0)
        growl = np.tanh(1.3 * (0.9 * fo + 0.5 * res))
        acc2 = np.zeros(n)
        for i in range(3, 6):
            f = mtof(voices[i] + motion[i])
            ph = np.cumsum(f) / SR + rng.random()
            s = (np.sin(2 * np.pi * ph) + 0.45 * osc_pulse(f * 2 ** (sg * 0.08 / 12), 0.5, rng.random())
                 + 0.2 * osc_saw(f * 2 ** (-sg * 0.05 / 12), rng.random()))
            acc2 += s * (1.2 if i == 5 else 0.8)
        fc2 = 1500 + 5500 * bright * np.exp(-t / (0.05 + 0.25 * dur)) + 2500 * m
        chord_sig = np.tanh(0.8 * filt(acc2, fc2, 2.0, 0))
        out[ch] = 0.6 * growl + 0.5 * chord_sig
    return out * env * vel, voices


# =====================================================================================
#  COMPOSITION
# =====================================================================================
LOOP = ["A", "G#m", "C#m", "B"]                     # IV - iii - vi - V in E major
SEQ = LOOP * 5 + ["A", "B", "E", "E"]
INTRO, BUILD, DROP, FLOW, OUTRO = 0, 4, 8, 16, 20
SECTIONS = [(INTRO, "Underwater"), (BUILD, "Surfacing"), (DROP, "Drop"), (FLOW, "Flow + drain"), (OUTRO, "Outro")]

HB = {
    "b0":  [(0, 3, 85), (3, 3, 83), (6, 2, 80), (8, 4, 83), (12, 2, 80), (14, 2, 76)],
    "b1":  [(0, 3, 83), (3, 3, 78), (6, 2, 80), (8, 6, 75), (14, 2, 78)],
    "b2":  [(0, 3, 80), (3, 3, 83), (6, 2, 87), (8, 4, 88), (12, 2, 87), (14, 2, 83)],
    "b3":  [(0, 6, 85), (6, 2, 83), (8, 8, 80)],
    "b3v": [(0, 4, 87), (4, 4, 85), (8, 8, 83)],
}


def hook(bar0, bars=("b0", "b1", "b2", "b3")):
    return [(bar0 + i, s, d, m) for i, k in enumerate(bars) for (s, d, m) in HB[k]]


class Session:
    """Arrangement helpers on one shared mix (used by the demo below and by tidepool_full.py)."""
    VOWELS = [("u", "o"), ("o", "a"), ("u", "a"), ("a", "o"), ("o", "e")]

    def __init__(self, seq):
        self.seq = seq
        self.mix = P.Mix()
        self.kicks, self.snares = [], []

    def kick(self, b, s, v=1.0):
        self.mix.add("kick", P.kick(v), T(b, s))
        self.kicks.append((T(b, s), v))

    def snare(self, b, s, v=1.0, pitch=0.0, sp=0.9, big=False):
        t = T(b, s)
        self.mix.add("snare", P.snare(v, pitch) * 0.85, t, rev=0.12, room=0.3)
        self.mix.add("snare", splash(v * sp, big), t, rev=0.25, room=0.2)
        self.snares.append((t, v))

    def tick(self, b, s, v=0.6, pan=0.0):           # a droplet as a hi-hat, with a quiet real hat for definition
        d = droplet(rng.uniform(3800, 6500), decay=0.012, chirp=0.5, tau=0.003, bright=0.0)
        self.mix.add("hats", d * v, T(b, s) + abs(rng.normal(0, 0.003)), pan=pan, room=0.15)
        self.mix.add("hats", P.hat(v * 0.3), T(b, s), pan=-pan)

    def pad(self, b, gain=1.0, steps=16, att=0.15, rel=0.8, chord=None):
        sig = P.supersaw(CH[chord or self.seq[b]]["pad"], steps * STEP, voices=5, spread=0.14, att=att, rel=rel, cutoff=5000)
        self.mix.add("pad", sig, T(b), gain=gain, rev=0.5 if steps > 16 else 0.4)

    def lead(self, events, gain=1.0, max_step=None):
        for (b, s, d, m) in events:
            if max_step and b == max_step[0] and s >= max_step[1]:
                continue
            self.mix.add("lead", drop_lead(m, d * STEP), T(b, s), gain=gain, pan=rng.uniform(-0.25, 0.25), rev=0.3, dly=0.35)

    def rain(self, b, density, gain=1.0, steps=16):
        tones = tones_in(self.seq[b], 88, 101)
        for s in range(steps):
            if rng.random() < density:
                d = droplet(float(mtof(rng.choice(tones))), decay=rng.uniform(0.03, 0.07), chirp=0.5, tau=0.006, bright=0.1)
                self.mix.add("rain", d * gain * rng.uniform(0.4, 1.0), T(b, s) + abs(rng.normal(0, 0.006)),
                             pan=rng.uniform(-0.8, 0.8), rev=0.3, dly=0.2)

    def subline(self, b0, b1, gain=1.0, drain_at=None, drain_semis=-24.0):
        """One continuous sine bass that glides (portamento) between chord roots."""
        t0 = T(b0)
        n = int((T(b1) - t0) * SR)
        target = np.empty(n)
        for b in range(b0, b1):
            target[int((T(b) - t0) * SR):int((T(b + 1) - t0) * SR)] = CH[self.seq[b]]["sub"]
        a = np.exp(-1 / (0.045 * SR))
        semi = signal.lfilter([1 - a], [1, -a], target, zi=[a * target[0]])[0]
        if drain_at:
            i0 = int((T(*drain_at) - t0) * SR)
            semi[i0:] += drain_semis * np.linspace(0, 1, n - i0) ** 1.5
        ph = 2 * np.pi * np.cumsum(mtof(semi)) / SR
        y = np.tanh(1.4 * (np.sin(ph) + 0.2 * np.sin(2 * ph))) / np.tanh(1.4)
        y[:220] *= np.linspace(0, 1, 220)
        y[-1300:] *= np.linspace(1, 0, 1300)
        self.mix.add("sub", y * gain, t0)

    def cb_hook(self, events, rate=11.0, bright=1.0, vowels=None, final_bend=0.0):
        vowels = vowels or self.VOWELS
        prev = None
        for i, (b, s, d, m) in enumerate(events):
            dur = d * STEP * (0.85 if d <= 2 else 0.92)
            v0, v1 = vowels[i % len(vowels)]
            sig, voices = liquid_stab(self.seq[b], m - 12, dur, vel=1.0 if s == 0 else 0.86,
                                      prev=None if s == 0 else prev, rate=rate, v0=v0, v1=v1, bright=bright,
                                      bend=final_bend if i == len(events) - 1 else 0.0)
            self.mix.add("cb", sig, T(b, s), rev=0.05)
            prev = voices
        return prev


def compose():
    S = Session(SEQ)
    mix = S.mix

    # =========================================================== UNDERWATER (bars 0-3)
    mix.add("amb", brook(8 * BAR + 0.5, rate=22), 0.0)
    for b in range(INTRO, BUILD):
        S.pad(b, gain=0.8, att=1.0 if b == 0 else 0.15)
    S.lead(hook(INTRO), gain=0.8)
    for b in (2, 3):
        S.rain(b, 0.25, 0.7)

    # =========================================================== SURFACING (bars 4-7)
    for b in range(BUILD, DROP):
        S.pad(b, gain=0.7, steps=8 if b == 7 else 16)
        S.rain(b, 0.35 + 0.1 * (b - BUILD), 0.8, steps=8 if b == 7 else 16)
    S.lead(hook(BUILD, ("b0", "b1", "b2", "b3v")), max_step=(7, 8))
    for b in (4, 5):
        S.kick(b, 0, 0.75)
        S.kick(b, 8, 0.75)
        for s in range(2, 16, 4):
            S.tick(b, s, 0.6, pan=0.2)
    for b in (6, 7):
        for s in (0, 4, 8, 12) if b == 6 else (0, 4):
            S.kick(b, s, 0.62)
    for s in range(0, 16, 2):
        S.snare(6, s, 0.2 + 0.01 * s, pitch=s * 0.2, sp=0.45)
    for s in range(8):
        S.snare(7, s, 0.17 + 0.015 * s, pitch=3 + s * 0.5, sp=0.45)
    mix.add("fx", rush(2.5 * BAR, 0.65), T(5, 8))
    pre_drop(mix, DROP)

    # =========================================================== DROP (bars 8-15)
    mix.add("fx", P.impact(0.9), T(DROP))
    mix.add("fx", splash(1.0, big=True), T(DROP), rev=0.3)
    S.cb_hook(hook(DROP) + hook(12, ("b0", "b1", "b2", "b3v")))
    S.subline(DROP, OUTRO, drain_at=(19, 8))
    for b in range(DROP, 19):
        S.pad(b, gain=0.45)
    S.pad(19, gain=0.45, steps=8)
    for b in range(DROP, FLOW):
        pos = (b - DROP) % 4
        S.kick(b, 0)
        S.kick(b, {0: 3, 1: 10, 2: 3, 3: 6}[pos], 0.85)
        S.snare(b, 8)
        if b == 15:
            for s, v in ((12, 0.32), (13, 0.38), (14, 0.46), (15, 0.56)):
                S.snare(b, s, v, pitch=2, sp=0.7)
        for s in range(0, 16, 2):
            S.tick(b, s, 0.9 if s % 4 == 2 else 0.5, pan=0.2)
            if b >= 12:
                S.tick(b, s + 1, 0.3, pan=-0.3)
        if b >= 12:
            S.rain(b, 0.2, 0.6)

    # =========================================================== FLOW + DRAIN (bars 16-19)
    mix.add("fx", splash(0.8, big=True), T(FLOW), rev=0.3)
    flow(S, FLOW, OUTRO - 1, drain_bar=19)
    S.lead(hook(FLOW), gain=0.9, max_step=(19, 8))
    for b in range(FLOW, OUTRO):
        pos = (b - FLOW) % 4
        S.kick(b, 0)
        if b < 19:
            S.kick(b, {0: 3, 1: 10, 2: 3}[pos], 0.85)
        S.snare(b, 8, big=b == 19)
        for s in range(0, 16 if b < 19 else 8):
            S.tick(b, s, (0.9 if s % 4 == 2 else 0.5) if s % 2 == 0 else 0.3, pan=0.2 if s % 2 == 0 else -0.3)

    # =========================================================== OUTRO (bars 20-23)
    mix.add("fx", splash(0.5, big=True), T(OUTRO), rev=0.5)
    S.pad(20, gain=0.7)
    S.pad(21, gain=0.7)
    sig = P.supersaw(CH["E"]["pad"], 2 * BAR, voices=5, spread=0.14, att=0.1, rel=2.5, cutoff=5000)
    mix.add("pad", sig, T(22), gain=0.7, rev=0.5)
    S.lead([(20, 0, 3, 85), (20, 3, 3, 83), (20, 6, 2, 80), (20, 8, 8, 76),
            (21, 0, 6, 87), (21, 6, 2, 85), (21, 8, 8, 83), (22, 0, 24, 88)], gain=0.85)
    for b in range(20, 23):
        S.rain(b, 0.3 - 0.08 * (b - 20), 0.6)
    for b in (20, 21):
        for s in range(2, 16, 4):
            S.tick(b, s, 0.35 - 0.1 * (b - 20), pan=0.2)
    S.subline(20, 22, gain=0.5)
    mix.add("amb", brook(4 * BAR + TAIL, rate=18), T(OUTRO))
    return mix, S.kicks, S.snares


def pre_drop(mix, drop_bar):
    """Half-bar gap before a drop: one big drop, four bubbles rising, a reversed splash sucking in."""
    b = drop_bar - 1
    mix.add("fx", droplet(float(mtof(71)), decay=0.25, chirp=0.9, tau=0.02, bright=0.2), T(b, 8), rev=0.5, dly=0.4)
    for j, nt in enumerate((71, 75, 78, 83)):
        mix.add("fx", 0.6 * droplet(float(mtof(nt)), decay=0.08, chirp=1.0, tau=0.015, bright=0.15), T(b, 12 + j), rev=0.3, dly=0.2)
    mix.add("fx", splash(0.7, big=True)[:, ::-1].copy(), T(drop_bar) - 1.0)


def flow(S, b0, last_bar, drain_bar=None, rate=14.0):
    """Legato 'flow': 8th-note chords rising and falling like a wave, each gliding out of the last.
    If drain_bar is given, its second half becomes a two-octave whirlpool dive."""
    WAVE = [0, 1, 2, 3, 4, 3, 2, 1]
    prev = None
    for b in range(b0, last_bar + 1):
        tops = tones_in(S.seq[b], 63, 78)
        for j in range(4 if b == drain_bar else 8):
            v0, v1 = Session.VOWELS[(b + j) % len(Session.VOWELS)]
            sig, prev = liquid_stab(S.seq[b], tops[WAVE[j] % len(tops)], 2 * STEP, vel=1.0 if j % 4 == 0 else 0.85,
                                    prev=prev, rate=rate, v0=v0, v1=v1, bright=1.1)
            S.mix.add("cb", sig, T(b, 2 * j), rev=0.05)
    if drain_bar is not None:
        sig, _ = liquid_stab(S.seq[drain_bar], 71, 8 * STEP, prev=prev, rate=10.0, v0="o", v1="u", drain=True)
        S.mix.add("cb", sig, T(drain_bar, 8), rev=0.15)
    return prev


# =====================================================================================
#  MIX
# =====================================================================================
CAL = {
    "kick": ((8, 12), -15.0), "snare": ((8, 12), -17.0), "hats": ((8, 12), -30.5), "sub": ((8, 12), -15.5),
    "cb": ((8, 12), -14.0), "pad": ((8, 12), -25.0), "lead": ((4, 7), -21.0), "rain": ((12, 16), -31.0),
    "amb": ((0, 4), -30.0), "fx": ((4, 8), -25.0), "rev": ((0, 4), -25.0), "room": ((8, 12), -25.0),
    "dly": ((4, 8), -27.0),
}
SURF = [(0, 450), (3.5, 650), (6, 14000), (8, 19000), (20, 19000), (23, 2500), (24.5, 1200)]


def automation(points):
    """Exponential interpolation of (bar, value) breakpoints into a per-sample curve."""
    t = np.arange(P.N) / SR
    xs = np.array([T(b) for b, _ in points])
    return np.exp(np.interp(t, xs, np.log([v for _, v in points])))


def mixdown(mix, kicks, snares, cal=CAL, surf=SURF, ref=(8, 12)):
    B = mix.buses
    t = np.arange(P.N) / SR

    # underwater -> surfacing -> sinking: one low-pass sweep across the melodic/ambient layers
    curve = automation(surf)
    for name in ("pad", "lead", "rain", "amb", "keys", "vox"):
        if name in B:
            B[name] = np.vstack([filt(B[name][c], curve, 1.0, 0) for c in range(2)])

    for name, depth, rel in (("pad", 0.7, 0.2), ("cb", 0.55, 0.16), ("sub", 1.0, 0.11), ("lead", 0.3, 0.18),
                             ("rain", 0.3, 0.15), ("amb", 0.3, 0.2), ("keys", 0.35, 0.18), ("vox", 0.3, 0.15)):
        if name in B:
            B[name] *= P.duck_env(kicks, depth, rel)
    B["cb"] *= P.duck_env(snares, 0.3, 0.1)

    # liquid colorbass bus: high-pass, slow stereo flanger (wet sheen), then OTT
    B["cb"] = signal.sosfilt(sos("highpass", 90, 2), B["cb"])
    for c in range(2):
        d = 0.8 + 2.4 * (0.5 + 0.5 * np.sin(2 * np.pi * t / (2 * BAR) + c * np.pi / 2))
        B["cb"][c] = flanger(np.ascontiguousarray(B["cb"][c]), d, 0.5, 0.35)
    B["cb"] = P.ott(B["cb"], 0.7)
    B["cb"] = peq(peq(B["cb"], 1800.0, 6.0, 0.7), 320.0, -3.0, 1.0)     # presence up, boxiness down
    # pads: slow phaser = the shimmer of light through water
    for c in range(2):
        fc = 300 * 10 ** (1.0 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.18 * t + c * np.pi / 2)))
        B["pad"][c] = phaser(np.ascontiguousarray(B["pad"][c]), fc, 4, 0.4, 0.5)
    B["sub"] = signal.sosfilt(sos("lowpass", 160, 2), 0.5 * (B["sub"][0] + B["sub"][1]))[None, :].repeat(2, 0)
    B["rain"] = signal.sosfilt(sos("highpass", 400, 2), B["rain"])
    if "vox" in B:
        B["vox"] = signal.sosfilt(sos("highpass", 250, 2), B["vox"])

    print("  reverb...")
    hall = P.make_ir(3.0, 3.5, 0.03, 6500, 11)
    room = P.make_ir(0.6, 0.9, 0.008, 9000, 12)
    B["rev"] = signal.sosfilt(sos("highpass", 220), P.convolve(B["rev"], hall))
    B["room"] = signal.sosfilt(sos("highpass", 180), P.convolve(B["room"], room))
    B["dly"] = P.pingpong(B["dly"], d=0.3, fb=0.5, taps=8)
    pump = P.duck_env(kicks, 0.35, 0.22)
    B["rev"] *= pump
    B["dly"] *= pump

    for name, ((b0, b1), target) in cal.items():
        B[name] *= 10 ** ((target - P.rms_db(B[name], b0, b1)) / 20)
    mixdown.buses = B
    master = sum(B.values())
    master = signal.sosfilt(sos("highpass", 28, 2), master)
    master *= 10 ** ((-17.0 - P.rms_db(master, *ref)) / 20)
    master *= P.comp_gain(master[0], master[1], -14.0, 2.0, -200.0, 1.0, 0.0, 0.01, 0.15, -200.0)
    drive = 1.0
    for _ in range(4):
        drive *= 10 ** ((-9.5 - P.lufs(P.limiter(P.softclip(master * drive)))) / 20)
    y = P.limiter(P.softclip(master * drive))
    fade = int(1.5 * SR)
    y[:, -fade:] *= np.linspace(1, 0, fade) ** 2
    return y, drive


def main():
    os.makedirs(P.OUT, exist_ok=True)
    t0 = time.time()
    print("composing + synthesizing...")
    mix, kicks, snares = compose()
    print(f"  {time.time() - t0:.1f}s")
    print("mixing + mastering...")
    y, drive = mixdown(mix, kicks, snares)
    assert np.all(np.isfinite(y))
    sf.write(os.path.join(P.OUT, NAME + ".wav"), y.T, SR, subtype="PCM_24")
    sf.write(os.path.join(P.OUT, NAME + ".mp3"), y.T, SR, format="MP3", subtype="MPEG_LAYER_III")
    P.overview_png(y, os.path.join(P.OUT, NAME + "_overview.png"), sections=SECTIONS,
                   title="TIDEPOOL  -  150 BPM liquid colorbass  -  E major", color="#5ad1ff")
    print(f"duration {y.shape[1] / SR:.1f}s | peak {20 * np.log10(np.abs(y).max()):.2f} dBFS | "
          f"integrated {P.lufs(y):.1f} LUFS | drive {20 * np.log10(drive):+.1f} dB | {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
