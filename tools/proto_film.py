#!/usr/bin/env python3
"""Prototype FILM (Reda et al., ECCV 2022) interpolation on the aligned pair.

FILM targets exactly this case: near-duplicate photos whose motion is far too
large for optical flow. Unlike the dissolve, this synthesises genuine in-between
poses -- people move rather than fade.

TorchScript export from jkawamoto/frame-interpolation-pytorch (re-exported to
avoid the MPS border-padding bug in the upstream weights).
"""
import argparse
import os
import sys
import time

import cv2
import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGES = os.path.join(HERE, os.pardir, 'ruddock', 'static', 'images')
MODEL = '/tmp/blendproto/models/film_net_fp32.pt'
OUT = '/tmp/blendproto'

ALIGN = 64  # FILM's pyramid needs dimensions divisible by this


def to_tensor(img, device):
  rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
  return torch.from_numpy(rgb).permute(2, 0, 1)[None].to(device)


def to_image(tensor):
  arr = tensor[0].permute(1, 2, 0).detach().cpu().float().numpy()
  arr = np.clip(arr, 0, 1) * 255.0
  return cv2.cvtColor(arr.astype(np.uint8), cv2.COLOR_RGB2BGR)


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument('--width', type=int, default=0,
                  help='downscale to this width first (0 = full resolution)')
  ap.add_argument('--device', default='auto', choices=['auto', 'mps', 'cpu'])
  ap.add_argument('--steps', type=int, default=0,
                  help='if set, render this many evenly spaced frames instead of the 3 probes')
  args = ap.parse_args()

  if not os.path.exists(MODEL):
    sys.exit('error: missing %s' % MODEL)

  if args.device == 'auto':
    device = 'mps' if torch.backends.mps.is_available() else 'cpu'
  else:
    device = args.device
  print('device: %s' % device)

  a = cv2.imread(os.path.join(IMAGES, 'house-photo-a.jpg'))
  b = cv2.imread(os.path.join(IMAGES, 'house-photo-b.jpg'))
  if a is None or b is None:
    sys.exit('error: run tools/align_photos.py first')

  if args.width:
    h = int(round(a.shape[0] * args.width / a.shape[1]))
    a = cv2.resize(a, (args.width, h), interpolation=cv2.INTER_AREA)
    b = cv2.resize(b, (args.width, h), interpolation=cv2.INTER_AREA)
  orig_h, orig_w = a.shape[:2]
  print('working at %dx%d' % (orig_w, orig_h))

  # Reflect-pad up to the pyramid's stride, then crop the result back.
  ph = (ALIGN - orig_h % ALIGN) % ALIGN
  pw = (ALIGN - orig_w % ALIGN) % ALIGN
  if ph or pw:
    a = cv2.copyMakeBorder(a, 0, ph, 0, pw, cv2.BORDER_REFLECT)
    b = cv2.copyMakeBorder(b, 0, ph, 0, pw, cv2.BORDER_REFLECT)
    print('padded to %dx%d' % (a.shape[1], a.shape[0]))

  model = torch.jit.load(MODEL, map_location='cpu').eval().to(device)
  ta, tb = to_tensor(a, device), to_tensor(b, device)

  if args.steps:
    ts = [i / (args.steps - 1.0) for i in range(args.steps)]
  else:
    # Endpoints included: at t=0 and t=1 FILM should reproduce the sources
    # almost exactly, which is the cheapest sanity check that it is behaving.
    ts = [0.0, 0.25, 0.5, 0.75, 1.0]

  os.makedirs(OUT, exist_ok=True)
  with torch.no_grad():
    for i, t in enumerate(ts):
      start = time.time()
      dt = ta.new_full((1, 1), t)
      try:
        out = model(ta, tb, dt)
      except Exception as exc:                       # noqa: BLE001
        sys.exit('error: FILM forward failed on %s: %s' % (device, exc))
      img = to_image(out)[:orig_h, :orig_w]
      name = ('film_seq_%03d.jpg' % i) if args.steps else ('film_t%02d.jpg' % int(t * 100))
      cv2.imwrite(os.path.join(OUT, name), img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
      g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
      print('t=%.3f  %5.1fs  local contrast %.2f  -> %s'
            % (t, time.time() - start,
               (g - cv2.GaussianBlur(g, (0, 0), 4)).std(), name))


if __name__ == '__main__':
  main()
