"""Shared paths and helpers for the CFD Intro project."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
CACHE = ROOT / "cache"
RENDERS = ROOT / "renders"
AUDIO = ROOT / "audio"
OUTPUT = ROOT / "output"
ASSETS = ROOT / "assets"
BLENDER_DIR = ROOT / "blender"
BLENDER_EXE = Path(os.environ.get("BLENDER_EXE", r"D:\Tools\Blender\blender.exe"))
FONTS = Path(r"C:\Windows\Fonts")

W, H, FPS = 1920, 1080, 24

FONT_TITLE = FONTS / "GillSansLightNova.ttf"
FONT_CAPTION = FONTS / "GeorgiaPro-Light.ttf"
FONT_CAPTION_IT = FONTS / "GeorgiaPro-LightItalic.ttf"
FONT_LABEL = FONTS / "GillSansLightNova.ttf"


def ffmpeg_exe() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def init_warp():
    """Import + init warp with its kernel cache kept inside the project."""
    import warp as wp

    cache = CACHE / "warp"
    cache.mkdir(parents=True, exist_ok=True)
    wp.config.kernel_cache_dir = str(cache)
    wp.config.quiet = True
    wp.init()
    return wp


def shot_dir(shot: str) -> Path:
    d = RENDERS / shot
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_dir(name: str) -> Path:
    d = CACHE / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_png16(path: Path, rgb: np.ndarray):
    """Save float RGB in [0,1] as 16-bit PNG (keeps dark gradients clean)."""
    import cv2

    a = np.clip(rgb, 0.0, 1.0)
    a = (a * 65535.0 + 0.5).astype(np.uint16)
    cv2.imwrite(str(path), a[..., ::-1])


def load_png(path: Path) -> np.ndarray:
    """Load 8/16-bit PNG as float32 RGB [0,1]."""
    import cv2

    a = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if a is None:
        raise FileNotFoundError(path)
    scale = 65535.0 if a.dtype == np.uint16 else 255.0
    a = a.astype(np.float32) / scale
    if a.ndim == 2:
        a = np.stack([a] * 3, -1)
    if a.shape[2] == 4:
        a = a[..., :3]
    return a[..., ::-1].copy()


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def run(cmd, **kw):
    print(">>", " ".join(str(c) for c in cmd))
    return subprocess.run([str(c) for c in cmd], check=True, **kw)
