"""
Train (custom fine-tuning of YOLOv8n on our bottle photos)
--------------------------------------------------------------
Fine-tunes the pretrained yolov8n.pt on OUR labeled photos, so it learns
what a bottle cap looks like from a top-down, sometimes-tilted view — a
case the original COCO-pretrained model was never taught, since COCO only
shows bottles from the side.

Don't run this until you've reviewed/corrected the draft labels — see
LABELING_INSTRUCTIONS.md. Training on uncorrected labels just teaches the
model to repeat the circle detector's mistakes.

Usage:
    python train.py
"""

from pathlib import Path

import torch
from ultralytics import YOLO

# Workaround for the AMD RX 9070 XT on Windows (ROCm 7.2.1): AMD's MIOpen
# library crashes during training with "miopenStatusUnknownError". On ROCm,
# this "cudnn" switch actually controls MIOpen — turning it off makes
# PyTorch use its own built-in GPU code instead. Still runs on the GPU.
torch.backends.cudnn.enabled = False

# Start from the same pretrained weights imagedetcode.py uses. Fine-tuning
# (continuing training from an already-trained model) needs far fewer
# examples than training from scratch, because the model already knows
# general shapes/edges/textures — we're just teaching it this one new view
# of "bottle".
# The guard below is required on Windows: the data loader starts helper
# processes ("workers") that re-run this file from the top. Without the
# guard, each worker would try to start its own training run and crash.
if __name__ == '__main__':
    model = YOLO('models/yolov8n.pt')

    model.train(
        data='data/dataset/data.yaml',
        epochs=100,        # training passes over the whole dataset; with a
                            # small dataset like ours, more passes help, and
                            # Ultralytics stops early if it stops improving.
        imgsz=1280,         # higher than the usual default (640) because our
                            # photos are large and bottle caps are small
                            # relative to the full crate — a low resolution
                            # would blur caps together, especially in the
                            # 150+ bottle crates.
        batch=4,            # how many images processed at once; kept low
                            # since imgsz=1280 uses more memory per image.
        patience=20,        # stop early if val performance hasn't improved
                            # for 20 epochs in a row, to avoid overfitting on
                            # such a small dataset.
        # Full path built from this file's own folder: newer Ultralytics
        # versions nest a relative 'models/runs' inside their own
        # runs/detect/ folder, which put results in the wrong place.
        project=str(Path(__file__).parent / 'models' / 'runs'),
        name='bottle_detector',
        exist_ok=True,      # reuse the folder instead of making
                            # bottle_detector-2, -3, ... on each rerun.
    )

    print("\nTraining complete. Best weights saved under "
          "models/runs/bottle_detector/weights/best.pt")
