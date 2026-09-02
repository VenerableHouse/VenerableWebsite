#!/usr/bin/env python3
"""Register house-photo-silly.jpg onto house-photo.jpg so the two can be blended.

The two photos are from the same shoot with the camera in the same place; the only
geometric difference is framing (a pure zoom + shift). Once that is undone the
architecture is pixel-identical between the two and only the people differ, which is
what makes a smooth transition possible at all.

Run once; the outputs are committed.
"""
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGES = os.path.join(HERE, os.pardir, 'ruddock', 'static', 'images')

BASE = os.path.join(IMAGES, 'house-photo.jpg')
SILLY = os.path.join(IMAGES, 'house-photo-silly.jpg')
OUT_A = os.path.join(IMAGES, 'house-photo-a.jpg')
OUT_B = os.path.join(IMAGES, 'house-photo-b.jpg')

# Guardrails. These are far looser than the values the real pair produces (861
# inliers at 0.39px), so tripping one means something actually changed.
MIN_INLIERS = 500
MAX_REPROJ_ERR = 1.0

# The homepage renders this image at 960 CSS px (#content is 1000px wide with
# 20px of padding), so 1920 is exactly 2x for retina and anything more is bytes
# nobody can see. At q85 that is ~450 KB each, comfortably under the 872 KB the
# single unoptimised photo cost before.
WEB_WIDTH = 1920
JPEG_QUALITY = 85


def find_homography(base_gray, silly_gray):
  """Estimate the homography mapping silly -> base."""
  sift = cv2.SIFT_create(nfeatures=8000)
  kp_base, desc_base = sift.detectAndCompute(base_gray, None)
  kp_silly, desc_silly = sift.detectAndCompute(silly_gray, None)

  matcher = cv2.BFMatcher()
  # Lowe's ratio test. The people moved, so a large minority of matches are
  # genuinely wrong; RANSAC below rejects those as outliers.
  good = [m for m, n in matcher.knnMatch(desc_silly, desc_base, k=2)
          if m.distance < 0.75 * n.distance]

  src = np.float32([kp_silly[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
  dst = np.float32([kp_base[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
  H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 3.0, maxIters=20000)
  if H is None:
    sys.exit('error: could not estimate a homography between the two photos')

  inliers = mask.ravel().astype(bool)
  err = np.linalg.norm(
      (cv2.perspectiveTransform(src, H) - dst).reshape(-1, 2), axis=1)[inliers]

  print('matches: %d ratio-test, %d RANSAC inliers (%.0f%%)'
        % (len(good), inliers.sum(), 100.0 * inliers.sum() / len(good)))
  print('reprojection error: mean %.2f px, p95 %.2f px'
        % (err.mean(), np.percentile(err, 95)))

  if inliers.sum() < MIN_INLIERS:
    sys.exit('error: only %d inliers, expected >= %d -- did the source photos change?'
             % (inliers.sum(), MIN_INLIERS))
  if err.mean() > MAX_REPROJ_ERR:
    sys.exit('error: mean reprojection error %.2f px exceeds %.2f px'
             % (err.mean(), MAX_REPROJ_ERR))
  return H


def largest_inscribed_rect(valid):
  """Biggest axis-aligned rect of fully-valid pixels, as (x0, y0, x1, y1).

  The warp leaves slivers of undefined pixels along the top and bottom edges (the
  framing difference is not perfectly axis-aligned). Cropping both images to this
  rect keeps them the same size and stops those pixels flickering during the
  blend. The trim is ~1.5% of the height.

  Greedy shrink: repeatedly pull in whichever border has the most invalid pixels.
  The invalid region is a pair of thin near-horizontal wedges, so this converges
  in a handful of iterations and lands on the obvious rectangle.
  """
  y0, x0 = 0, 0
  y1, x1 = valid.shape
  while y1 - y0 > 1 and x1 - x0 > 1:
    sub = valid[y0:y1, x0:x1]
    edges = (
        ((~sub[0, :]).sum(), 'top'),
        ((~sub[-1, :]).sum(), 'bottom'),
        ((~sub[:, 0]).sum(), 'left'),
        ((~sub[:, -1]).sum(), 'right'),
    )
    worst, which = max(edges)
    if worst == 0:
      # Every border is clean. Interior holes are impossible here (the warped
      # source is a solid quad), so we are done.
      break
    if which == 'top':
      y0 += 1
    elif which == 'bottom':
      y1 -= 1
    elif which == 'left':
      x0 += 1
    else:
      x1 -= 1
  else:
    sys.exit('error: no valid rectangle after warping')
  return x0, y0, x1, y1


def photometric_match(src, ref, background):
  """Fit a per-channel gain/offset taking src towards ref, on background pixels only.

  The two frames differ slightly in exposure. Without this the blend has a faint
  brightness pop. Only background (unchanged) pixels are fit, since that is the
  region that *should* be identical -- fitting over the people would drag the
  correction towards the difference we deliberately want to keep.
  """
  out = np.empty_like(src, dtype=np.float32)
  for c in range(3):
    s = src[..., c][background].astype(np.float32)
    r = ref[..., c][background].astype(np.float32)
    gain, offset = np.polyfit(s, r, 1)
    print('  channel %d: gain %.4f, offset %+.2f' % (c, gain, offset))
    out[..., c] = src[..., c].astype(np.float32) * gain + offset
  return np.clip(out, 0, 255).astype(np.uint8)


def main():
  base = cv2.imread(BASE)
  silly = cv2.imread(SILLY)
  if base is None or silly is None:
    sys.exit('error: could not read source photos from %s' % IMAGES)
  print('base  %dx%d' % (base.shape[1], base.shape[0]))
  print('silly %dx%d' % (silly.shape[1], silly.shape[0]))

  base_gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
  silly_gray = cv2.cvtColor(silly, cv2.COLOR_BGR2GRAY)
  H = find_homography(base_gray, silly_gray)
  print('H (silly -> base):\n%s' % np.round(H / H[2, 2], 5))

  size = (base.shape[1], base.shape[0])
  warped = cv2.warpPerspective(silly, H, size, flags=cv2.INTER_LANCZOS4)
  valid = cv2.warpPerspective(
      np.ones(silly.shape[:2], np.uint8), H, size, flags=cv2.INTER_NEAREST) > 0

  x0, y0, x1, y1 = largest_inscribed_rect(valid)
  print('common valid rect: x %d..%d, y %d..%d  (%dx%d, trimmed %d rows / %d cols)'
        % (x0, x1, y0, y1, x1 - x0, y1 - y0,
           base.shape[0] - (y1 - y0), base.shape[1] - (x1 - x0)))

  out_a = base[y0:y1, x0:x1]
  out_b = warped[y0:y1, x0:x1]

  # Background = where the two already agree. Blur first so the mask follows
  # regions rather than individual noisy pixels.
  diff = cv2.GaussianBlur(
      cv2.absdiff(cv2.cvtColor(out_a, cv2.COLOR_BGR2GRAY),
                  cv2.cvtColor(out_b, cv2.COLOR_BGR2GRAY)), (0, 0), 5)
  background = diff < 12
  print('photometric match on %.1f%% of pixels (unchanged background):'
        % (100.0 * background.mean()))
  out_b = photometric_match(out_b, out_a, background)

  if out_a.shape[1] > WEB_WIDTH:
    height = int(round(out_a.shape[0] * WEB_WIDTH / out_a.shape[1]))
    out_a = cv2.resize(out_a, (WEB_WIDTH, height), interpolation=cv2.INTER_AREA)
    out_b = cv2.resize(out_b, (WEB_WIDTH, height), interpolation=cv2.INTER_AREA)
    print('resized for web: %dx%d' % (WEB_WIDTH, height))

  params = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
  cv2.imwrite(OUT_A, out_a, params)
  cv2.imwrite(OUT_B, out_b, params)

  residual = cv2.absdiff(out_a, out_b)
  print('\npost-align abs-diff: median %.1f, p90 %.1f (0-255)'
        % (np.median(residual), np.percentile(residual, 90)))
  print('pixels differing >30 levels: %.1f%%'
        % (100.0 * (residual.max(axis=2) > 30).mean()))
  for path in (OUT_A, OUT_B):
    print('wrote %s (%.0f KB)' % (path, os.path.getsize(path) / 1024.0))


if __name__ == '__main__':
  main()
