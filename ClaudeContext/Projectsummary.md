# Orange Pi 3B Bottle Counter — Project Memory

## About the user

New to coding and actively learning. When explaining or making changes to code,
default to clear, line-by-line explanations of what each piece does and why —
not just the change itself. Don't assume familiarity with Python idioms,
OpenCV, or ML terminology; briefly explain new concepts as they come up.

## Project overview

A device built on the Orange Pi 3B that uses a camera and a pretrained ML
model to detect and count bottles in view, displaying the live count on a
touchscreen. Includes audio feedback ("captured") when a photo is taken.
Location: Chennai, India (relevant for hardware sourcing).

## Hardware — finalized

- **Board**: Orange Pi 3B, 4GB RAM variant (RK3566 SoC, 0.8 TOPS NPU, Mali-G52
  GPU). 4GB chosen for OS + camera capture + RKNN inference + PySide6 UI
  running concurrently with headroom.
- **Camera**: Arducam B0292 — 8MP Sony IMX219 sensor, autofocus, USB 2.0,
  UVC-compliant (plug-and-play). Chosen over CSI because Orange Pi 3B's CSI
  driver compatibility couldn't be confirmed. Sourced via Robu.in, ~₹3,869.
  Known limits: rolling shutter (fine for stationary capture), modest
  low-light performance.
  **Received and tested on the Windows laptop (2026-09-23)** — see "Camera
  hardware test" section below for full results: confirmed working via
  OpenCV, default capture resolution (640×480) is far below its real
  capability, actual working ceiling ~2592×1944 through OpenCV's UVC video
  path.
- **Touchscreen** — three separate connections:
  1. HDMI (video in) from Orange Pi to the driver board.
  2. Power — separate DC input to the driver board, confirmed 5V. Driver
     board is the HC10MST (M-star chip, up to 1900×1200, likely native
     1280×800, 40-pin LVDS out). Datasheet says "MICRO USB-5V" but the actual
     cable has 2 bare pins — confirm physical connector once board is in
     hand; either way it's 5V.
  3. Touch (USB) — DG101565A08 (~10.1" capacitive, ILI2511 controller,
     4-pin FPC VCC/D-/D+/GND, standard USB pinout, 3.3V logic, 10mA).
     Uses the generic `hid-multitouch` Linux driver — no custom driver work.
- **Power architecture** — two independent supplies:
  - 5V/3A USB-C → Orange Pi 3B (also powers camera and touch controller,
    both USB bus-powered).
  - Separate 5V DC adapter → display driver board (HDMI/LVDS circuitry +
    backlight). Exact connector (micro-USB vs 2-pin) still to be confirmed
    physically.
- **Speaker**: USB or 3.5mm powered speaker, connected to the Orange Pi's own
  headphone jack or a USB port — not the display's driver board (audio
  support there is unconfirmed).
- **Microphone**: mentioned early on, never tied to a confirmed feature —
  still open whether it's actually needed (e.g. voice-triggered capture).
  Not yet sourced.
- **Storage**: Orange Pi eMMC module, or Class 10/A2 microSD as a cheaper
  starting point.
- **Cooling**: passive heatsink recommended for sustained camera + NPU load.

## Software approach

- **Detection strategy**: Pretrained YOLOv8n (via `ultralytics`), trained on
  COCO — "bottle" is already class ID 39, so zero custom training needed.
  Detection (not classification) chosen because counting requires separating
  individual object instances.
- **Dev environment**: Windows + VS Code, Python extension installed.
  Packages: `opencv-python`, `ultralytics`.
- **RKNN conversion (for later)**: Needed to run the model on the Orange Pi's
  NPU. RKNN-Toolkit2 only officially supports Ubuntu 18.04/20.04/22.04, not
  the user's native Ubuntu 26.x. Plan: Docker (Rockchip's official image) or
  WSL2 with Ubuntu 22.04. Deferred until core detection logic is proven.
- **UI framework**: PySide6 (better touch support than Kivy, clean OpenCV
  frame integration via QImage/QPixmap). Audio "captured" cue planned via
  `QSoundEffect` (QtMultimedia), playing a pre-recorded `.wav`, not live TTS.

## Project workflow (6 phases)

1. Hardware bring-up — assemble parts, flash OS (needs hardware)
2. Peripheral checks — camera, display, touch, audio (needs hardware)
3. Model prep — convert to RKNN format (RKNN step needs hardware; rest doesn't)
4. Core application — capture, inference, counting loop (no hardware needed)
5. UI integration — PySide6 touchscreen app (no hardware needed)
6. Test & deploy — tune performance, package as autostart kiosk app (needs hardware)

## Software-only progress (no hardware needed)

1. Python environment set up — done
2. Pretrained model loading — done (`models/yolov8n.pt`)
3. Detection on sample photos — done, using bundled `bus.jpg` as a stand-in
   test image (real bottle photos not yet provided at time of writing)
4. Filter detections and count — done, logic verified (correctly excluded a
   low-confidence, edge-of-frame detection from the count)
5. Tune against real photos — **not yet done**, waiting on real bottle photos
6. Package into one reusable function — done, see `imagedetcode.py`
   (now superseded by `circle_counter.py` — see "MAJOR PIVOT" below)
7. Build the UI shell (PySide6, placeholder data) — not yet done
8. Wire the UI to the real detection function — not yet done

## MAJOR PIVOT (2026-09-22): real photos changed the approach

Real bottle photos were provided (originally `Code/Bottle Images (Upright)/`,
now moved to `Code/data/Bottle Images (Upright)/` in the later folder
reorg — 16 photos). Testing against them revealed two things that change
the plan above:

1. **The real camera view is top-down onto a packed crate** (many bottles
   at once, seen from above), not the side-view single-bottle shots COCO's
   "bottle" class was trained on. The pretrained YOLOv8n model
   (`imagedetcode.py`) detected **zero bottles on all 16 real photos**,
   even at a confidence threshold as low as 0.01 — confirmed via raw
   unfiltered detection output. This is a domain mismatch, not a threshold
   issue: a top-down grid of caps doesn't visually resemble what COCO
   calls a "bottle".
2. Tried a classical CV fallback instead: `circle_counter.py` uses OpenCV's
   Hough Circle Transform to detect bottle caps directly as circles — no
   training data needed. Result, spot-checked on 3 of 16 photos:
   - **Works well** when the camera is close to directly overhead and
     bottles are upright (IMG_4723: 39 detected, visually accurate).
   - **Fails on perspective-distorted photos** — caps further from the
     camera look smaller and fall outside the detector's expected size
     range (IMG_4730: undercounts, whole top third of crate missed).
   - **Fails structurally on tilted/leaning bottles** — their caps appear
     as ellipses, not circles, from a top-down angle, so the circle
     detector misses them almost entirely and instead reports false
     positives on background texture (IMG_4743: only 11 found, all wrong —
     0 real bottles detected, matches only crate texture/holes).

**Decision (user confirmed): pursue both fixes together**, not one or the
other:
- **Hardware**: mount the production camera directly overhead, as high
  above the crate as the enclosure allows, lens axis perpendicular to the
  crate — minimizes the perspective distortion seen in IMG_4730. This
  doesn't fix tilted-bottle packing on its own.
- **Software**: fine-tune a custom YOLOv8 model on the real photos so it
  learns bottles from this top-down/tilted view, instead of relying on
  COCO's side-view training. This is genuine training — the "no training
  needed" assumption from the original plan no longer holds for the
  top-down crate scenario.

### Custom training pipeline (built; dataset now finished, training not yet run)

- `prepare_dataset.py` — auto-generates a *draft* YOLO-format labeled
  dataset (now at `data/dataset/` post-reorg, see "Folder structure" below)
  by converting `circle_counter.py`'s detected circles into bounding boxes.
  Splits 16 photos into 13 train / 3 val (seeded, reproducible). Saves
  `data/dataset/data.yaml` (1 class: "bottle"). Draft labels were
  originally incomplete (inherited circle_counter.py's blind spots —
  missed tilted bottles, missed far/small caps, occasional false positive
  on background) — **since corrected and finalized, see "Labeling tool
  switch" section below** (the tool ended up being makesense.ai, not
  LabelImg as originally planned).
- `train.py` — fine-tunes `models/yolov8n.pt` on the corrected dataset
  (`imgsz=1280` because caps are small relative to full crate photos,
  `epochs=100` with early-stop `patience=20`). **Not yet run** — see
  "Training hardware plan" below (moving to a GPU machine before running
  this).
- `tests/batch_test.py` — calls `circle_counter.py`'s
  `count_bottles_topdown()` instead of the old YOLO-based `count_bottles()`
  from `imagedetcode.py`, since the latter is confirmed non-functional for
  this photo angle.

### Labeling tool switch: LabelImg → makesense.ai

Tried LabelImg (desktop, `pip install labelImg`) first, per the original
plan. It kept crashing unpredictably — no reproducible trigger, likely
general instability from an unmaintained tool (last updated ~2022) running
on Python 3.14 (released years later, never tested against it). Rather
than debug a flaky old desktop app, switched to **makesense.ai** (free,
runs entirely in-browser, no install/account, so the Python version is
irrelevant to it). It supports the same import/correct/export workflow via
YOLO format — needed the per-image `.txt` files and a `labels.txt` class
list ("bottle") selected together in one file-picker action (a browser
file picker can't multi-select across separate folders, which caused one
early "labels.txt required" import error until all the files were copied
into one flat folder first).

**Labeling is now complete (2026-09-23)** — all 16 photos corrected and
exported, copied into `data/dataset/labels/train/` and
`data/dataset/labels/val/` (paths shown post-reorg; at the time this was
still just `dataset/labels/train/` etc — see "Folder structure" below),
replacing the auto-generated drafts. Final box counts per photo:
IMG_4723: 38, IMG_4724: 38, IMG_4729: 202, IMG_4730: 202, IMG_4731: 125,
IMG_4732 (val): 125, IMG_4733: 125, IMG_4734 (val): 159, IMG_4735: 159,
IMG_4736 (val): 159, IMG_4740: 149, IMG_4742: 149, IMG_4743: 119,
IMG_4744: 119, IMG_4745: 119, IMG_4747: 58. (Several photos share identical
counts — confirmed via diff to be real coincidences, not a duplication bug;
likely the same physical crate photographed more than once, which would
have the same true count regardless of angle.)

**Dataset is now ready for `train.py` to be run** — this is the next
blocking step, paused at the user's request to test newly-arrived camera
hardware first (see below).

## Camera hardware test (2026-09-23)

The Arducam B0292 arrived and was tested on the Windows laptop via
`camera_test.py` (a short script from a separate Claude session, verified
and run from here). Findings:

- **Camera index 1** (via `cv2.VideoCapture(1)`) **is the Arducam**,
  confirmed by capturing a frame and visually matching it to what was
  physically held in front of the lens (a printed document). Camera index
  0 returned a consistently black feed (brightness ~0.5/255) even after
  warm-up frames — almost certainly a laptop-integrated IR camera (e.g.
  Windows Hello), not a usable device for this project.
- **Gotcha discovered**: the very first frame read immediately after
  `cap.read()` is often invalid (solid black or blown-out white) because
  the sensor's auto-exposure/auto-white-balance hasn't stabilized yet.
  Fix: discard ~15-30 frames (with a short `time.sleep(1)` first) before
  keeping a frame for real use. Relevant for any future capture code,
  including the eventual Orange Pi capture loop.
- **Resolution**: opens at a default of 640×480 unless explicitly set.
  Tested requesting several resolutions via `cap.set(cv2.CAP_PROP_FRAME_WIDTH/HEIGHT)`
  — actual negotiated results:
  - Requested 3280×2464 (full 8MP sensor) → got 2592×1944 (~5MP) — the
    practical video-streaming ceiling over USB 2.0 through OpenCV; the
    sensor's full 8MP is likely still-photo-only, not sustainable as a
    live video stream at this bandwidth.
  - 1920×1080, 1280×720, 640×480 all negotiated cleanly as requested.
  - Confirmed 2592×1944 actually delivers real frame data (not just an
    accepted-but-empty request) — captured and visually verified a sharp,
    detailed frame at that resolution.
  - **Action item for later capture code** (UI integration / Orange Pi
    capture loop): must explicitly call
    `cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2592)` /
    `cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1944)` right after opening the
    camera — otherwise it silently captures at 640×480, which would hurt
    bottle-cap detection accuracy (small caps need real resolution to be
    distinguishable, especially on the dense 100+ bottle crates).
- Camera was handheld during testing (not mounted), so blur/rotation seen
  in test captures don't reflect final device behavior — orientation will
  be whatever the fixed production mount sets it to.

## Folder structure (reorganized 2026-09-23)

The `Code/` folder was tidied — core scripts stayed at the top level,
everything test-related and data/model files moved into dedicated
subfolders:

```
Code/
├── imagedetcode.py       (YOLO-based detector — non-functional for top-down crate photos, kept for reference)
├── circle_counter.py     (working classical CV detector, Hough Circle Transform)
├── prepare_dataset.py    (builds a dataset from scratch — DO NOT re-run now, would wipe corrected labels)
├── add_new_photos.py     (adds a new photo batch to the existing dataset WITHOUT touching corrected labels)
├── train.py              (fine-tunes YOLOv8n on the labeled dataset)
├── LABELING_INSTRUCTIONS.md
├── GPU_TRAINING_SETUP.md (home-PC ROCm/PyTorch setup for the AMD 9070 XT)
├── ClaudeContext/
│   ├── Projectsummary.md (this file)
│   └── ChallengesLog.md  (study log of every bug/issue hit, with root causes and fixes)
├── data/
│   ├── Bottle Images (Upright)/   (batch 1: 16 raw source photos)
│   ├── Bottle Images (new)/       (batch 2: 39 raw source photos)
│   └── dataset/                    (YOLO-format training data: images/{train,val}/, labels/{train,val}/, data.yaml, labels.txt — 55 photos total, fully labeled)
├── models/
│   └── yolov8n.pt                  (pretrained base weights; trained weights will land in models/runs/ once train.py is run)
└── tests/
    ├── camera_test.py              (hardware check script)
    ├── batch_test.py               (runs circle_counter.py across a whole folder of photos)
    └── outputs/                    (all test-generated images: result_circles.jpg, which_camera_*.jpg, batch_results/)
```

**Path changes to remember**: scripts now reference `models/yolov8n.pt`
(not `yolov8n.pt`), `data/dataset/...` (not `dataset/...`), and
`data/Bottle Images (Upright)/` (not `Bottle Images (Upright)/`). Test
output images now default into `tests/outputs/` instead of scattering into
the `Code/` root. `tests/batch_test.py` adds `Code/` to `sys.path` at the
top so it can still import `circle_counter.py` despite living one folder
down — needed since it moved but `circle_counter.py` didn't. All scripts
verified working after the move (smoke-tested each one).

Removed as redundant/stale during cleanup: `dataset/import_all/` and
`dataset/import_val/` (pre-reorg paths — these were the batch-1 temporary
staging folders used only to work around makesense.ai's file-picker
limitation; content already merged into `data/dataset/labels/`), and the
LabelImg-era `classes.txt` files (unused since the switch to makesense.ai).
(A similar staging folder, `data/dataset/import_new/`, was used the same
way for batch 2 — see "Second photo batch" section below — and can be
deleted too now that batch 2 labeling is complete and merged.)

## Original script: imagedetcode.py (SUPERSEDED — kept for reference only)

**No longer the current detector.** This section describes the original
pretrained-YOLOv8n approach, written and tested before real bottle photos
existed (verified only against a stand-in test image). Once real photos
arrived, this script was confirmed non-functional for the actual top-down
crate view (see "MAJOR PIVOT" above) — it detects zero bottles on all 16
real photos. **The current working detector is `circle_counter.py`**, and
the eventual production detector will be the custom-trained model from
`train.py`. Kept here for historical context, not as a how-to.

Key implementation notes (as originally written):
- `model = YOLO('models/yolov8n.pt')` is loaded once at module level
  (outside any function) because loading is slow and the script may
  process many images.
- `TARGET_CLASS` and `CONFIDENCE_THRESHOLD` are top-level constants so
  they're easy to find and tune without hunting through the code.
- `count_bottles(image_path, save_path='tests/outputs/result.jpg')`
  returns an integer count and also saves an annotated copy of the image
  — this return value is what the future PySide6 UI will consume directly.
- The `if __name__ == '__main__':` block only runs when the script is
  executed directly (`python imagedetcode.py photo.jpg`), not when it's
  later imported elsewhere.

## How to run and test locally (current setup, no hardware)

**Current working detector is `circle_counter.py`, not `imagedetcode.py`**
(see note above). From the `Code/` folder:

1. Open the project folder in VS Code, open the integrated terminal.
2. Confirm `opencv-python` and `ultralytics` are installed (`pip list`).
3. Run: `python circle_counter.py "data/Bottle Images (Upright)/IMG_4723.jpeg"`
   (or any photo path).
4. Check the terminal for `Bottles found: N`, and open
   `tests/outputs/result_circles.jpg` to see annotated boxes and the count.
5. To run against a whole folder of photos at once instead of one at a
   time, use `python tests/batch_test.py "data/Bottle Images (Upright)"` —
   results land in `tests/outputs/batch_results/`.

This all runs on the Windows laptop, not the Orange Pi — hardware isn't in
the loop yet at this stage. (The actual training run (`train.py`) is
planned for the home PC instead — see "Training hardware plan" below.)

## Training hardware plan: moving to a home PC with a GPU (2026-09-23)

This laptop has no GPU (`torch.cuda.is_available()` → `False`) — running
`train.py` here would mean CPU-only training, likely several hours given
the dataset (16 photos, many with 100-200+ bottle instances each) at
`imgsz=1280`. **Decision: move training to the user's home PC**, which has
a Ryzen 9700X3D CPU, an AMD Radeon RX 9070 XT (16GB VRAM), and 32GB DDR5
RAM — a GPU-capable machine, once set up correctly. (The CPU/RAM are far
more than this small workload needs — GPU training is GPU-bound, not
CPU-bound, since the CPU's only role is data loading/preprocessing for a
44-image training set, which is effectively instant regardless of CPU.
Estimated training time on the 9070XT: roughly 10-30 minutes for the full
100-epoch run, vs. an estimated 6-18+ hours on this CPU-only laptop — not
yet benchmarked on either machine as of this writing, since training
hasn't been run yet.)

AMD GPUs need ROCm (not CUDA) for PyTorch acceleration, and Windows ROCm
support is newer/less mature than Linux. Researched current (2026) status:
the RX 9070 XT is officially supported via AMD's "PyTorch on Windows"
edition (ROCm 7.2.1 + PyTorch 2.9.1, Windows 11, Python 3.12 specifically).
**Full step-by-step setup instructions are in `GPU_TRAINING_SETUP.md`**
(same folder as this file) — Python 3.12 install, driver version
requirement, the exact ROCm/PyTorch pip install command, the
install-order gotcha (installing `ultralytics` can silently overwrite the
ROCm-enabled PyTorch with a CPU-only build if done in the wrong order),
and GPU-detection verification steps to run before trusting it.

**Plan**: user copies the whole `Code/` folder to the home PC (all scripts
use relative paths only, so this works unchanged in any location), opens a
separate Claude Code session there, points it at `GPU_TRAINING_SETUP.md`
for the environment setup and this file for full project context, then
runs `train.py` there instead of on this laptop. `train.py` itself hasn't
been run yet as of this writing.

## Second photo batch + operational decision (2026-09-25)

User provided 39 more real photos (`data/Bottle Images (new)/`) — all
clean, near-overhead shots (unlike the first batch, none tilted), ranging
from sparse (~24 bottles) to very dense (200+) crates. Landscape-oriented
(wider field of view than the first, portrait-oriented batch), which meant
bottle caps appear smaller in pixels — the first batch's tuned
`HOUGH_PARAMS` (`minRadius=25`) missed almost everything on this batch (6
photos got exactly 0 draft boxes). Diagnosed and fixed: added an optional
`hough_params` override to `prepare_dataset.py`'s `detect_circles_full_res()`,
and a new script **`add_new_photos.py`** uses a widened radius range
(`minRadius=12, maxRadius=40`) just for this batch's draft-labeling pass —
doesn't touch `circle_counter.py`'s actual tuned production parameters.
Regenerated drafts with this fix: every photo now has substantial coverage
(spot-checked IMG_4830 visually — went from 0 to 94 detected, good
coverage). All 39 photos added to `data/dataset/` (31 train, 8 val),
**alongside**, not replacing, the original 16 (`add_new_photos.py` was
specifically written to never touch already-corrected labels — only
`prepare_dataset.py` would overwrite the whole dataset, so that script must
NOT be re-run now that real corrections exist). **New dataset total: 55
photos (44 train / 11 val).**

**Labeling complete (2026-09-28)** — all 39 new photos corrected via
makesense.ai and merged into `data/dataset/labels/train/` and
`data/dataset/labels/val/`, verified: every file's box count changed from
its draft (real correction happened, not an unchanged re-export), and
suspicious matching counts among consecutive photo IDs (e.g. IMG_4837-4842
all landing on 31) were spot-checked via diff and confirmed to be genuine
coincidences — different coordinates, same total — consistent with those
being the same physical crate photographed multiple times in a row.
**Full dataset (55 photos, 44 train / 11 val) is now fully labeled and
ready for `train.py`.**

**Operational decision**: rather than chase down more tilted/fallen-over
bottle photos for training-data robustness, the user will instead have
staff physically keep bottles upright when handling them for this device
— a process constraint instead of a model-robustness requirement, to get
the project working sooner. Revisit tilted-bottle handling later if
needed; not a current priority.

## Immediate next steps

1. **Blocking step**: run `train.py` on the home PC (see "Training
   hardware plan" above) using the full 55-photo dataset — all labels are
   now corrected and complete (both batches).
2. Once trained, check the resulting model
   (`models/runs/bottle_detector/weights/best.pt`) against the 11 held-out
   val photos before trusting it.
3. Tilted-bottle robustness is deliberately deprioritized (see "Second
   photo batch" note above) — handled via process (staff keep bottles
   upright), not training data, for now.
4. Physically confirm/adjust the production camera mount to be as close to
   directly overhead as the enclosure allows (see "MAJOR PIVOT" note above).
5. When writing any future capture code (UI integration, Orange Pi loop),
   remember the two camera gotchas from the hardware test: discard warm-up
   frames before use, and explicitly set resolution to 2592×1944 (don't
   rely on the 640×480 default).
6. Build the PySide6 UI shell (step 7) — this can happen in parallel, it
   doesn't depend on the detection method being finalized.
7. Wire the (now custom-trained) detection function into the UI (step 8).
8. Decide the trigger condition for the "captured" audio cue (manual button
   vs. count stabilizing over consecutive frames).
9. Resolve the open microphone question (needed or not).
