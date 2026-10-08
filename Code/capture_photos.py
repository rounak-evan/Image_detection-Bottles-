"""
Capture training/test photos with the Arducam
---------------------------------------------
Opens the Arducam, shows a live preview, and saves a full-resolution photo
each time you press SPACE. Built for collecting real "field" photos from the
production camera, to test (and later retrain) the bottle model on.

Runs on the laptop — only needs opencv-python, not the model or a GPU.
Counting happens later on the home PC.

Usage (from the Code/ folder):
    python capture_photos.py            # camera index 1 (the Arducam on the laptop)
    python capture_photos.py 0          # a different camera index, if 1 isn't it

Keys (click the preview window first so it receives the key presses):
    SPACE  save a photo
    Q      quit
"""

import sys
import time
from datetime import datetime
from pathlib import Path

import cv2

# Laptop camera index 1 = Arducam (index 0 is the laptop's black IR camera).
# See ChallengesLog #7. Other machines may number cameras differently.
CAMERA_INDEX = int(sys.argv[1]) if len(sys.argv) > 1 else 1

# Highest resolution the Arducam streams over USB 2.0 (ChallengesLog #8).
# Without setting this, OpenCV silently uses 640x480.
WIDTH, HEIGHT = 2592, 1944

WARMUP_FRAMES = 30     # thrown away while auto-exposure settles (ChallengesLog #6)
PREVIEW_WIDTH = 1000   # preview is shrunk to fit the screen; saved photos are full size

# Saved next to the other raw photo batches, with the same folder naming style.
OUTPUT_DIR = Path(__file__).resolve().parent / 'data' / 'Bottle Images (arducam)'


if __name__ == '__main__':
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        sys.exit(f"Could not open camera index {CAMERA_INDEX}. Try another index, e.g. "
                 f"'python capture_photos.py 0'.")

    # MJPG = the camera compresses each frame before sending it over USB.
    # Uncompressed frames at 2592x1944 are too big for USB 2.0, which makes
    # the preview very slow or makes the camera fall back to a lower resolution.
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

    print("Warming up camera...")
    time.sleep(1)
    for _ in range(WARMUP_FRAMES):
        cap.read()

    ok, frame = cap.read()
    if not ok:
        sys.exit("Camera opened but returned no image.")

    # Check what we actually got, not what we asked for — the camera can
    # silently give a lower resolution than requested.
    h, w = frame.shape[:2]
    print(f"Capturing at {w}x{h}")
    if (w, h) != (WIDTH, HEIGHT):
        print(f"WARNING: expected {WIDTH}x{HEIGHT}. Is this the Arducam? "
              f"Photos will still save, but at lower detail.")

    print(f"Saving photos to: {OUTPUT_DIR}")
    print("SPACE = save photo, Q = quit")

    saved = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            print("Lost the camera feed — is the USB cable still connected?")
            break

        scale = PREVIEW_WIDTH / frame.shape[1]
        preview = cv2.resize(frame, None, fx=scale, fy=scale)
        cv2.putText(preview, f"Saved: {saved}   SPACE = save, Q = quit", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow('Arducam capture', preview)

        key = cv2.waitKey(1) & 0xFF   # waits 1 ms for a key press; 0xFF strips extra bits Windows adds
        if key == ord(' '):
            # Timestamped name (down to the millisecond), so photos never overwrite each other.
            stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]   # %f is microseconds; drop 3 digits
            filename = OUTPUT_DIR / f"ARDU_{stamp}.jpg"
            # Quality 95 (out of 100) keeps fine cap detail; OpenCV's default is also 95,
            # but stated explicitly so it's easy to find and change.
            cv2.imwrite(str(filename), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            saved += 1
            print(f"Saved {filename.name}")
        elif key in (ord('q'), ord('Q')):
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"Done — {saved} photo(s) saved to {OUTPUT_DIR}")
