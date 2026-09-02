#!/usr/bin/env python3
"""Resample the uniform FILM ladder onto a non-uniform playback curve, then encode.

Two corrections are composed, in this order:

  1. ARC-LENGTH REPARAMETERISATION. FILM's t is not guaranteed to be uniform in
     *perceived* change -- if it isn't, constant-rate playback of a uniform
     ladder visibly speeds up and slows down on its own. Measuring cumulative
     frame-to-frame difference and resampling against it removes that inherent
     jerk, giving a constant perceived rate as the neutral baseline.

  2. A DELIBERATE SIGMOID on top. The synthesised middle of the morph is where
     faces are least plausible, so we sprint through it and linger on the two
     ends, which are real photographs. A normalised logistic has its maximum
     slope exactly at the midpoint, which is the shape we want.

The sigmoid is applied in arc-length space, so it governs *perceived* progress
rather than FILM's raw parameter.
"""
import argparse
import itertools
import os
import shutil
import subprocess
import sys

import cv2
import numpy as np

LADDER = '/tmp/blendproto/ladder'
OUT = '/tmp/blendproto'
IMAGES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      os.pardir, 'ruddock', 'static', 'images')

# The ladder's endpoints must BE the source photographs. An earlier version swept
# FILM's dt parameter uniformly, which silently produced a sequence that never
# reached either photo (13.6 grey levels off at dt=0) -- the transition visibly
# failed to converge at both ends. Bisection makes convergence exact by
# construction; this guard makes sure it stays that way.
MAX_ENDPOINT_ERR = 0.5


def load_ladder(path):
  names = sorted(f for f in os.listdir(path) if f.endswith('.png'))
  if len(names) < 3:
    sys.exit('error: ladder at %s has only %d frames -- run '
             'tools/make_film_ladder.py first' % (path, len(names)))
  return [os.path.join(path, n) for n in names]


def check_endpoints(paths):
  for name, path, index in (('house-photo-a.jpg', paths[0], 0),
                            ('house-photo-b.jpg', paths[-1], len(paths) - 1)):
    frame = cv2.imread(path)
    source = cv2.imread(os.path.join(IMAGES, name))
    ref = cv2.resize(source, (frame.shape[1], frame.shape[0]),
                     interpolation=cv2.INTER_AREA)
    err = float(np.abs(frame.astype(np.float32) - ref.astype(np.float32)).mean())
    print('endpoint f%04d vs %s: mean abs-diff %.3f' % (index, name, err))
    if err > MAX_ENDPOINT_ERR:
      sys.exit('error: ladder does not converge to %s (%.2f > %.2f). The '
               'transition would not start or end on the real photograph.'
               % (name, err, MAX_ENDPOINT_ERR))


def arc_length(paths):
  """Cumulative perceived change along the ladder, normalised to [0, 1]."""
  prev = None
  steps = [0.0]
  for p in paths:
    img = cv2.imread(p).astype(np.float32)
    if prev is not None:
      steps.append(float(np.abs(img - prev).mean()))
    prev = img
  cum = np.cumsum(steps)
  return cum / cum[-1], np.array(steps[1:])


def logistic_curve(tau, k):
  """Normalised logistic on [0, 1]. k=0 degenerates to linear."""
  if k <= 1e-6:
    return tau
  raw = 1.0 / (1.0 + np.exp(-k * (tau - 0.5)))
  lo = 1.0 / (1.0 + np.exp(k * 0.5))
  hi = 1.0 / (1.0 + np.exp(-k * 0.5))
  return (raw - lo) / (hi - lo)


# H.264 needs even dimensions under yuv420p, and the ladder is 1440x845 -- an odd
# height. Cropping the last row is invisible and lossless for the rest; scaling
# would resample every pixel.
EVEN = 'crop=trunc(iw/2)*2:trunc(ih/2)*2'

CODECS = {
    # VP9 is what we would actually ship: ~30% smaller than H.264 at matched
    # quality, and these frames are near-identical so inter-frame prediction is
    # very effective.
    'webm': ['-c:v', 'libvpx-vp9', '-b:v', '0', '-deadline', 'good',
             '-cpu-used', '1', '-pix_fmt', 'yuv420p'],
    # H.264 for viewing and sharing -- plays anywhere, including QuickTime and
    # chat clients that will not touch a webm.
    'mp4': ['-c:v', 'libx264', '-preset', 'slow', '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart'],
}
# Matched-ish perceptual quality; the two scales are not the same number.
CRF_OFFSET = {'webm': 0, 'mp4': -15}


def encode(frames, path, fps, crf, container, reverse=False):
  """Encode a frame list to one container.

  Goes through a numbered symlink directory rather than ffmpeg's concat demuxer:
  concat needs per-file duration directives to honour a framerate with still
  images, whereas -framerate on a numbered sequence is unambiguous. Symlinks keep
  it free -- the ladder PNGs are never copied.
  """
  seq = list(reversed(frames)) if reverse else frames
  staging = path + '.seq'
  shutil.rmtree(staging, ignore_errors=True)
  os.makedirs(staging)
  for i, src in enumerate(seq):
    os.symlink(os.path.abspath(src), os.path.join(staging, 'f%05d.png' % i))
  cmd = (['ffmpeg', '-y', '-loglevel', 'error',
          '-framerate', str(fps), '-i', os.path.join(staging, 'f%05d.png'),
          '-vf', EVEN, '-an',
          '-crf', str(max(0, crf + CRF_OFFSET[container]))]
         + CODECS[container] + [path])
  subprocess.run(cmd, check=True)
  shutil.rmtree(staging, ignore_errors=True)
  return os.path.getsize(path)


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument('--ladder', default=LADDER)
  ap.add_argument('--out-frames', type=int, default=90)
  ap.add_argument('--fps', type=int, default=30)
  ap.add_argument('-k', '--steepness', type=float, default=8.0,
                  help='logistic steepness; 0 = linear, 8 = default, 12 = severe')
  ap.add_argument('--no-arclength', action='store_true')
  ap.add_argument('--label', default='',
                  help='descriptive word folded into the output filename')
  ap.add_argument('--format', default='both', choices=['webm', 'mp4', 'both'])
  ap.add_argument('--crf', type=int, default=38,
                  help='VP9 quality; 38 halves the size vs 30 and the difference '
                       'is invisible because these frames are only ever seen in motion')
  args = ap.parse_args()

  paths = load_ladder(args.ladder)
  n = len(paths)
  print('ladder: %d frames' % n)
  check_endpoints(paths)

  s, steps = arc_length(paths)
  uniform = np.linspace(0, 1, n)
  print('arc-length vs uniform t: max deviation %.3f  (0 = FILM t is already '
        'perceptually uniform)' % np.abs(s - uniform).max())
  print('per-step perceived change: mean %.2f, min %.2f, max %.2f  (ratio %.2fx)'
        % (steps.mean(), steps.min(), steps.max(), steps.max() / max(steps.min(), 1e-6)))

  tau = np.linspace(0, 1, args.out_frames)
  u = logistic_curve(tau, args.steepness)
  if args.no_arclength:
    idx = u * (n - 1)
  else:
    # Invert the arc-length map: what ladder position sits at arc position u?
    idx = np.interp(u, s, np.arange(n, dtype=np.float64))
  picks = np.clip(np.round(idx).astype(int), 0, n - 1)

  # Diagnostics: how long do we dwell in the synthetic middle?
  mid = (u > 0.3) & (u < 0.7)
  print('\ncurve k=%.1f: %d/%d output frames (%.0f%% of runtime) spend arc 0.3-0.7'
        % (args.steepness, mid.sum(), args.out_frames,
           100.0 * mid.sum() / args.out_frames))
  print('  linear would be 40%%; speed at midpoint is %.2fx linear'
        % ((args.steepness / 4.0) / np.tanh(args.steepness / 4.0)
           if args.steepness > 1e-6 else 1.0))
  runs = [len(list(group)) for _, group in itertools.groupby(picks.tolist())]
  print('  distinct ladder frames used: %d/%d; longest hold on one frame: %d '
        'output frames (%.2fs)'
        % (len(set(picks.tolist())), n, max(runs), max(runs) / float(args.fps)))

  label = ('_' + args.label) if args.label else ''
  stem = 'blend_k%02d%s' % (int(round(args.steepness)), label)
  frames = [paths[i] for i in picks]
  containers = ['webm', 'mp4'] if args.format == 'both' else [args.format]

  print()
  for container in containers:
    for direction, rev in (('', False), ('_reverse', True)):
      path = os.path.join(OUT, '%s%s.%s' % (stem, direction, container))
      size = encode(frames, path, args.fps, args.crf, container, rev)
      print('wrote %-52s %6.0f KB' % (os.path.basename(path), size / 1024.0))
  print('  (%d frames, %.2fs @ %dfps)' % (args.out_frames,
                                          args.out_frames / float(args.fps), args.fps))

  # Contact sheet so the pacing can be eyeballed without scrubbing a video.
  cols, rows = 6, 3
  picks_sheet = np.linspace(0, args.out_frames - 1, cols * rows).astype(int)
  thumbs = []
  for i in picks_sheet:
    im = cv2.imread(frames[i])
    thumbs.append(cv2.resize(im, (im.shape[1] // 5, im.shape[0] // 5)))
  sheet = np.vstack([np.hstack(thumbs[r * cols:(r + 1) * cols]) for r in range(rows)])
  sheet_path = os.path.join(OUT, 'contact_sheet_%s.jpg' % stem)
  cv2.imwrite(sheet_path, sheet, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
  print('wrote %s' % sheet_path)


if __name__ == '__main__':
  main()
