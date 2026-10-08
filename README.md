# Image_detection-Bottles-
Created for the detection, count and labelling of bottles (Top-down view) using Yolov8 (nano model) on OPi 3B. The whole system contains the SBC, LCD Touchscreen and a Arducam Camera.

## Overview

A device that counts the bottles in a crate from a top-down photo. An
Arducam takes the photo, a custom-trained YOLOv8n model counts the caps on
the Orange Pi 3B's NPU, and the count is shown on a 10.1" touchscreen.

**Status (2026-10-08):** model trained and verified (counts all validation
photos exactly); running on the Orange Pi's NPU in ~0.65 s per photo;
capture-and-count program working on the Pi. Next: real crate photos from
the Arducam, then the touchscreen app once the LCD arrives.

## Where to start

| Read this | For |
|---|---|
| [`Code/ClaudeContext/Projectsummary.md`](Code/ClaudeContext/Projectsummary.md) | Full project state — start at "Where things stand" |
| [`Code/ClaudeContext/ChallengesLog.md`](Code/ClaudeContext/ChallengesLog.md) | Every problem hit so far, with causes and fixes |
| [`Code/ORANGE_PI_SETUP.md`](Code/ORANGE_PI_SETUP.md) | Setting up the Orange Pi (OS, NPU, camera, eMMC) |
| [`Code/GPU_TRAINING_SETUP.md`](Code/GPU_TRAINING_SETUP.md) | Training on the home PC (AMD RX 9070 XT, ROCm) |
| [`Code/LABELING_INSTRUCTIONS.md`](Code/LABELING_INSTRUCTIONS.md) | Labeling photos in makesense.ai |
| [`Code/LAPTOP_QUICKSTART.md`](Code/LAPTOP_QUICKSTART.md) | Taking Arducam photos on the laptop |

## Layout

- `Code/` — all scripts, models and docs
  - `pi/bottle_counter.py` — runs on the Orange Pi: photo → NPU model → count
  - `models/runs/bottle_detector/weights/best.pt` — the trained model
  - `models/rknn/best_fp16.rknn` — the same model converted for the Pi's NPU
  - `data/dataset/labels/` — bottle labels (YOLO format)
- `LCD Display/`, `Printer/` — hardware datasheets
- `Workflow diagrams/` — system diagrams

## Not in this repository

Kept off GitHub on purpose: **all photos** (raw batches, dataset images,
test outputs — kept private), the home PC's Python environment
(`Code/venv/`), and the 8 GB Orange Pi OS image (download link and
checksum are in `Code/ORANGE_PI_SETUP.md`). To retrain, the photos need to
be copied back into `Code/data/dataset/images/` from the original source.
