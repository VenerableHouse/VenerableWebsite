#!/usr/bin/env python3
"""Render a ladder of FILM frames between the two photos, by recursive bisection.

Stage 1 of 2. Stage 2 (tools/pace_ladder.py) only resamples these files, so the
transition curve can be retuned without touching the GPU again.

WHY BISECTION, NOT A SWEEP OF t:

The exported model takes a time parameter, but it does NOT interpolate to its own
endpoints -- measured on this pair, model(A, B, dt=0) sits 13.6 grey levels away
from A, about half the entire A->B distance, and dt=1 is 11.9 from B. The cause
is not reconstruction loss: model(A, A, 0.5) returns A to within 0.77. It is that
the fusion stage always mixes in content from BOTH inputs, so at dt=0 you get "A,
plus whatever it borrowed from B where the flow was unreliable".

A naive uniform sweep of dt therefore produces a sequence that never actually
reaches either photograph -- the transition visibly fails to converge at both
ends. Recursive midpoint bisection is how FILM is meant to be driven: the two
real photographs are KEPT as the endpoints and only interior frames are ever
synthesised, so convergence is exact by construction. It also asks the network
for smaller and smaller motions as the recursion deepens, which is the regime it
handles best.

Produces 2**depth + 1 frames using 2**depth - 1 model calls.
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

# fp16 is not just faster -- at fp32 the MPS backend falls off a memory cliff
# above ~1024px wide (0.8 s/frame at 1024 but 24 s/frame at 1440, a 30x jump for
# 2x the pixels). fp16 halves the working set and scales linearly instead.
MODEL_FP16 = '/tmp/blendproto/models/film_net_fp16.pt'
MODEL_FP32 = '/tmp/blendproto/models/film_net_fp32.pt'
LADDER = '/tmp/blendproto/ladder'

ALIGN = 64  # FILM's feature pyramid needs dimensions divisible by this


def to_tensor(img, device, dtype):
  """BGR uint8 -> padded NCHW tensor. Returns the tensor and the unpadded size."""
  h, w = img.shape[:2]
  padded = cv2.copyMakeBorder(img, 0, (ALIGN - h % ALIGN) % ALIGN,
                              0, (ALIGN - w % ALIGN) % ALIGN, cv2.BORDER_REFLECT)
  rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
  t = torch.from_numpy(rgb).permute(2, 0, 1)[None]
  return t.to(device=device, dtype=dtype), (h, w)


def to_image(tensor, size):
  arr = np.clip(tensor[0].permute(1, 2, 0).float().cpu().numpy(), 0, 1) * 255.0
  return cv2.cvtColor(arr.astype(np.uint8), cv2.COLOR_RGB2BGR)[:size[0], :size[1]]


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument('--width', type=int, default=1440)
  ap.add_argument('--depth', type=int, default=7,
                  help='bisection depth; yields 2**depth + 1 frames (7 -> 129)')
  ap.add_argument('--device', default='auto', choices=['auto', 'mps', 'cpu'])
  ap.add_argument('--precision', default='fp16', choices=['fp16', 'fp32'])
  ap.add_argument('--out', default=LADDER)
  args = ap.parse_args()

  model_path = MODEL_FP16 if args.precision == 'fp16' else MODEL_FP32
  dtype = torch.float16 if args.precision == 'fp16' else torch.float32
  if not os.path.exists(model_path):
    sys.exit('error: missing %s' % model_path)
  device = ('mps' if torch.backends.mps.is_available() else 'cpu'
            ) if args.device == 'auto' else args.device

  a = cv2.imread(os.path.join(IMAGES, 'house-photo-a.jpg'))
  b = cv2.imread(os.path.join(IMAGES, 'house-photo-b.jpg'))
  if a is None or b is None:
    sys.exit('error: run tools/align_photos.py first')

  width = args.width
  height = int(round(a.shape[0] * width / a.shape[1]))
  a = cv2.resize(a, (width, height), interpolation=cv2.INTER_AREA)
  b = cv2.resize(b, (width, height), interpolation=cv2.INTER_AREA)

  total = 2 ** args.depth          # number of intervals
  frames = total + 1
  os.makedirs(args.out, exist_ok=True)
  path = lambda i: os.path.join(args.out, 'f%04d.png' % i)

  # The real photographs, verbatim. Everything else is synthesised between them.
  cv2.imwrite(path(0), a)
  cv2.imwrite(path(total), b)

  model = torch.jit.load(model_path, map_location='cpu').eval().to(device)
  print('device %s (%s), %d frames at %dx%d by depth-%d bisection (%d model calls)'
        % (device, args.precision, frames, width, height, args.depth, total - 1))

  started = time.time()
  done = 0
  half = torch.zeros(1, 1, device=device, dtype=dtype) + 0.5
  with torch.no_grad():
    for level in range(1, args.depth + 1):
      stride = total >> level      # distance from a midpoint to each parent
      for mid in range(stride, total, 2 * stride):
        if os.path.exists(path(mid)):
          continue
        lo = cv2.imread(path(mid - stride))
        hi = cv2.imread(path(mid + stride))
        tl, size = to_tensor(lo, device, dtype)
        th, _ = to_tensor(hi, device, dtype)
        # Lossless PNG between levels: the recursion feeds its own output back in,
        # so any lossy step here would compound over the remaining levels.
        cv2.imwrite(path(mid), to_image(model(tl, th, half), size))
        done += 1
      rate = (time.time() - started) / max(done, 1)
      print('  level %d/%d complete (%d/%d frames, %.2fs each, eta %.1f min)'
            % (level, args.depth, done, total - 1, rate,
               rate * (total - 1 - done) / 60.0), flush=True)

  print('ladder complete: %d frames in %.1f min'
        % (frames, (time.time() - started) / 60.0))


if __name__ == '__main__':
  main()
