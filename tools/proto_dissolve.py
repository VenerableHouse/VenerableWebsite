#!/usr/bin/env python3
"""Prototype the multiband dissolve, in the same maths the WebGL shader will use.

Three things separate this from a plain opacity cross-fade:

  1. Blending happens in LINEAR LIGHT. Alpha-blending gamma-encoded sRGB is the
     specific reason naive cross-fades go muddy and low-contrast at t=0.5.
  2. It is MULTIBAND (Burt-Adelson Laplacian pyramid). Ghosting is a
     high-frequency artefact -- two sets of eyes at 50% each. So coarse bands
     cross over slowly and smoothly, while fine bands switch fast, and never sit
     at 50/50 long enough to read as a double exposure.
  3. Fine bands are DITHERED IN TIME by a noise field, so each region switches at
     its own moment instead of the whole frame snapping together.
"""
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGES = os.path.join(HERE, os.pardir, 'ruddock', 'static', 'images')
OUT = '/tmp/blendproto'

LEVELS = 5

# Per-level transition shape, finest band first. `width` is how long the band
# takes to cross over, `jitter` is how far the noise field scatters each pixel's
# crossover in time. Fine bands: fast and heavily scattered. Coarse bands: a
# slow, clean, global fade.
BANDS = [
    # width, jitter
    (0.18, 0.70),   # finest detail: snaps, widely scattered
    (0.25, 0.55),
    (0.40, 0.35),
    (0.60, 0.18),
    (0.85, 0.06),   # coarsest detail
]
RESIDUAL_WIDTH = 1.0  # the blurred base image: plain smooth crossfade


def srgb_to_linear(x):
  x = x.astype(np.float32) / 255.0
  return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x):
  x = np.clip(x, 0.0, 1.0)
  s = np.where(x <= 0.0031308, x * 12.92, 1.055 * (x ** (1 / 2.4)) - 0.055)
  return np.clip(s * 255.0 + 0.5, 0, 255).astype(np.uint8)


def laplacian_pyramid(img, levels):
  """[fine ... coarse detail bands] + [residual]."""
  gauss = [img]
  for _ in range(levels):
    gauss.append(cv2.pyrDown(gauss[-1]))
  bands = []
  for i in range(levels):
    up = cv2.pyrUp(gauss[i + 1], dstsize=(gauss[i].shape[1], gauss[i].shape[0]))
    bands.append(gauss[i] - up)
  return bands, gauss[-1]


def collapse(bands, residual):
  out = residual
  for band in reversed(bands):
    out = cv2.pyrUp(out, dstsize=(band.shape[1], band.shape[0])) + band
  return out


def fractal_noise(shape, octaves=5, base=6, seed=7):
  """Smooth multi-octave value noise, normalised to [0, 1].

  Blobby rather than per-pixel: the image melts in organic patches at roughly
  face-to-torso scale, which suits a group photo better than a fine dither
  sparkle. Normalised by rank so the melt is perfectly uniform in time -- every
  crossover moment is equally represented, no dead stretches.
  """
  rng = np.random.default_rng(seed)
  h, w = shape
  acc = np.zeros(shape, np.float32)
  amp = 1.0
  for o in range(octaves):
    gh, gw = base * 2 ** o, int(base * 2 ** o * w / h)
    grid = rng.random((max(gh, 2), max(gw, 2))).astype(np.float32)
    acc += amp * cv2.resize(grid, (w, h), interpolation=cv2.INTER_CUBIC)
    amp *= 0.5
  flat = acc.ravel()
  ranks = np.empty(flat.size, np.float32)
  ranks[np.argsort(flat)] = np.arange(flat.size, dtype=np.float32)
  return (ranks / (flat.size - 1)).reshape(shape)


def smoothstep(e0, e1, x):
  t = np.clip((x - e0) / np.maximum(e1 - e0, 1e-6), 0.0, 1.0)
  return t * t * (3.0 - 2.0 * t)


def band_alpha(t, noise, width, jitter):
  """Per-pixel crossover: each pixel flips at its own time, drawn from `noise`."""
  center = 0.5 + jitter * (noise - 0.5)
  # Rescale so alpha still reaches a clean 0 and 1 at t=0 and t=1 despite jitter.
  lo = center - width * 0.5
  hi = center + width * 0.5
  span = 0.5 + jitter * 0.5 + width * 0.5
  return smoothstep(lo, hi, (t * 2.0 - 1.0) * span + 0.5)


def blend(a_bands, a_res, b_bands, b_res, noise_by_shape, t):
  out_bands = []
  for i, (ba, bb) in enumerate(zip(a_bands, b_bands)):
    width, jitter = BANDS[min(i, len(BANDS) - 1)]
    alpha = band_alpha(t, noise_by_shape[ba.shape[:2]], width, jitter)[..., None]
    out_bands.append(ba * (1.0 - alpha) + bb * alpha)
  ra = smoothstep(0.5 - RESIDUAL_WIDTH / 2, 0.5 + RESIDUAL_WIDTH / 2, t)
  return collapse(out_bands, a_res * (1.0 - ra) + b_res * ra)


def main():
  a = cv2.imread(os.path.join(IMAGES, 'house-photo-a.jpg'))
  b = cv2.imread(os.path.join(IMAGES, 'house-photo-b.jpg'))
  if a is None or b is None:
    sys.exit('error: run tools/align_photos.py first')

  a_bands, a_res = laplacian_pyramid(srgb_to_linear(a), LEVELS)
  b_bands, b_res = laplacian_pyramid(srgb_to_linear(b), LEVELS)

  noise_by_shape = {}
  full = fractal_noise(a.shape[:2])
  for band in a_bands:
    shape = band.shape[:2]
    noise_by_shape[shape] = (full if shape == a.shape[:2]
                             else cv2.resize(full, (shape[1], shape[0])))

  os.makedirs(OUT, exist_ok=True)
  for t in (0.25, 0.5, 0.75):
    img = linear_to_srgb(blend(a_bands, a_res, b_bands, b_res, noise_by_shape, t))
    path = os.path.join(OUT, 'dissolve_t%02d.jpg' % int(t * 100))
    cv2.imwrite(path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    # Local RMS contrast is the number that collapses in a naive cross-fade.
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    detail = g - cv2.GaussianBlur(g, (0, 0), 4)
    print('t=%.2f  local contrast (RMS of detail) %.2f  -> %s'
          % (t, detail.std(), os.path.basename(path)))

  for name, img in (('a', a), ('b', b)):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    print('source %s local contrast %.2f'
          % (name, (g - cv2.GaussianBlur(g, (0, 0), 4)).std()))
  naive = cv2.addWeighted(a, 0.5, b, 0.5, 0)
  g = cv2.cvtColor(naive, cv2.COLOR_BGR2GRAY).astype(np.float32)
  print('naive sRGB cross-fade t=0.50 local contrast %.2f'
        % (g - cv2.GaussianBlur(g, (0, 0), 4)).std())


if __name__ == '__main__':
  main()
