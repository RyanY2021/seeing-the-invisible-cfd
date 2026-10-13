"""
SEEING THE INVISIBLE v2 — score.  "Tidepool (CFD edit)": liquid colorbass softened for a 4:44 explainer film.

120 BPM (1 bar = 2 s = 48 video frames), E major, 142 bars + tail. Built on the Tidepool water instruments
(tidepool.py) and the Prism Arcade DSP engine (prism_arcade.py), both copied from D:/Creative/Colorbass Test.

Softer than Tidepool: no impacts or heavy drops, soft kick (no click), snaps instead of big snares, colorbass
stabs filtered and lightly compressed, master at -14 LUFS. Keeps the flow: droplet plinks, kalimba, babbling
brook, gliding chords, droplet hi-hats. Clawd's world (inside the computer, Act III) adds an 8-bit chip voice.

    python score_v2.py   ->  audio/score_v2.wav (48 kHz, 24-bit) + audio/score_v2_overview.png
"""
import os
import sys
import time

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prism_arcade as P  # noqa: E402
import tidepool as TP  # noqa: E402
from prism_arcade import SR, STEP, BAR, T, mtof, sos  # noqa: E402
from tidepool import CH, LOOP, hook, droplet, drop_lead, brook, splash, rush, liquid_stab, tones_in, flow  # noqa: E402

N_BARS = 142
TAIL = 6.0
P.N = int((N_BARS * BAR + TAIL) * SR)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "audio")
NAME = "score_v2"
rng = TP.rng

DEEP = ["C#m", "A", "E/G#", "B", "C#m", "A", "C", "B"]
SEQ = (LOOP * 3 + ["A", "B"]                     # 0   prologue
       + LOOP * 2                                # 14  I   why see it
       + LOOP * 7                                # 22  II  the rules
       + LOOP * 6                                # 50  III the computer's trick
       + ["C#m", "A", "E/G#", "B", "C", "B"]     # 74      nature agrees
       + LOOP + ["A", "B"]                       # 80      resolution & cost
       + DEEP * 2 + ["C#m", "A", "C", "B"]       # 86  IV  turbulence
       + ["A", "B"] + LOOP * 5 + ["A", "B"]      # 106 V   everywhere
       + LOOP * 2 + ["A", "B", "E", "E"])        # 130 VI  close
assert len(SEQ) == N_BARS, len(SEQ)

SECTIONS = [(0, "Prologue"), (10, "Title"), (14, "I why"), (22, "II rules"), (42, "equations"),
            (50, "III computer"), (66, "time steps"), (74, "nature"), (80, "cost"), (86, "IV turbulence"),
            (96, "models"), (106, "V everywhere"), (130, "VI close")]
H2 = ("b0", "b1", "b2", "b3v")
VOWELS_B = [("o", "a"), ("u", "e"), ("a", "o"), ("o", "i"), ("u", "a")]
DEEP_MEL = [(b + 54, s, d, m) for (b, s, d, m) in [
    (32, 0, 6, 80), (32, 6, 2, 83), (32, 8, 8, 87), (33, 0, 6, 85), (33, 6, 2, 83), (33, 8, 4, 80), (33, 12, 4, 76),
    (34, 0, 8, 78), (34, 8, 4, 80), (34, 12, 4, 83), (35, 0, 10, 78), (35, 10, 2, 80), (35, 12, 4, 83),
    (36, 0, 6, 88), (36, 6, 2, 87), (36, 8, 8, 83), (37, 0, 6, 85), (37, 6, 2, 83), (37, 8, 4, 80), (37, 12, 4, 81),
    (38, 0, 8, 83), (38, 8, 4, 79), (38, 12, 4, 76), (39, 0, 8, 78), (39, 8, 8, 75)]]
OUTRO_END = [(136, 0, 3, 85), (136, 3, 3, 83), (136, 6, 2, 80), (136, 8, 8, 76),
             (137, 0, 6, 87), (137, 6, 2, 85), (137, 8, 8, 83), (138, 0, 48, 88)]


# =====================================================================================
#  SOFT INSTRUMENTS
# =====================================================================================
def soft_kick(vel=1.0):
    """round, clickless kick: just the pitched body, gently saturated and low-passed"""
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    f = 46.0 + 95.0 * np.exp(-t / 0.035) + 140.0 * np.exp(-t / 0.006)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.26)
    body = np.tanh(1.4 * body) / np.tanh(1.4)
    body = signal.sosfilt(sos("lowpass", 1800), body)
    body[:48] *= np.linspace(0, 1, 48)
    body[-int(0.05 * SR):] *= np.linspace(1, 0, int(0.05 * SR))
    return body * vel


def kalimba(note, vel=1.0):
    """thumb-piano pluck (from tidepool_full.py)"""
    f = float(mtof(note))
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(f * 2.0 ** (-0.12 * np.exp(-t / 0.006))) / SR
    y = (np.sin(ph) + 0.18 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / 0.025)
         + 0.08 * np.sin(2 * ph) * np.exp(-t / 0.15))
    env = (1 - np.exp(-t / 0.0007)) * np.exp(-t / 0.28)
    env[-256:] *= np.linspace(1, 0, 256)
    return y * env * vel


def soft_stab(chord, top, dur, vel=1.0, prev=None, **kw):
    """Tidepool's liquid colorbass stab, darker and rounder (no screaming top end)"""
    kw.setdefault("bright", 0.65)
    sig, voices = liquid_stab(chord, top, dur, vel=vel, prev=prev, **kw)
    sig = signal.sosfilt(sos("lowpass", 3800, 2), sig)
    return sig, voices


class Session(TP.Session):
    def kick(self, b, s, v=1.0):
        self.mix.add("kick", soft_kick(v), T(b, s))
        self.kicks.append((T(b, s), v * 0.6))

    def snare(self, b, s, v=1.0, pitch=0.0, sp=0.5, big=False):
        """a soft snap + a small water splash instead of a big snare"""
        t = T(b, s)
        sn = 0.25 * P.snare(v * 0.6, pitch)
        sp_ = P.snap(v) * 0.9
        sn[:sp_.shape[0]] += sp_
        self.mix.add("snare", sn, t, rev=0.15, room=0.3)
        self.mix.add("snare", splash(v * sp, big and v > 0.5), t, rev=0.25, room=0.2)
        self.snares.append((t, v * 0.5))

    def cb_hook(self, events, rate=11.0, bright=0.65, vowels=None, final_bend=0.0):
        vowels = vowels or self.VOWELS
        prev = None
        for i, (b, s, d, m) in enumerate(events):
            dur = d * STEP * (0.85 if d <= 2 else 0.92)
            v0, v1 = vowels[i % len(vowels)]
            sig, voices = soft_stab(self.seq[b], m - 12, dur, vel=0.9 if s == 0 else 0.78,
                                    prev=None if s == 0 else prev, rate=rate, v0=v0, v1=v1, bright=bright,
                                    bend=final_bend if i == len(events) - 1 else 0.0)
            self.mix.add("cb", sig, T(b, s), rev=0.08)
            prev = voices
        return prev

    def kal(self, b, gain=1.0, pattern=(0, 2, 1, 3, 2, 4, 3, 1), octave=12):
        p = CH[self.seq[b]]["pad"]
        tones = sorted(p[1:]) + [p[1] + 12]
        for j, k in enumerate(pattern):
            self.mix.add("keys", kalimba(tones[k % len(tones)] + octave, gain * (1.0 if j % 4 == 0 else 0.72)),
                         T(b, 2 * j), pan=0.45 * np.sin(1.3 * j), rev=0.3, dly=0.25)

    def chip_arp(self, b, gain=1.0, steps=16, rate=2):
        """8-bit arpeggio through the chord (Clawd's pixel world)"""
        tones = tones_in(self.seq[b], 76, 92)
        order = tones + tones[-2:0:-1]
        for j, s in enumerate(range(0, steps, rate)):
            nt = order[j % len(order)]
            sig = P.chip(nt, STEP * rate * 0.7, duty=0.25, vib=0.0, dec=0.08, sus=0.3)
            self.mix.add("chip", sig * gain * (1.0 if j % 4 == 0 else 0.75), T(b, s), pan=0.3 * (-1) ** j,
                         rev=0.15, dly=0.2)

    def chip_lead(self, events, gain=1.0):
        prev = None
        for (b, s, d, m) in events:
            sig = P.chip(m, d * STEP * 0.92, duty=0.5, vib=0.2, prev=prev, dec=0.3, sus=0.55)
            self.mix.add("chip", sig * gain, T(b, s), rev=0.25, dly=0.3)
            prev = m

    def gliss(self, t, chord, up=True, dur=0.6, gain=0.7):
        tones = tones_in(chord, 76, 100)
        tones = tones if up else tones[::-1]
        for j, nt in enumerate(tones):
            x = j / len(tones)
            d = droplet(float(mtof(nt)), decay=0.08, chirp=0.4, tau=0.006, bright=0.1)
            self.mix.add("rain", d * gain * (0.6 + 0.4 * x), t + dur * x, pan=-0.7 + 1.4 * x, rev=0.35, dly=0.2)

    def siren(self, b, note, bars, v0="u", v1="o", gain=0.5):
        self.mix.add("vox", P.vox(note, bars * BAR * 0.95, v0, v1, scoop=-3.0), T(b), gain=gain, rev=0.6, dly=0.2)

    def chop(self, b, s, note, dur, v0, v1, gain=0.8):
        self.mix.add("vox", P.vox(note, dur, v0, v1, scoop=-2.0), T(b, s), gain=gain, rev=0.3, dly=0.2)

    def groove(self, b, pos, ticks16=False, snap_v=0.8, kick_v=0.85):
        """half-time liquid groove: kick on 1 (+ a pickup), snap on 3, droplet hats on 8ths"""
        self.kick(b, 0, kick_v)
        self.kick(b, {0: 10, 1: 6, 2: 10, 3: 14}[pos], kick_v * 0.7)
        self.snare(b, 8, snap_v)
        for s in range(0, 16, 2):
            self.tick(b, s, 0.7 if s % 4 == 2 else 0.4, pan=0.2)
            if ticks16:
                self.tick(b, s + 1, 0.22, pan=-0.3)

    def roll(self, b0, bars=2, v0=0.15, v1=0.35):
        hits = [(b0 + i, k * 16 / div, i) for i, div in enumerate((8, 16)[:bars]) for k in range(div)]
        for j, (b, s, i) in enumerate(hits):
            x = j / (len(hits) - 1)
            self.snare(b, s, v0 + (v1 - v0) * x, pitch=4 * x ** 2, sp=0.3)


def rise_droplets(S, b):
    """the gentle 'pre-drop': half a bar of rising bubbles instead of a gap + impact"""
    for j, nt in enumerate((71, 75, 78, 83, 87)):
        S.mix.add("fx", 0.5 * droplet(float(mtof(nt)), decay=0.09, chirp=1.0, tau=0.015, bright=0.15),
                  T(b, 8 + 1.5 * j), rev=0.35, dly=0.2)


# =====================================================================================
#  COMPOSITION
# =====================================================================================
def compose():
    S = Session(SEQ)
    mix = S.mix

    # ------------------------------------------------ PROLOGUE (0-13): underwater, the invisible
    mix.add("amb", brook(14 * BAR + 0.5, rate=16), 0.0)
    for b in range(0, 14):
        S.pad(b, gain=0.55, att=3.5 if b == 0 else 0.15)
    S.siren(2, 64, 2, gain=0.35)
    S.siren(6, 68, 2, "u", "o", gain=0.35)
    S.lead(hook(4), gain=0.5)
    for b in range(6, 14):
        S.kal(b, 0.4 + 0.03 * (b - 6))
    mix.add("fx", rush(1.2 * BAR, 0.22), T(7, 4))                 # V02: Clawd's swipe stirs the smoke
    S.gliss(T(9, 8), "B", up=True, dur=0.9, gain=0.55)            # into the title
    mix.add("fx", splash(0.3, big=True), T(10), rev=0.5)
    S.siren(10, 71, 4, "o", "a", gain=0.4)
    for b in (11, 12, 13):
        S.rain(b, 0.15, 0.5)
    S.subline(12, 14, gain=0.35)

    # ------------------------------------------------ I (14-21): surfacing — why see it
    mix.add("amb", brook(8 * BAR + 0.5, rate=12, wash=0.08), T(14))
    for b in range(14, 22):
        S.pad(b, gain=0.5)
        S.kal(b, 0.65)
        S.rain(b, 0.12 + 0.02 * (b - 14), 0.6)
    S.lead(hook(14) + hook(18, H2), gain=0.75)
    S.subline(14, 22, gain=0.5)
    for b in range(16, 22):
        S.kick(b, 0, 0.65)
        S.kick(b, 8, 0.55)
        for s in range(2, 16, 4):
            S.tick(b, s, 0.5, pan=0.2)
    for b in range(15, 20):                                        # the five cards pop in on the downbeats
        S.mix.add("fx", 0.45 * droplet(float(mtof(83 + 2 * (b - 15))), decay=0.07, chirp=0.9, tau=0.01),
                  T(b), rev=0.3, dly=0.25)
    rise_droplets(S, 21)

    # ------------------------------------------------ II (22-49): the rules — groove 1
    mix.add("fx", splash(0.4, big=True), T(22), rev=0.3)
    S.cb_hook(hook(22) + hook(26, H2))
    S.cb_hook(hook(30) + hook(34, H2))
    S.cb_hook(hook(38) + hook(42, H2), final_bend=-5.0)
    S.lead(hook(30) + hook(34, H2), gain=0.75)
    S.subline(22, 48)
    for b in range(22, 48):
        S.pad(b, gain=0.38)
        S.groove(b, (b - 22) % 4, ticks16=b >= 34)
        if b >= 34:
            S.rain(b, 0.12, 0.5)
    for b, ch in ((26, "A"), (30, "A"), (34, "A"), (38, "A")):     # each new rule gets a little water-harp
        S.gliss(T(b) - 0.45, ch, up=True, dur=0.45, gain=0.55)
    for b in range(42, 48):                                        # equations assemble: kalimba sparkle
        S.kal(b, 0.5, octave=24)
    S.roll(46, 2)
    mix.add("fx", rush(2 * BAR, 0.35), T(46))
    # 48-49: the equations shatter into shards, then a breath
    t_crack = T(48, 14 / 3)                                     # V11: the slab cracks at shot frame 14
    mix.add("fx", splash(0.55, big=True), t_crack, rev=0.4)
    for j in range(14):
        d = droplet(rng.uniform(1800, 5200), decay=rng.uniform(0.02, 0.05), chirp=0.8, tau=0.006)
        mix.add("fx", 0.4 * d, t_crack + rng.uniform(0, 0.8), pan=rng.uniform(-0.9, 0.9), rev=0.4)
    S.pad(48, gain=0.4, steps=32, rel=1.5)
    S.siren(48, 76, 2, "o", "u", gain=0.3)
    rise_droplets(S, 49)

    # ------------------------------------------------ III (50-85): inside the computer
    mix.add("fx", P.downlifter(1.5 * BAR, 0.3), T(50))
    for b in range(50, 74):
        S.pad(b, gain=0.42)
        S.chip_arp(b, 0.55 if b < 66 else 0.45)
    for b in range(50, 66):
        S.kal(b, 0.45)
    S.chip_lead(hook(54) + hook(58, H2), gain=0.55)                 # the hook in 8-bit: Clawd's theme
    S.subline(54, 74, gain=0.75)
    for b in range(54, 66):
        S.kick(b, 0, 0.7)
        S.kick(b, 8, 0.6)
        S.snare(b, 12, 0.35, sp=0.2) if b % 2 else None
        for s in range(2, 16, 4):
            S.tick(b, s, 0.45, pan=0.2)
    # 66-73: time steps — a steady 16th-note droplet clock, four-on-the-floor, then the swirls emerge (flow)
    for b in range(66, 74):
        for s in range(16):
            S.tick(b, s, 0.55 if s % 4 == 0 else 0.3, pan=0.25 * np.sin(s))
        for s in (0, 4, 8, 12):
            S.kick(b, s, 0.6 + 0.03 * (b - 66))
        if b >= 68:
            S.snare(b, 8, 0.5)
    S.lead(hook(66), gain=0.6)
    flow(S, 70, 73, rate=12.0)
    # 74-79: nature agrees — breakdown under the satellite photo
    mix.add("fx", splash(0.45, big=True), T(74), rev=0.6)
    mix.add("amb", brook(6 * BAR + 0.5, rate=10, wash=0.1), T(74))
    for b in range(74, 80):
        S.pad(b, gain=0.6)
    S.siren(74, 68, 2, "u", "a", gain=0.45)
    S.siren(76, 71, 2, "o", "a", gain=0.45)
    S.siren(78, 67, 2, "u", "o", gain=0.4)
    S.lead([(74, 0, 6, 80), (74, 6, 2, 83), (74, 8, 8, 87), (75, 0, 16, 85), (76, 0, 6, 88), (76, 6, 2, 87),
            (76, 8, 8, 83), (77, 0, 16, 80), (78, 0, 8, 79), (78, 8, 8, 76), (79, 0, 16, 78)], gain=0.7)
    S.gliss(T(74), "C#m")
    S.gliss(T(78), "C", up=False)
    # 80-85: resolution & cost — pixel groove returns, lighter
    for b in range(80, 86):
        S.pad(b, gain=0.42)
        S.chip_arp(b, 0.5)
        S.groove(b, (b - 80) % 4, snap_v=0.55, kick_v=0.7)
    S.chip_lead(hook(80, ("b0", "b1")), gain=0.45)
    S.subline(80, 86, gain=0.7)
    rise_droplets(S, 85)

    # ------------------------------------------------ IV (86-105): turbulence — the deep
    mix.add("fx", P.downlifter(2 * BAR, 0.35), T(86))
    mix.add("amb", brook(20 * BAR + 0.5, rate=12), T(86))
    for b in range(86, 106):
        S.pad(b, gain=0.5)
        S.kal(b, 0.75 if b < 96 else 0.55)
    S.lead(DEEP_MEL[:13], gain=0.75)                               # 86-89
    S.lead([(b + 4, s, d, m) for (b, s, d, m) in DEEP_MEL], gain=0.75)   # 90-97 (full phrase)
    for b, nt, v1 in ((86, 68, "o"), (90, 71, "a"), (94, 67, "u")):
        S.siren(b, nt, 2, "u", v1, gain=0.4)
    S.gliss(T(86), "C#m")
    S.gliss(T(94), "C", up=False)
    S.subline(90, 106, gain=0.55)
    for b in range(90, 96):                                        # heartbeat under the swirls
        S.kick(b, 0, 0.55)
        S.kick(b, 2, 0.38)
    for b in range(96, 106):                                       # models: light ticking, a camera's patience
        S.kick(b, 0, 0.55)
        S.snare(b, 8, 0.3, sp=0.3)
        for s in range(2, 16, 4):
            S.tick(b, s, 0.4, pan=0.2)
    S.lead(hook(98) + hook(102, H2), gain=0.55)

    # ------------------------------------------------ V (106-129): everywhere — the fullest, still soft
    for b in (106, 107):
        S.pad(b, gain=0.5, steps=16 if b == 106 else 8)
        S.rain(b, 0.3, 0.7)
    S.roll(106, 2, 0.12, 0.3)
    mix.add("fx", rush(2 * BAR, 0.4), T(106))
    rise_droplets(S, 107)
    for b in (108, 112, 116, 120, 124):                             # one soft splash per application shot
        mix.add("fx", splash(0.45, big=True), T(b), rev=0.3)
    S.cb_hook(hook(108, H2) + hook(112), rate=13.0, bright=0.75, vowels=VOWELS_B)
    S.lead(hook(108) + hook(112, H2), gain=0.75)
    for i, (b, s, d, m) in enumerate(hook(108) + hook(112, H2)):
        if d >= 3:
            S.chop(b, s, m - 12, d * STEP * 0.85, *VOWELS_B[i % len(VOWELS_B)], gain=0.6)
    flow(S, 116, 119, rate=13.0)
    S.lead(hook(116), gain=0.75)
    # 120-123: waterfall cascades (triplets tumbling down, each gliding from the last)
    prev = None
    for b in range(120, 124):
        tones = sorted(tones_in(SEQ[b], 63, 82), reverse=True)
        for j in range(12):
            v0, v1 = TP.Session.VOWELS[(b + j) % len(TP.Session.VOWELS)]
            sig, prev = soft_stab(SEQ[b], tones[j % 6 + j // 6], BAR / 12 * 0.95, vel=0.85 if j % 6 == 0 else 0.7,
                                  prev=None if j % 6 == 0 else prev, rate=15.0, v0=v0, v1=v1, bright=0.8)
            mix.add("cb", sig, T(b, j * 16 / 12), rev=0.08)
    S.gliss(T(120), "A", up=False)
    S.gliss(T(122), "C#m", up=False)
    # 124-127: finale hook, then a gentle drain
    fin = S.cb_hook(hook(124, ("b0", "b1", "b2")) + [(127, 0, 6, 85), (127, 6, 2, 83)], rate=13.0, bright=0.75,
                    vowels=VOWELS_B)
    S.lead(hook(124, ("b0", "b1", "b2")) + [(127, 0, 6, 85), (127, 6, 2, 83)], gain=0.8)
    S.chop(124, 0, 73, 0.6, "o", "a", gain=0.6)
    sig, _ = soft_stab("B", 71, 8 * STEP, prev=fin, rate=10.0, v0="o", v1="u", drain=True)
    mix.add("cb", sig * 0.6, T(127, 8), rev=0.2)
    for b in range(108, 128):
        S.pad(b, gain=0.4)
        if b < 120:
            S.groove(b, (b - 108) % 4, ticks16=b >= 112)
        else:
            S.kick(b, 0)
            S.kick(b, 10 * 16 / 12, 0.6)
            S.snare(b, 8, 0.7)
            for j in range(12):
                S.tick(b, j * 16 / 12, 0.6 if j % 3 == 0 else 0.3, pan=0.25 * (-1) ** j)
        if b >= 112:
            S.rain(b, 0.15, 0.5)
    S.subline(108, 128, drain_at=(127, 8), drain_semis=-12.0)
    for b in (128, 129):                                           # breath before the close
        S.pad(b, gain=0.55)
        S.kal(b, 0.6)
    S.siren(128, 76, 2, "o", "u", gain=0.35)

    # ------------------------------------------------ VI (130-141): close — sinking back, resolving to E
    mix.add("fx", splash(0.35, big=True), T(130), rev=0.6)
    mix.add("amb", brook(12 * BAR + TAIL, rate=14), T(130))
    for b in range(130, 138):
        S.pad(b, gain=0.6)
        S.kal(b, 0.7 - 0.05 * (b - 130))
    S.pad(138, gain=0.65, steps=64, att=0.1, rel=4.0)
    S.lead(hook(130) + hook(134, H2)[:6], gain=0.65)
    S.lead(OUTRO_END, gain=0.75)
    S.siren(136, 68, 2, "o", "u", gain=0.4)
    for b in range(130, 138):
        S.rain(b, 0.2 - 0.02 * (b - 130), 0.55)
    for b in range(130, 134):
        S.kick(b, 0, 0.5)
        S.snare(b, 8, 0.3, sp=0.4)
        for s in range(2, 16, 4):
            S.tick(b, s, 0.3, pan=0.2)
    S.subline(130, 138, gain=0.45)
    S.gliss(T(138, 4), "E", up=True, dur=1.2, gain=0.4)
    S.chip_lead([(141, 12, 1, 88), (141, 13, 1, 92), (141, 14, 2, 95)], gain=0.3)   # Clawd's goodbye blip (peek)
    return mix, S.kicks, S.snares


# =====================================================================================
#  MIX (softer master than Tidepool: gentle OTT, light pumping, -14 LUFS)
# =====================================================================================
CAL = {
    "kick": ((108, 116), -18.0), "snare": ((108, 116), -21.0), "hats": ((108, 116), -32.0),
    "sub": ((108, 116), -17.5), "cb": ((108, 116), -18.0), "pad": ((108, 116), -25.0), "lead": ((30, 38), -22.0),
    "rain": ((112, 120), -31.0), "amb": ((0, 8), -29.0), "fx": ((46, 50), -26.0), "rev": ((0, 14), -25.0),
    "room": ((108, 116), -26.0), "dly": ((14, 22), -28.0), "keys": ((86, 96), -25.5), "vox": ((74, 80), -24.0),
    "chip": ((54, 62), -26.0),
}
SURF = [(0, 420), (5, 600), (9.6, 800), (10, 2600), (13.5, 3200), (16, 17000), (49.5, 17000), (50, 1500),
        (52, 14000), (86, 14000), (86.5, 5000), (90, 9000), (106, 12000), (108, 17000), (130, 17000),
        (136, 3000), (142, 900)]


def mixdown(mix, kicks, snares):
    B = mix.buses
    t = np.arange(P.N) / SR
    curve = TP.automation(SURF)
    for name in ("pad", "lead", "rain", "amb", "keys", "vox", "chip"):
        if name in B:
            B[name] = np.vstack([P.filt(B[name][c], curve, 1.0, 0) for c in range(2)])
    for name, depth, rel in (("pad", 0.35, 0.2), ("cb", 0.3, 0.16), ("sub", 0.6, 0.12), ("lead", 0.15, 0.18),
                             ("rain", 0.15, 0.15), ("amb", 0.15, 0.2), ("keys", 0.2, 0.18), ("vox", 0.15, 0.15),
                             ("chip", 0.2, 0.15)):
        if name in B:
            B[name] *= P.duck_env(kicks, depth, rel)
    B["cb"] = signal.sosfilt(sos("highpass", 90, 2), B["cb"])
    for c in range(2):
        d = 0.8 + 2.4 * (0.5 + 0.5 * np.sin(2 * np.pi * t / (2 * BAR) + c * np.pi / 2))
        B["cb"][c] = TP.flanger(np.ascontiguousarray(B["cb"][c]), d, 0.45, 0.3)
    B["cb"] = P.ott(B["cb"], 0.3)
    for c in range(2):
        fc = 300 * 10 ** (1.0 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.15 * t + c * np.pi / 2)))
        B["pad"][c] = TP.phaser(np.ascontiguousarray(B["pad"][c]), fc, 4, 0.4, 0.45)
    B["sub"] = signal.sosfilt(sos("lowpass", 150, 2), 0.5 * (B["sub"][0] + B["sub"][1]))[None, :].repeat(2, 0)
    B["rain"] = signal.sosfilt(sos("highpass", 400, 2), B["rain"])
    B["vox"] = signal.sosfilt(sos("highpass", 250, 2), B["vox"])
    B["chip"] = signal.sosfilt(sos("highpass", 300, 2), B["chip"])
    print("  reverb...")
    hall = P.make_ir(3.2, 3.8, 0.03, 6500, 11)
    room = P.make_ir(0.6, 0.9, 0.008, 9000, 12)
    B["rev"] = signal.sosfilt(sos("highpass", 220), P.convolve(B["rev"], hall))
    B["room"] = signal.sosfilt(sos("highpass", 180), P.convolve(B["room"], room))
    B["dly"] = P.pingpong(B["dly"], d=0.375, fb=0.45, taps=8)       # dotted 8th at 120 BPM
    pump = P.duck_env(kicks, 0.2, 0.25)
    B["rev"] *= pump
    B["dly"] *= pump
    for name, ((b0, b1), target) in CAL.items():
        if name in B:
            B[name] *= 10 ** ((target - P.rms_db(B[name], b0, b1)) / 20)
    mixdown.buses = B
    master = sum(B.values())
    master = signal.sosfilt(sos("highpass", 28, 2), master)
    master = P.shelf(master, 7500.0, -2.0)
    master *= 10 ** ((-19.0 - P.rms_db(master, 108, 116)) / 20)
    master *= P.comp_gain(master[0], master[1], -16.0, 1.6, -200.0, 1.0, 0.0, 0.015, 0.2, -200.0)
    drive = 1.0
    for _ in range(4):
        drive *= 10 ** ((-14.0 - P.lufs(P.limiter(P.softclip(master * drive, 0.8)))) / 20)
    y = P.limiter(P.softclip(master * drive, 0.8), ceiling=0.89)
    fade = int(3.0 * SR)
    y[:, -fade:] *= np.linspace(1, 0, fade) ** 2
    return y, drive


def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    print("composing + synthesizing...")
    mix, kicks, snares = compose()
    print(f"  {time.time() - t0:.1f}s  buses: {', '.join(mix.buses)}")
    print("mixing + mastering...")
    y, drive = mixdown(mix, kicks, snares)
    assert np.all(np.isfinite(y))
    sf.write(os.path.join(OUT, NAME + ".wav"), y.T, SR, subtype="PCM_24")
    P.SECTIONS = SECTIONS
    P.overview_png(y, os.path.join(OUT, NAME + "_overview.png"), sections=SECTIONS,
                   title="SEEING THE INVISIBLE v2  -  Tidepool (CFD edit)  -  120 BPM  -  E major", color="#ff9e6b")
    print(f"duration {y.shape[1] / SR:.1f}s | peak {20 * np.log10(np.abs(y).max()):.2f} dBFS | "
          f"integrated {P.lufs(y):.1f} LUFS | drive {20 * np.log10(drive):+.1f} dB | {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
