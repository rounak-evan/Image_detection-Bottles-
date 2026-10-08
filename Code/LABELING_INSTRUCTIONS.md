# Reviewing and correcting the draft labels

**Status: both batches complete.**

- Batch 1 (16 photos, `data/Bottle Images (Upright)/`): completed
  2026-09-23 — corrected and merged into `data/dataset/`.
- Batch 2 (39 photos, `data/Bottle Images (new)/`): completed 2026-09-28
  — corrected and merged into `data/dataset/`. The staging folder used for
  this batch, `data/dataset/import_new/`, is now redundant and can be
  deleted.

**Full dataset (55 photos) is fully labeled, and the model has been
trained on it (2026-10-03)** — see `ClaudeContext/Projectsummary.md`,
"First training run". (`data/dataset/import_new/` was still on disk as of
that date.)
Keeping this doc for reference in case a future batch 3 needs the same
process — the steps below describe the general workflow (originally
written for batch 1, with batch 2 callouts added where the process
differed).

**Batch 3 (planned): real crate photos from the Arducam** — taken with
the camera resting steady over a crate (on the Orange Pi, or on the laptop
with `capture_photos.py`). For this batch, draft labels should come from
the trained model (`best.pt`), not the circle detector — they'll be much
closer to correct, so the makesense.ai pass becomes mostly checking.

**Ground-truth rule (user decision, 2026-10-03):** the labels exported
from makesense.ai are the final verdict on true counts — the user
double-checks every photo before exporting. If the model and a label
disagree, it's recorded as a model error.

`prepare_dataset.py` already wrote a *draft* bounding box around every
bottle cap it could find, using the same circle detector from
`circle_counter.py`. You now need to review each photo and fix mistakes
before training — otherwise the model just learns the circle detector's own
blind spots (missed tilted bottles, missed caps near the top of angled
photos, occasional false box on background texture).

**Tool: [makesense.ai](https://www.makesense.ai)** — free, runs entirely in
your browser (your images never leave your computer), no install, no
account. We switched to this after LabelImg (a desktop tool) kept crashing
unpredictably — likely an old, unmaintained tool running on a much newer
Python version than it was ever tested against. Browser-based sidesteps
that problem completely.

## 1. Gather the files you'll need

All in `Code/data/dataset/`:

- The photos: `images/train/` and `images/val/`
- The matching draft label files: `labels/train/` and `labels/val/`
  (one `.txt` per photo, YOLO format)
- `labels.txt` — the class list (just contains "bottle")

You can label a whole batch together in one session — it's simpler than
doing separate imports per photo. I'll help split the corrected labels
back into the train/val folders afterward.

**Batch 2 note:** the 39 new photos' draft `.txt` files (plus a copy of
`labels.txt`) are already gathered into one flat folder for you —
`data/dataset/import_new/` — so you can skip hunting through
`labels/train/` and `labels/val/` and just use that folder directly for
both loading images and importing annotations below. (The photos
themselves are still at `data/Bottle Images (new)/`, or in
`data/dataset/images/train/` and `images/val/` if you'd rather grab them
from there.)

## 2. Open makesense.ai and load the photos

1. Go to https://www.makesense.ai
2. Click **Get Started**
3. Choose **Object Detection**
4. Drag in the photos for whichever batch you're labeling (batch 1: all 16
   from `images/train` + `images/val`; batch 2: all 39 from
   `data/Bottle Images (new)/`)

## 3. Import the existing draft labels

Don't start labeling from scratch — import the draft boxes first:

1. Look for an **Actions** menu (top toolbar once your images are loaded)
2. Choose **Import Annotations**
3. Select format **YOLO**
4. When prompted, provide (all in one file-picker selection — the browser
   can't select across separate folders, so copy them into one flat folder
   first if they're not already together):
   - The per-image `.txt` annotation files (batch 1: from `labels/train/`
     and `labels/val/`; batch 2: from `data/dataset/import_new/`)
   - The `labels.txt` file (batch 1: `data/dataset/labels.txt`; batch 2:
     already included in `import_new/`) — this tells makesense.ai that
     class `0` means "bottle"

If the exact menu wording looks different from this (the site updates
occasionally), look for anything mentioning "import" near where images or
labels are managed — tell me what you see and I'll help you find it.

## 4. For every photo, fix three things

- **False boxes** — a box sitting on the crate, floor, or shadow instead of
  a real bottle: click it, delete it.
- **Missed bottles** — no box around a real cap (common on tilted bottles
  and the far/top edge of angled photos): draw a new box around it.
- **Loose/offset boxes** — box present but not snug around the cap: drag its
  edges to tighten it.

**Batch 1:** start with **IMG_4743 and IMG_4730** (the tilted-bottle and
perspective-distorted ones) — those need the most correction. Clean
overhead photos like IMG_4723 should need little to no fixing.

**Batch 2:** all 39 photos are clean overhead shots (no tilted bottles),
and the draft parameters were tuned specifically for this batch's cap
size — so coverage should be good across the board already, no particular
photo should need dramatically more work than another. Still worth a full
visual pass on each, since "good coverage" isn't the same as "every cap
correctly boxed."

**Tip:** you don't have to get every single one of hundreds of bottles
perfect on the densest photos — reasonable coverage is enough for the
model to learn the shape. Prioritize fixing the worst photos over
nitpicking pixel-perfect boxes on the easy ones.

## 5. Export when done

**Actions → Export Annotations → YOLO format.** This downloads a zip of
corrected `.txt` files (one per photo).

## 6. Get the corrected labels back into the project

Unzip the download somewhere (e.g. your Downloads folder), then tell me
where it landed — I'll sort the corrected `.txt` files back into
`data/dataset/labels/train/` and `data/dataset/labels/val/` matching our
existing split, so nothing needs to be moved by hand.

## 7. Train

Once the corrected labels are back in place, run `train.py` to fine-tune
the model (on the home PC — see `GPU_TRAINING_SETUP.md`). Note: retraining
overwrites `models/runs/bottle_detector/`, so copy the current
`weights/best.pt` somewhere safe first if you want to compare old vs. new.
