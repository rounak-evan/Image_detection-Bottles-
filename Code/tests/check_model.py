"""
Check the trained model's COUNTS against our hand-corrected labels
------------------------------------------------------------------
Training reported scores like precision/recall, but what the device actually
needs is "this crate has N bottles". This script runs the trained model
(best.pt) on labeled photos and compares its count per photo against the
true count from our corrected label files (one line per bottle).

It also saves each photo with the model's boxes drawn on it, so mistakes can
be checked by eye — into tests/outputs/model_check/.

Usage (from the Code/ folder):
    python tests/check_model.py          # the 11 val photos (never trained on)
    python tests/check_model.py train    # the 44 training photos
"""

import sys
from pathlib import Path

import torch
from ultralytics import YOLO

# Same AMD MIOpen workaround as train.py — see GPU_TRAINING_SETUP.md.
torch.backends.cudnn.enabled = False

# Code/ folder, worked out from this file's location (tests/ is one level down),
# so the script works no matter which folder it's run from.
CODE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = CODE_DIR / 'models' / 'runs' / 'bottle_detector' / 'weights' / 'best.pt'
DATASET_DIR = CODE_DIR / 'data' / 'dataset'
OUTPUT_DIR = CODE_DIR / 'tests' / 'outputs' / 'model_check'

IMG_SIZE = 1280            # must match the imgsz the model was trained at
# Tuned 2026-10-03 (see ChallengesLog #18). With Ultralytics' defaults
# (conf=0.25, iou=0.7) the model double-counted many caps: a second, slightly
# larger, low-confidence box around a cap that already had a box.
CONFIDENCE_THRESHOLD = 0.5   # drop boxes the model is less than 50% sure about
OVERLAP_THRESHOLD = 0.4      # if two boxes overlap more than 40%, keep only the
                             # more confident one (Ultralytics' default is 70%)
MAX_DETECTIONS = 1000      # default is 300 — too low, our densest crates have 337 bottles


def true_count(label_path):
    """Count the bottles in a label file: one non-empty line = one bottle box."""
    with open(label_path) as f:
        return sum(1 for line in f if line.strip())


if __name__ == '__main__':
    split = sys.argv[1] if len(sys.argv) > 1 else 'val'
    image_paths = sorted((DATASET_DIR / 'images' / split).glob('*.jpeg'))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    model = YOLO(str(MODEL_PATH))

    print(f"\nChecking {len(image_paths)} '{split}' photos\n")
    print(f"{'Photo':<14}{'True':>6}{'Model':>7}{'Diff':>7}{'Error %':>9}")
    print('-' * 43)

    total_true = 0
    total_abs_diff = 0
    for image_path in image_paths:
        expected = true_count(DATASET_DIR / 'labels' / split / f'{image_path.stem}.txt')

        result = model.predict(str(image_path), imgsz=IMG_SIZE, conf=CONFIDENCE_THRESHOLD,
                               iou=OVERLAP_THRESHOLD, max_det=MAX_DETECTIONS, verbose=False)[0]
        predicted = len(result.boxes)

        # labels=False and conf=False hide the "bottle 0.93" text above each
        # box — with hundreds of boxes, the text would cover the caps.
        result.save(filename=str(OUTPUT_DIR / f'{image_path.stem}.jpg'), labels=False, conf=False)

        diff = predicted - expected   # negative = missed bottles, positive = extra boxes
        print(f"{image_path.stem:<14}{expected:>6}{predicted:>7}{diff:>+7}"
              f"{abs(diff) / expected * 100:>8.1f}%")
        total_true += expected
        total_abs_diff += abs(diff)

    print('-' * 43)
    print(f"Total bottles: {total_true}, total miscounted: {total_abs_diff} "
          f"({total_abs_diff / total_true * 100:.2f}%)")
    print(f"Annotated images saved to {OUTPUT_DIR}")
