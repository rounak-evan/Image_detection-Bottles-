# Orange Pi 3B Bottle Counter — Project Memory

## About the user

New to coding and actively learning. When explaining or making changes to code,
default to clear, line-by-line explanations of what each piece does and why —
not just the change itself. Don't assume familiarity with Python idioms,
OpenCV, or ML terminology; briefly explain new concepts as they come up.

## Project overview

A device built on the Orange Pi 3B that uses a camera and a custom-trained
ML model to detect and count bottles in a crate (seen from above),
displaying the count on a touchscreen. Includes audio feedback
("captured") when a photo is taken. Location: Chennai, India (relevant
for hardware sourcing).

## Where things stand (end of day 2026-10-06) — read this first

- **Model:** custom YOLOv8n trained on 55 labeled phone photos
  (`models/runs/bottle_detector/weights/best.pt`). Counts all 11 val photos
  exactly with `imgsz=1280, conf=0.5, iou=0.4, max_det=1000`. Not yet
  tested on real crate photos from the Arducam.
- **Orange Pi 3B:** running Ubuntu 22.04 (Orange Pi 1.0.8, kernel 5.10),
  **boots from the eMMC alone** (since 2026-10-07 — keep the old SD card
  out), IP 192.168.1.115, SSH key login from this PC, NPU driver RKNPU
  v0.9.6 present.
- **Capture-and-count program:** `pi/bottle_counter.py` on the Pi
  (`~/bottle/`) — photo → crop → NPU → count, exact on all val photos.
- **Camera on the Pi:** works at full 3264x2448; manual focus 150 is
  sharpest at test height.
- **Model on the Pi's NPU (2026-10-07):** `best_fp16.rknn` counts all 11
  val photos exactly, ~0.64 s per photo. INT8 version is broken (counts 0)
  — fixable later for speed, not needed now.
- **Next:** real crate photos from the Arducam, then the Pi
  capture-and-count script. Full list: "Immediate next steps" at the bottom.
- Details of today's boot problem and fix: `ChallengesLog.md` #20.

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
  path **on Windows**. **On the Orange Pi (Linux, 2026-10-06) it offers the
  full 3264×2448 at 15 fps (MJPG)** — see "Orange Pi 3B bring-up".
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
  **Re-checked against both datasheets (2026-10-08, screen ordered):**
  HDMI does **not** power the display — HDMI's +5V line is only meant for
  ~55 mA (EDID/identification), far too little for a 10.1" backlight. The
  HC10MST needs its own **5V supply on its micro-USB socket** (datasheet
  gives no current; plan **5V 2A**). The touch panel's 4-pin FPC is USB
  wiring (VCC, D-, D+, GND) but its controller is 3.3V (drawing says 2.8V)
  — connect it through the USB adapter it ships with, not straight to a
  5V USB port. Powering the display from a Pi USB port is possible but not
  recommended (the Pi's 5V/3A supply already feeds Pi + camera + touch).
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
  starting point. **Currently (2026-10-06):** SanDisk 64GB SD card + USB
  pen drive (temporary); eMMC module removed and kept — target long-term
  boot device.
- **Cooling**: passive heatsink recommended for sustained camera + NPU load.

## Software approach

- **Detection strategy**: ~~Pretrained YOLOv8n (via `ultralytics`), trained on
  COCO — "bottle" is already class ID 39, so zero custom training needed.~~
  **Superseded** — the COCO model can't see bottles from above (see "MAJOR
  PIVOT"). **Current detector: a custom fine-tuned YOLOv8n,
  `models/runs/bottle_detector/weights/best.pt`, trained 2026-10-03** (see
  "First training run" below). Detection (not classification) chosen because
  counting requires separating individual object instances.
- **Dev environment**: Windows + VS Code, Python extension installed.
  Packages: `opencv-python`, `ultralytics`.
- **RKNN conversion (next step)**: Needed to run the model on the Orange Pi's
  NPU. RKNN-Toolkit2 only officially supports Ubuntu 18.04/20.04/22.04, not
  the user's native Ubuntu 26.x. Plan: Docker (Rockchip's official image) or
  WSL2 with Ubuntu 22.04 on the home PC. Core detection logic is now proven
  (count check), and the Pi's NPU driver is confirmed (RKNPU v0.9.6).
- **UI framework**: PySide6 (better touch support than Kivy, clean OpenCV
  frame integration via QImage/QPixmap). Audio "captured" cue planned via
  `QSoundEffect` (QtMultimedia), playing a pre-recorded `.wav`, not live TTS.

## Project workflow (6 phases)

1. Hardware bring-up — assemble parts, flash OS (needs hardware)
   — **done** (booted 2026-10-06; running from the eMMC since 2026-10-07)
2. Peripheral checks — camera, display, touch, audio (needs hardware)
   — **camera done**; audio, display, touch pending
3. Model prep — convert to RKNN format (RKNN step needs hardware; rest doesn't)
   — **done 2026-10-07**: FP16 RKNN model exact on the NPU (~0.65 s/photo)
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
5. Tune against real photos — done differently than planned: real photos
   showed the pretrained model doesn't work, so a custom model was labeled
   and trained instead (see "MAJOR PIVOT" and "First training run" below)
6. Package into one reusable function — done, see `imagedetcode.py`
   (now superseded by `circle_counter.py`, and that in turn by the trained
   model — a counting function wrapping `best.pt` is **not yet written**)
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

### Custom training pipeline (built, dataset finished, first training run done 2026-10-03)

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
  `epochs=100` with early-stop `patience=20`). **Run successfully on the
  home PC's GPU on 2026-10-03** — see "First training run" below. Two
  changes were made to it along the way: MIOpen is disabled
  (`torch.backends.cudnn.enabled = False`) to avoid an AMD GPU crash, and
  the output folder is now an absolute path with `exist_ok=True` so
  results land in `models/runs/bottle_detector/` every time.
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
├── capture_photos.py     (laptop: live Arducam preview, SPACE saves a full-res 2592x1944 photo)
├── ORANGE_PI_SETUP.md    (Orange Pi 3B bring-up: OS image, flashing, first boot, NPU check, SSH, peripherals)
├── LAPTOP_QUICKSTART.md  (using the project on the laptop to take Arducam crate photos)
├── pi/
│   ├── bottle_counter.py   (runs ON THE PI: photo → crop → NPU model → count; the engine the touchscreen app will call)
│   └── install_to_emmc.sh  (runs ON THE PI with sudo: copies the running system onto the eMMC — ERASES the eMMC)
├── tools/
│   ├── fix_gpt_entry_pointer.ps1   (Windows, admin: repairs the GPT header bug that blocked first boot — ChallengesLog #20)
│   └── pen_drive_lba1_before_fix.bin (backup of the pen drive's original header sector, for undo)
├── train.py              (fine-tunes YOLOv8n on the labeled dataset)
├── train_log.txt         (full console output of the 2026-10-03 training run)
├── LABELING_INSTRUCTIONS.md
├── GPU_TRAINING_SETUP.md (home-PC ROCm/PyTorch setup for the AMD 9070 XT)
├── ClaudeContext/
│   ├── Projectsummary.md (this file)
│   └── ChallengesLog.md  (study log of every bug/issue hit, with root causes and fixes)
├── data/
│   ├── Bottle Images (Upright)/   (batch 1: 16 raw source photos)
│   ├── Bottle Images (new)/       (batch 2: 39 raw source photos)
│   ├── Bottle Images (arducam)/   (batch 3, planned: real field photos from the production camera, via capture_photos.py)
│   └── dataset/                    (YOLO-format training data: images/{train,val}/, labels/{train,val}/, data.yaml, labels.txt — 55 photos total, fully labeled)
├── models/
│   ├── yolov8n.pt                  (pretrained base weights — the starting point for training)
│   ├── rknn/                       (NPU model for the Pi: best_fp16.rknn + convert.py + npu_count.py — see "Model on the NPU")
│   └── runs/bottle_detector/       (output of train.py: weights/best.pt = the trained model, weights/last.pt,
│                                    results.csv per-epoch metrics, plots, val_batch*_pred.jpg previews)
├── weights/
│   └── yolo26n.pt                  (auto-downloaded by Ultralytics during training, most likely for its
│                                    AMP self-check — not used by any of our scripts)
└── tests/
    ├── camera_test.py              (hardware check script)
    ├── batch_test.py               (runs circle_counter.py across a whole folder of photos)
    ├── check_model.py              (trained model's count vs. true label count, per photo — see "Count check")
    └── outputs/                    (all test-generated images: result_circles.jpg, which_camera_*.jpg, batch_results/, model_check/,
                                     pi_camera/ = Arducam shots taken on the Orange Pi + counted_* model runs)
```

Outside `Code/`: `C:\ML_Project\Orange_pi_OS\` holds the flashed OS image
(`Orangepi3b_1.0.8_ubuntu_jammy_desktop_xfce_linux5.10.160.img` + `.sha`,
checksum verified). On the Pi itself, test captures live in
`/home/orangepi/camtest/`.

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
deleted too now that batch 2 labeling is complete and merged. **Still
present on disk as of 2026-10-03.**) The `data/dataset/labels/*.cache`
files are created automatically by Ultralytics when training scans the
labels — harmless, and regenerated if deleted.

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
the loop yet at this stage. (Training (`train.py`) runs on the home PC
instead — see "Training hardware plan" and "First training run" below.)

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
runs `train.py` there instead of on this laptop. **Done — this plan worked;
see "First training run" below.** The setup needed one extra fix not in the
original guide (the MIOpen crash), now added to `GPU_TRAINING_SETUP.md`.
Actual training time: ~2.3 minutes, far below the 10-30 minute estimate.

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

## First training run (2026-10-03, home PC GPU)

`train.py` was run on the home PC (Ultralytics 8.4.171, Python 3.12.10,
torch 2.9.1+rocm7.2.1, AMD Radeon RX 9070 XT) on the full 55-photo dataset
(44 train / 11 val). Full console output saved in `train_log.txt`.

**Problems hit and fixed along the way** (details in `ChallengesLog.md`
#15-#16):
- Training crashed with `miopenStatusUnknownError` (AMD's MIOpen library).
  Fixed by turning MIOpen off (`torch.backends.cudnn.enabled = False` at
  the top of `train.py`) — training still runs on the GPU.
- Ultralytics saved results to the wrong place
  (`runs/detect/models/runs/bottle_detector-2/`). Results were moved to
  `models/runs/bottle_detector/`, the stray `runs/` folder deleted, and
  `train.py` fixed to use an absolute output path + `exist_ok=True`.
  (Note: `models/runs/bottle_detector/args.yaml` still records the old
  `bottle_detector-2` name/path — it's just a record of that run's
  settings, not something any script reads, so this is harmless.)

**Result**:
- Early stopping kicked in at epoch 77 (no improvement for 20 epochs);
  **best epoch was 57**, saved as `weights/best.pt` (6.3 MB). Total
  training time **~2.3 minutes** (0.038 hours).
- Final validation of `best.pt` on the 11 val photos (1,297 bottles):
  **precision 0.999, recall 0.998, mAP50 0.995, mAP50-95 0.699**.
  In plain terms: almost every bottle was found (recall) and almost
  nothing that wasn't a bottle got flagged (precision). mAP50-95 is lower
  because it also grades how *tightly* each box fits the cap — that matters
  less for counting, which only needs one box per bottle.
- Inference speed on the 9070 XT: ~6.7 ms per image (will be much slower
  on the Orange Pi — real speed only known after RKNN conversion).

**Caveats — don't fully trust these numbers yet:**
1. **`max_det` cap**: Ultralytics warned that some photos contain up to
   **337 bottles**, but by default it reports at most **300 detections per
   image** (`max_det=300`). On the densest crates the model *cannot*
   report more than 300, so it would undercount, and the val metrics above
   may be slightly optimistic. Any inference/counting code must pass a
   higher limit (e.g. `max_det=500`), and validation should be re-run with
   that setting.
2. **Small val set**: 11 photos, several of which are the same physical
   crate photographed multiple times (see the matching-count notes
   above) — the val photos are likely very similar to some training
   photos, so these scores probably overstate how well it handles a
   genuinely new crate/lighting setup.
3. ~~Not yet checked as counts~~ — **done, see "Count check" below.**
   Still not tested on real-camera (Arducam) images — only phone photos.

### Count check (2026-10-03) — `tests/check_model.py`

New script: runs `best.pt` on the labeled photos and prints, per photo,
true count (lines in the label file) vs. model count, and saves annotated
images to `tests/outputs/model_check/`. Run from `Code/` with the venv:
`python tests/check_model.py` (val) or `python tests/check_model.py train`.

- **With Ultralytics' default settings it overcounted badly** (val: 167
  extra, IMG_4732 +63) — the model drew duplicate, slightly larger,
  low-confidence boxes around caps that already had a box. Fixed with
  settings alone, no retraining (details: `ChallengesLog.md` #18).
- **Production inference settings (use these everywhere — UI, Orange Pi
  loop, RKNN tests):** `imgsz=1280, conf=0.5, iou=0.4, max_det=1000`.
- **Results with those settings:**
  - Val (11 photos, never trained on): **1297/1297 — every photo exact.**
  - Train (44 photos): 4972 bottles, 22 off (0.44%), 40/44 exact.
    Remaining errors:
    - IMG_4818 (+14), IMG_4819 (+6): real bottles *outside* the crate
      (cardboard box / neighbouring crate at the photo edge) — the model
      counts any visible bottle. Production must frame or crop to the
      crate only (`ChallengesLog.md` #19).
    - IMG_4823, IMG_4824 (−1 each): the model counted 21 vs. 22 labeled —
      a small model undercount. Labels re-checked and confirmed correct by
      the user in makesense.ai (2026-10-03). (For reference only: the one
      unmatched label in each file is a zero-height entry —
      `0 0.677778 0.582353 0.003486 0.000000` /
      `0 0.670806 0.670588 0.003486 0.000000`.)

**Ground-truth rule (user decision, 2026-10-03):** the makesense.ai labels
are the final verdict on true counts — the user double-checks every
photo before exporting. When the model and a label disagree, treat it as
a model error; never "correct" or second-guess a label file.

## Orange Pi 3B bring-up (2026-10-06)

Bring-up guide: `ORANGE_PI_SETUP.md` (official Orange Pi Ubuntu 22.04
desktop image, vendor kernel 5.10 for the NPU driver; NPU driver check;
SSH so Claude can run commands from the PC; then camera → speaker → custom
LCD → touch, one at a time).

**Status: BOOTED, reachable over SSH, NPU driver present, camera working.**
First boot was blocked for most of the day by a corrupted GPT header
(partition-entry pointer rewritten from LBA 2 to 2016 on the Pi's first
boot — full story in `ChallengesLog.md` #20; the SD cards were never
faulty).

   **Current setup:**
   - **Boot: eMMC only (since 2026-10-07).** The running system was copied
     onto the 58.3 GB eMMC module with `pi/install_to_emmc.sh` (does what
     Orange Pi's menu-driven `nand-sata-install` does: fresh GPT sized to
     the whole eMMC, bootloader `idbloader.img` @ sector 64 + `u-boot.itb` @
     16384, FAT `/boot` + ext4 `/` with **new UUIDs** — root
     `2317443f-005a-4f77-849e-626c2f68b6e5`, boot `F446-73EF` — rsync of the
     live system, fstab + `orangepiEnv.txt` rootdev updated). Verified: GPT
     entry pointer 2 and backup at the last LBA (so the #20 bug can't
     trigger), boots with no SD/USB, NPU driver OK, `bottle_counter.py`
     still exact. The previous project's OS on the eMMC was erased (user
     approved).
   - The old SanDisk SD card still holds the previous two-device system
     (root UUID `fbf3a91f-…`). **Keep the SD card out of the Pi** — the
     eMMC bootloader may look at the SD card first and try to boot that old
     system. The USB pen drive was wiped on 2026-10-07 (one exFAT
     partition, label `ML_PROJECT`) and now carries a full copy of
     `C:\ML_Project` for working on the laptop.
   - Board SPI flash (16 MB) is **erased** — it held the previous project's
     custom U-Boot.
   - Pi IP: **192.168.1.115** (DHCP — may change after router restarts).
     SSH key from this PC is installed: `ssh orangepi@192.168.1.115` works
     without a password. Password is still the default `orangepi` (change
     it before the device leaves the bench).
   - Verified: kernel 5.10.160-rockchip-rk356x, Orange Pi 1.0.8 Jammy,
     3.8 GB RAM, **NPU driver `RKNPU v0.9.6` present**, idle temp ~58 °C.
   - Ubuntu 24.04 upgrade prompt disabled (`Prompt=never` in
     `/etc/update-manager/release-upgrades`) — RKNN needs 22.04.
   - **Arducam on the Pi works** (USB ID `0c45:6366` "Microdia Webcam
     Vitade AF", `/dev/video0`). Unlike on Windows (capped at 2592x1944),
     Linux offers the **full 3264x2448 (8 MP) at 15 fps in MJPG**.
     OpenCV 4.5.4 installed (`apt install python3-opencv`); verified
     `cv2.VideoCapture(0, cv2.CAP_V4L2)` + MJPG + 3264x2448 returns real
     frames (~0.15 s per frame read after warm-up). First test shots
     (`tests/outputs/pi_camera/`) looked slightly hazy — check for a
     protective film on the lens / autofocus settling before judging.
     Open question: capture at 3264x2448 or 2592x1944 — decide once real
     crate shots are compared (model runs at imgsz=1280 either way).
   - **Focus:** camera ships with autofocus off (`focus_auto=0`); manual
     `focus_absolute` 1-1023, lower = farther. With the camera resting
     steady (not hand-held — hand-held sweeps are too noisy to use), a
     sweep peaked clearly at **focus 150** (Laplacian sharpness ~330 vs
     <50 at 200+). Autofocus picked a worse value (144, softer). Plan: lock
     manual focus in the capture code, re-sweep once at the final mount
     height.
   - **First model run on Pi-camera photos (2026-10-06,
     `tests/outputs/pi_camera/counted_crate_*.jpg`)** — scene had no crate
     (suitcase, box with a printed photo, a water bottle). Model found 2-3
     boxes: the water bottle's cap (correct, 0.68) plus 1-2 false positives
     on small pale/dark spots in the printed photo (0.79, 0.54). Expected
     — the model only ever saw caps in blue crates. Reinforces the plan to
     crop each frame to the crate region. Real accuracy test still needs
     Arducam shots of actual crates.
   - PC note: Windows **Smart App Control** (on) intermittently blocks
     `_rocm_sdk_libraries_custom\bin\rocrand.dll` ("An Application Control
     policy has blocked this file") — retrying worked.
   PC network: `192.168.1.0/24`, router `192.168.1.1`, PC `192.168.1.135`
   (wired). No LCD yet — HDMI to a monitor for now.

**Not yet checked on the Pi:** speaker/audio, custom LCD, touch panel,
Wi-Fi.

## Model on the NPU (2026-10-07)

Done on the Pi itself ("route B" — no WSL2 on the PC; WSL/Docker aren't
installed there). Steps and results:

1. **PC:** `best.pt` → `best.onnx` (Ultralytics export, `imgsz=1280`,
   `opset=12`, `simplify=True`; output shape `(1, 5, 33600)` = cx, cy, w,
   h, score per candidate box).
2. **Pi:** venv `~/rknn-venv` with `rknn-toolkit2==2.3.2` +
   `rknn-toolkit-lite2==2.3.2` (torch 2.2.0, onnx 1.16.1, numpy 1.26.4,
   opencv-python-headless). **Gotcha:** the toolkit pins
   `onnxoptimizer==0.3.8`, which has no aarch64 wheel (pip tries to build
   it and fails on missing cmake). Installed the toolkit with `--no-deps`
   plus all other deps by hand — conversion works without onnxoptimizer.
3. **Pi runtime updated:** `/usr/lib/librknnrt.so` 1.4.0 (2022) → **2.3.2**
   (from the airockchip/rknn-toolkit2 GitHub repo, v2.3.2 tag); old file
   kept as `/usr/lib/librknnrt.so.1.4.0.bak`.
4. **Conversion** (`~/bottle/convert.py`, copy in `models/rknn/`):
   `target_platform='rk3566'`, `mean 0 / std 255`, calibration on 30 train
   photos. Took ~6.5 min on the Pi. Printed many
   `REGTASK: bit width of field value exceeds the limit, target: lite`
   errors — turned out harmless for FP16.
5. **Count check on the real NPU** (`~/bottle/npu_count.py`, letterbox to
   1280 like Ultralytics, `conf=0.5, iou=0.4`):
   - **FP16 (`best_fp16.rknn`, 9.1 MB): 1297/1297 — all 11 val photos
     exact, ~0.64 s per photo on the NPU.** ✅ This is the working model
     (copy at `models/rknn/best_fp16.rknn`; on the Pi in `~/bottle/`).
   - INT8 (`best_int8.rknn`): counts **0** on every photo (~0.23 s). Cause:
     the single `(5, 33600)` output mixes box coordinates (0-1280) and
     scores (0-1) on one INT8 scale, so every score rounds to 0. Fix if
     ever needed (≈3× faster): export with boxes and scores as separate
     outputs (Rockchip model-zoo style YOLOv8 export), then re-quantize.
     Not needed now — 0.64 s is fine for capture-then-count.

Timing above is NPU inference only (letterbox + NMS on the CPU add a
little; capture adds ~0.15 s).

## Capture-and-count program (2026-10-07) — `pi/bottle_counter.py`

The device's "engine" (no screen of its own — the touchscreen app will
call it). Lives in the repo at `Code/pi/bottle_counter.py`, deployed on
the Pi at `~/bottle/bottle_counter.py` next to `best_fp16.rknn`. Run with
the venv: `~/rknn-venv/bin/python bottle_counter.py` (camera) or
`... --image photo.jpg` (existing photos); saves the photo + a
`_counted.jpg` copy with boxes and "Bottles: N" to `~/bottle/captures/`.

What it does: opens the camera once (MJPG, 3264x2448, focus locked at
150, 3 s warm-up), takes a photo, crops to the crate (`CROP` setting —
currently the whole photo; set it once the mount is fixed), letterboxes to
1280, runs the FP16 model on the NPU, filters with `conf=0.5, iou=0.4`,
maps boxes back to the full photo. For the app: `BottleCounter()` once,
then `count_from_camera()` → `CountResult(count, boxes, photo, annotated,
seconds)`.

Tested: all 11 val photos exact (~0.65 s each incl. pre/post-processing),
boxes land correctly on the caps; live camera run works (scene had no
crate → 0).

## Immediate next steps (as of end of day 2026-10-06)

Done so far, for reference: model trained (2026-10-03) and count-checked
(val 1297/1297 exact with `conf=0.5, iou=0.4, max_det=1000`); Orange Pi
booted with NPU driver; Arducam captures 8 MP photos on the Pi with focus
locked at 150.

**Suggested order for the next session:**

1. ~~Convert the model for the NPU~~ — **done 2026-10-07**, FP16 version
   counts all val photos exactly at ~0.64 s (see "Model on the NPU").
2. ~~Run it on the Pi~~ — done (same section). Optional later: fix INT8
   for ~3× speed.
3. **Real crate photos from the Arducam** — camera resting steady over an
   actual crate at roughly the final mount height; re-run the focus sweep
   there, capture a batch, label in makesense.ai, and count-check. This is
   the phone→Arducam accuracy test; if counts are off, add these photos to
   the dataset (`add_new_photos.py`, or draft labels from `best.pt`) and
   retrain (~2-3 min on the 9070 XT).
4. ~~Write the Pi capture-and-count script~~ — **done 2026-10-07**,
   `pi/bottle_counter.py` (see "Capture-and-count program"). Still to set:
   the `CROP` region, once the mount is fixed.
5. **Exclude bottles outside the crate** — fixed crop region and/or camera
   framing (ChallengesLog #19).
6. ~~Move the Pi's system onto the eMMC~~ — **done 2026-10-07**, boots
   from the eMMC alone. Still to do: **change the default password**
   (`orangepi`), and optionally wipe the old SD card / pen drive.
7. Remaining peripherals: speaker, then custom LCD + touch when they arrive.
8. PySide6 UI shell, then wire in the counting function.
9. Physically confirm the production camera mount is directly overhead.
10. Open decisions: trigger for the "captured" audio cue (button vs. count
    stabilizing); microphone needed or not.
11. Housekeeping: delete `data/dataset/import_new/`.

Deprioritized on purpose: tilted-bottle robustness (staff keep bottles
upright — see "Second photo batch").
