"""
Bottle counter — the "engine" of the device (runs on the Orange Pi)
--------------------------------------------------------------------
Takes a photo with the Arducam, counts the bottles in it using the trained
model on the Pi's NPU (AI chip), and returns the count. Also saves the photo
with a box drawn around every bottle it counted, so the count can be checked
by eye.

Two ways to use it:

1. From the command line (for testing):
       ~/rknn-venv/bin/python bottle_counter.py                 # take a photo and count it
       ~/rknn-venv/bin/python bottle_counter.py --image a.jpg   # count an existing photo instead

2. From other Python code (the touchscreen app will do this later):
       counter = BottleCounter()          # slow part, once: loads the model, opens the camera
       result = counter.count_from_camera()
       print(result.count)                # e.g. 126
       counter.close()

Must be run with the venv that has rknn-toolkit-lite2 installed (~/rknn-venv).
"""

import argparse
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from rknnlite.api import RKNNLite

HERE = Path(__file__).resolve().parent

# --- Model settings (must match how the model was trained and tested) -------
MODEL_PATH = HERE / 'best_fp16.rknn'   # FP16 version: exact on all val photos.
                                       # (The INT8 version counts 0 — see ChallengesLog #23.)
IMG_SIZE = 1280                        # the model was trained on 1280x1280 images
CONFIDENCE_THRESHOLD = 0.5             # drop boxes the model is less than 50% sure about
OVERLAP_THRESHOLD = 0.4                # two boxes overlapping >40% = the same bottle; keep one
                                       # (both values tuned on the PC — ChallengesLog #18)

# --- Camera settings (worked out on 2026-10-06, see ORANGE_PI_SETUP.md 6a) ----
CAMERA_DEVICE = 0                      # /dev/video0 = the Arducam on the Pi
CAPTURE_WIDTH, CAPTURE_HEIGHT = 3264, 2448   # full 8 MP — Linux allows this, Windows didn't
FOCUS = 150                            # manual focus; sharpest at the test height. Re-check
                                       # once the camera is in its final mount.
WARMUP_SECONDS = 3                     # frames read and thrown away while exposure settles

# --- Crop to the crate ------------------------------------------------------
# Only this part of the photo is counted, so bottles lying *next to* the crate
# are ignored (ChallengesLog #19). Given as fractions of the photo's width and
# height: (left, top, right, bottom). (0, 0, 1, 1) = the whole photo.
# Set this properly once the camera mount and crate position are fixed.
CROP = (0.0, 0.0, 1.0, 1.0)

SAVE_DIR = HERE / 'captures'           # where photos and marked-up photos are saved


@dataclass
class CountResult:
    count: int                 # number of bottles counted
    boxes: np.ndarray          # one row per bottle: x1, y1, x2, y2 (pixels in the full photo)
    photo: np.ndarray          # the photo that was counted (BGR, full size)
    annotated: np.ndarray      # same photo with the boxes and the count drawn on it
    seconds: float             # time taken to count (not including taking the photo)


class BottleCounter:
    def __init__(self, model_path=MODEL_PATH, crop=CROP, use_camera=True):
        self.crop = crop
        # Load the model onto the NPU. Done once, because it takes a few seconds.
        self.npu = RKNNLite(verbose=False)
        if self.npu.load_rknn(str(model_path)) != 0:
            raise RuntimeError(f'Could not load the model: {model_path}')
        if self.npu.init_runtime() != 0:
            raise RuntimeError('Could not start the NPU runtime')

        self.camera = None
        if use_camera:
            self._open_camera()

    # ---- camera ------------------------------------------------------------
    def _open_camera(self):
        self.camera = cv2.VideoCapture(CAMERA_DEVICE, cv2.CAP_V4L2)
        if not self.camera.isOpened():
            raise RuntimeError(f'Could not open camera /dev/video{CAMERA_DEVICE}')
        # MJPG = the camera compresses frames before sending them over USB.
        # Without it, 8 MP frames are too big for USB 2.0.
        self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)
        # Lock the focus. The camera's own autofocus picked a blurrier setting
        # in testing, and a fixed mount never needs refocusing anyway.
        subprocess.run(['v4l2-ctl', '-d', f'/dev/video{CAMERA_DEVICE}',
                        '-c', 'focus_auto=0', '-c', f'focus_absolute={FOCUS}'],
                       check=False, capture_output=True)
        # The first frames after opening are often too dark/bright while the
        # camera adjusts its exposure (ChallengesLog #6) — read and discard them.
        start = time.time()
        while time.time() - start < WARMUP_SECONDS:
            self.camera.read()

    def take_photo(self):
        # The camera keeps a few frames queued up; grab() throws the old ones
        # away so the photo is from *now*, not from a moment ago.
        for _ in range(3):
            self.camera.grab()
        ok, frame = self.camera.read()
        if not ok:
            raise RuntimeError('Camera returned no image — is it still plugged in?')
        h, w = frame.shape[:2]
        if (w, h) != (CAPTURE_WIDTH, CAPTURE_HEIGHT):
            # Silently getting a smaller photo would quietly hurt accuracy (ChallengesLog #8).
            print(f'WARNING: camera gave {w}x{h}, expected {CAPTURE_WIDTH}x{CAPTURE_HEIGHT}')
        return frame

    # ---- counting ----------------------------------------------------------
    def count_from_camera(self):
        return self.count_photo(self.take_photo())

    def count_photo(self, photo):
        start = time.time()

        # 1. Crop to the crate area.
        h, w = photo.shape[:2]
        left, top = int(self.crop[0] * w), int(self.crop[1] * h)
        right, bottom = int(self.crop[2] * w), int(self.crop[3] * h)
        region = photo[top:bottom, left:right]

        # 2. "Letterbox" to 1280x1280, exactly like during training: shrink so
        #    the long side is 1280, then pad the short side with grey (114).
        rh, rw = region.shape[:2]
        scale = IMG_SIZE / max(rh, rw)
        new_w, new_h = round(rw * scale), round(rh * scale)
        pad_x, pad_y = (IMG_SIZE - new_w) // 2, (IMG_SIZE - new_h) // 2
        model_input = np.full((IMG_SIZE, IMG_SIZE, 3), 114, np.uint8)
        model_input[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = cv2.resize(region, (new_w, new_h))
        model_input = cv2.cvtColor(model_input, cv2.COLOR_BGR2RGB)   # model was trained on RGB

        # 3. Run the model on the NPU. Output: 5 rows x 33600 candidate boxes —
        #    centre x, centre y, width, height (in 1280x1280 pixels), and a score.
        output = self.npu.inference(inputs=[model_input[None]], data_format=['nhwc'])[0]
        candidates = output.reshape(5, -1).T

        # 4. Keep confident boxes only, then merge duplicates of the same bottle (NMS).
        candidates = candidates[candidates[:, 4] > CONFIDENCE_THRESHOLD]
        boxes = np.zeros((0, 4))
        if len(candidates):
            cx, cy, bw, bh, scores = candidates.T
            xywh = np.stack([cx - bw / 2, cy - bh / 2, bw, bh], axis=1)
            keep = cv2.dnn.NMSBoxes(xywh.tolist(), scores.tolist(),
                                    CONFIDENCE_THRESHOLD, OVERLAP_THRESHOLD)
            keep = np.array(keep).flatten()
            # 5. Convert boxes from 1280x1280 model coordinates back to the full photo.
            x1 = (xywh[keep, 0] - pad_x) / scale + left
            y1 = (xywh[keep, 1] - pad_y) / scale + top
            x2 = x1 + xywh[keep, 2] / scale
            y2 = y1 + xywh[keep, 3] / scale
            boxes = np.stack([x1, y1, x2, y2], axis=1)

        seconds = time.time() - start
        return CountResult(len(boxes), boxes, photo, self._draw(photo, boxes), seconds)

    def _draw(self, photo, boxes):
        out = photo.copy()
        thickness = max(2, photo.shape[1] // 800)
        h, w = photo.shape[:2]
        # Show the crop area in yellow, if it's not the whole photo.
        if tuple(self.crop) != (0.0, 0.0, 1.0, 1.0):
            cv2.rectangle(out, (int(self.crop[0] * w), int(self.crop[1] * h)),
                          (int(self.crop[2] * w), int(self.crop[3] * h)), (0, 255, 255), thickness)
        for x1, y1, x2, y2 in boxes.astype(int):
            cv2.rectangle(out, (x1, y1), (x2, y2), (0, 200, 0), thickness)
        label = f'Bottles: {len(boxes)}'
        cv2.putText(out, label, (20, 30 + 40 * thickness), cv2.FONT_HERSHEY_SIMPLEX,
                    thickness, (0, 0, 0), thickness * 4)       # black outline...
        cv2.putText(out, label, (20, 30 + 40 * thickness), cv2.FONT_HERSHEY_SIMPLEX,
                    thickness, (255, 255, 255), thickness)     # ...white text, readable on any background
        return out

    def close(self):
        if self.camera is not None:
            self.camera.release()
        self.npu.release()


def save(result, name):
    SAVE_DIR.mkdir(exist_ok=True)
    photo_path = SAVE_DIR / f'{name}.jpg'
    marked_path = SAVE_DIR / f'{name}_counted.jpg'
    cv2.imwrite(str(photo_path), result.photo, [cv2.IMWRITE_JPEG_QUALITY, 95])
    cv2.imwrite(str(marked_path), result.annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return photo_path, marked_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Count bottles in a crate.')
    parser.add_argument('--image', nargs='*', help='count these photo files instead of using the camera')
    parser.add_argument('--no-save', action='store_true', help="don't save photos")
    args = parser.parse_args()

    counter = BottleCounter(use_camera=not args.image)
    try:
        if args.image:
            for path in args.image:
                result = counter.count_photo(cv2.imread(path))
                print(f'{Path(path).name}: Bottles: {result.count}  ({result.seconds:.2f}s)')
                if not args.no_save:
                    save(result, Path(path).stem)
        else:
            result = counter.count_from_camera()
            print(f'Bottles: {result.count}  ({result.seconds:.2f}s)')
            if not args.no_save:
                photo_path, marked_path = save(result, datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
                print(f'Saved {photo_path.name} and {marked_path.name} in {SAVE_DIR}')
    finally:
        counter.close()
