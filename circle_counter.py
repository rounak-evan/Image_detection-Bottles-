"""
Circle Counter (classical CV, no AI training required)
--------------------------------------------------------
Counts bottles in a TOP-DOWN photo of a packed crate by detecting the
circular bottle caps directly, using OpenCV's Hough Circle Transform.

Why this instead of the YOLO-based imagedetcode.py:
YOLOv8n was pretrained on COCO, where "bottle" almost always means a
side-view photo (a bottle's neck/shoulder/body silhouette). A top-down photo
of packed caps looks nothing like that to the model, so it detects nothing.
Bottle caps, though, are simple, high-contrast circles against a differently
colored crate — a classical shape-detection technique handles this well
without needing any training data.

How Hough Circle Transform works (brief):
It's a voting algorithm. For every edge pixel in the image, it imagines all
the circles of allowed radii that could pass through that pixel, and casts a
"vote" for each one's center. Centers that accumulate enough votes from many
edge pixels agreeing on the same circle are reported as detected circles.

Usage:
    python circle_counter.py your_photo.jpg
"""

import sys
import os
import cv2
import numpy as np

# Resize every photo to this width before detecting circles. This keeps
# processing fast and keeps the Hough parameters below meaningful regardless
# of the original photo's resolution (a phone photo might be 4000px+ wide).
PROCESS_WIDTH = 900

# --- Hough Circle parameters (tuned by testing against real sample photos) ---
# minDist: minimum allowed distance between two detected circle centers, so
#   one cap isn't counted twice. Set close to the expected cap spacing.
# param1: the upper threshold for the internal Canny edge detector.
# param2: how many "votes" a circle needs to count as detected — lower finds
#   more circles (risk of false positives), higher finds fewer (risk of
#   missing faint/reflective caps).
# minRadius / maxRadius: expected cap radius range, in pixels, AFTER
#   resizing to PROCESS_WIDTH.
HOUGH_PARAMS = dict(
    dp=1,
    minDist=45,
    param1=60,
    param2=30,
    minRadius=25,
    maxRadius=55,
)


def count_bottles_topdown(image_path, save_path='tests/outputs/result_circles.jpg'):
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(
            f"Could not open image at '{image_path}' — check the path is "
            "correct and the file exists."
        )

    # Resize down to a consistent working size (keeps aspect ratio).
    height, width = image.shape[:2]
    scale = PROCESS_WIDTH / width
    resized = cv2.resize(image, (PROCESS_WIDTH, int(height * scale)))

    # Hough Circle Transform works on a single-channel (grayscale) image.
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    # Blur first to smooth out label text/reflections on the caps, which
    # would otherwise create false edges and confuse circle detection.
    blurred = cv2.medianBlur(gray, 5)

    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        **HOUGH_PARAMS,
    )

    count = 0
    if circles is not None:
        # circles is a float array; round and convert to int pixel coords.
        circles = np.round(circles[0, :]).astype(int)
        count = len(circles)
        for (x, y, r) in circles:
            cv2.circle(resized, (x, y), r, (0, 255, 0), 2)
            cv2.circle(resized, (x, y), 2, (0, 0, 255), 3)

    cv2.putText(resized, f'Count: {count}', (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
    cv2.imwrite(save_path, resized)

    return count


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python circle_counter.py your_photo.jpg')
        sys.exit(1)

    photo_path = sys.argv[1]
    bottle_count = count_bottles_topdown(photo_path)
    print(f'Bottles found: {bottle_count}')
    print('Annotated image saved to tests/outputs/result_circles.jpg')
