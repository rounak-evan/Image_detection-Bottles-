# Challenges & Bugs Log

A study log of every real problem hit while building this project, in the
order they happened. Each entry: what broke, how we figured out *why*
(not just *that*), and what fixed it. The "why this matters" lines are the
transferable lessons — the specific bug won't recur, but the underlying
pattern will.

---

## 1. Pretrained model detected zero bottles on real photos

**Symptom:** `imagedetcode.py` (YOLOv8n pretrained on COCO) returned 0
bottles on all 16 real crate photos — even lowering the confidence
threshold to 0.01 changed nothing.

**Diagnosis:** Ran raw, unfiltered detection (no class/confidence filter
at all) on one photo directly — still zero detections of *anything*, not
just "bottle." That ruled out "threshold too strict" and pointed at a
deeper mismatch.

**Root cause:** COCO's "bottle" class is built almost entirely from
**side-view** photos (a bottle's neck/shoulder/body silhouette). Our real
camera setup shoots **top-down** onto a packed crate — a grid of circular
caps seen from directly above looks nothing like what the model learned
to call a "bottle." This is a *domain mismatch*, not a tuning problem.

**Fix:** Built a classical computer-vision fallback (`circle_counter.py`,
Hough Circle Transform) that detects the caps directly as circles, with
no training data needed.

**Why this matters:** A model that's "pretrained" only knows what it was
shown. Before assuming a tuning parameter is wrong, check whether the
model has ever seen anything resembling your actual input — test with the
filter *removed*, not just loosened.

---

## 2. Classical circle detector had two real failure modes

**Symptom:** `circle_counter.py` worked well on some photos (39/39
correct on a clean overhead shot) but badly on others.

**Diagnosis:** Visually compared the annotated output against the source
photo for several cases, not just trusting the printed count.

**Root causes (two distinct ones):**

- **Perspective distortion** — in photos taken at more of an angle, caps
  farther from the camera appear smaller in the frame and fell outside
  the detector's expected pixel-size range. Whole sections of a crate
  went undetected.
- **Tilted/leaning bottles** — a cap only looks like a circle when viewed
  nearly straight-on. Tilted bottles show an *ellipse* from a top-down
  camera, which a circle detector structurally cannot match. Nearly 100%
  miss rate on these, plus false positives on the crate's textured
  background.

**Fix:** No parameter tweak fixes structural mismatches. Decision: pursue
both a hardware fix (mount the camera more directly overhead) and a
software fix (train a custom model that learns actual bottle appearance,
tilt included).

**Why this matters:** Two different problems can produce a similar
symptom ("bad count"). Fixing only the first one you find can still leave
the second silently broken — check multiple examples before declaring a
fix complete.

---

## 3. LabelImg (desktop labeling tool) crashed unpredictably

**Symptom:** LabelImg opened but closed randomly during use — no
consistent trigger (not tied to a specific action like saving or opening
a particular image).

**Diagnosis:** Checked the installed tool's age against the installed
Python version — LabelImg was last updated around 2022; the system was
running Python 3.14 (released years later). "Unpredictable crash, no
reproducible trigger" is the signature of general incompatibility, not a
single fixable bug.

**Fix:** Switched to [makesense.ai](https://www.makesense.ai) — runs
entirely in-browser, so it has no dependency on the local Python version
at all.

**Why this matters:** An old, unmaintained tool running on a much newer
language/runtime version than it was ever tested against is a real
category of bug worth recognizing quickly, rather than debugging deeper
and deeper into a tool that was simply never designed for this
environment.

---

## 4. makesense.ai import failed: "labels.txt file is required"

**Symptom:** Selecting the annotation `.txt` files in the import dialog
still produced an error saying `labels.txt` was missing, even though it
existed on disk.

**Diagnosis:** Noticed the annotation files and `labels.txt` lived in
different folders (`labels/train/`, `labels/val/`, and `dataset/`
respectively).

**Root cause:** A browser's native file picker can only select files from
**one folder at a time** — it can't multi-select across separate folders
in one action. The import needs all files (annotations + `labels.txt`)
selected together in a single picker action.

**Fix:** Copied everything needed into one flat folder (`import_all/`),
so a single file-picker selection could grab it all at once.

**Why this matters:** A browser tool's constraints aren't always about
the tool's *feature support* — sometimes it's a basic OS/browser API
limitation (like single-folder file selection) that no amount of
clicking around the tool's UI will get past. Restructure the files to fit
the constraint instead.

---

## 5. Validation-set photos silently skipped during labeling

**Symptom:** After the first labeling pass, box counts for the 3
validation photos exactly matched their original (flawed) draft counts —
meaning they'd never actually been corrected.

**Diagnosis:** Compared box counts (`wc -l` on each label file) before vs.
after the labeling session, for every photo — not just spot-checking a
couple. The 13 training photos all showed real, different counts; the 3
validation photos showed *identical* counts to their drafts.

**Root cause:** The validation photos were never dragged into the
makesense.ai session in the first place — an easy thing to miss since
they live in a separate folder (`images/val/`) from the training photos.

**Fix:** Ran a small separate labeling pass for just those 3 photos.

**Why this matters:** "The tool didn't show an error" isn't the same as
"the step actually happened." Verifying a batch operation by checking
*every* item's before/after state (not just a sample) caught something a
visual skim would likely have missed.

---

## 6. First frame after opening a camera is often invalid

**Symptom:** Capturing a frame immediately after `cv2.VideoCapture(i)`
returned a solid black or blown-out white image — not a real photo of
anything.

**Diagnosis:** Re-captured after discarding several frames first (with a
short delay) — the next real frame was a normal, correctly exposed photo.

**Root cause:** A camera sensor's auto-exposure and auto-white-balance
need a moment to stabilize after the stream opens. The very first frame
or two is often captured mid-adjustment.

**Fix:** Standard pattern now used everywhere in this project's capture
code: sleep briefly, discard ~15-30 warm-up frames, *then* keep a frame
for real use.

**Why this matters:** A hardware/driver "first result is garbage" pattern
is common enough to expect by default with any live sensor (cameras,
some other real-time hardware) — don't assume the very first reading is
representative.

---

## 7. Two camera indices both "worked" — only one was the real camera

**Symptom:** `cv2.VideoCapture(0)` and `cv2.VideoCapture(1)` both reported
successfully opening and both returned frames.

**Diagnosis:** Captured and visually inspected an actual frame from each
index, rather than trusting `isOpened()`/`read()` success alone. Index 0
was consistently pure black (brightness ~0.5/255) even after warm-up;
index 1 showed a real, recognizable scene matching what was physically
held in front of the lens.

**Root cause:** Many Windows laptops have a second built-in camera device
(often an infrared camera for Windows Hello face login) that also
enumerates as a valid `VideoCapture` index and also "successfully opens"
— it just never produces a normal visible-light image.

**Fix:** Identified index 1 as the real Arducam by content, not by index
number assumption.

**Why this matters:** "Opens without error" is a weak signal for "is the
device I think it is." When multiple devices are plausible, check actual
output content, not just success/failure of the API call.

---

## 8. Default camera resolution silently far below actual capability

**Symptom:** Nothing crashed — but frames were only 640×480 by default,
much lower than the Arducam's rated 8MP sensor.

**Diagnosis:** Explicitly requested several resolutions via
`cap.set(cv2.CAP_PROP_FRAME_WIDTH/HEIGHT)` and checked what was actually
negotiated back (not just assuming the request succeeded).

**Root cause:** OpenCV opens a `VideoCapture` at a conservative default
resolution unless a higher one is explicitly requested — this is silent,
not an error.

**Fix:** Documented as a required step for any future capture code: call
`cap.set(...)` for width/height right after opening, and confirmed the
camera can actually deliver up to 2592×1944 over USB 2.0 (requesting the
full 8MP/3280×2464 gets clamped down to this by the driver).

**Why this matters:** Some settings have safe-but-suboptimal defaults
that never throw an error — "it worked" doesn't mean "it worked at the
capability you assumed." Explicitly verify capacity-related settings
rather than trusting silent defaults.

---

## 9. Windows file lock blocked a folder move during reorganization

**Symptom:** `mv dataset data/` failed with `Permission denied`, even
though nothing was visibly open in that folder.

**Diagnosis:** Retried the plain move again (ruled out a one-off
transient lock) — still failed the same way.

**Fix:** Used `cp -r` (copy) followed by `rm -rf` (delete original)
instead of a direct rename — this worked where the atomic move didn't.

**Why this matters:** On Windows, a file can be locked by something
non-obvious (an indexer, antivirus scan, an editor's file-watcher) even
when no window is visibly showing it open. A copy+delete sidesteps the
lock in a way a rename sometimes can't, since it doesn't require
exclusive access to the *directory entry* the same way.

---

## 10. Moving a script broke its import of a sibling script

**Symptom:** After relocating `batch_test.py` into a `tests/` subfolder
(while `circle_counter.py` stayed at the project root), the plan was for
`from circle_counter import ...` to keep working — but it would have
silently broken on the next run.

**Diagnosis:** Understood *before* running it that Python only
auto-adds a script's *own* folder to its search path when run directly —
not the folder of whatever script originally called it, and not any
project "root" by default.

**Fix:** Added an explicit `sys.path.insert(0, ...)` at the top of
`tests/batch_test.py` pointing at the parent folder, before the import.

**Why this matters:** Reorganizing files isn't just a filesystem
operation — relative imports between Python files are tied to directory
structure. Moving files can silently break imports that used to work by
coincidence of being in the same folder.

---

## 11. Documentation drifted out of sync with the actual project state

**Symptom:** `Projectsummary.md` still referenced old file paths
(`dataset/` instead of `data/dataset/`, `yolov8n.pt` instead of
`models/yolov8n.pt`) and the abandoned LabelImg tool, well after the
folder reorg and the switch to makesense.ai had already happened.

**Diagnosis:** Did a deliberate full re-read of the memory file end to
end and cross-checked every path/tool reference against what actually
exists on disk now, rather than assuming earlier edits caught everything.

**Fix:** Corrected every stale reference; relabeled one section
explicitly as "SUPERSEDED — kept for reference only" so a future reader
(human or AI) wouldn't mistake old narrative for current instructions.

**Why this matters:** Documentation doesn't automatically follow code
changes — every past decision recorded as "done" needs revisiting
whenever something it depended on (a path, a tool, a filename) changes
later. A living memory doc needs periodic consistency audits, not just
additions.

---

## 12. No GPU available — CPU training would take hours

**Symptom:** About to run `train.py`, no error yet — just a practical
concern before committing to a long-running job.

**Diagnosis:** Checked `torch.cuda.is_available()` *before* starting
training, not after watching it crawl for an hour.

**Fix:** Decided to move training to a separate PC with a GPU rather than
run on CPU.

**Why this matters:** For anything long-running (training, batch
processing), verify the execution environment's capability *before*
starting, not by watching progress and hoping. A five-second check saves
potentially hours of wasted, unmonitored compute.

---

## 13. AMD GPU needs ROCm, not CUDA — and Windows support is version-specific

**Symptom:** Not a bug exactly — a real constraint discovered during
planning: `pip install torch` alone would not enable GPU acceleration on
an AMD card.

**Diagnosis:** Researched current (2026) documentation rather than
relying on possibly-outdated general knowledge, since GPU compute stack
support changes fast. Confirmed the RX 9070 XT needed a *specific*
release (ROCm 7.2.1 + PyTorch 2.9.1) built for a *specific* Python
version (3.12 exactly — not whatever the newest available Python was).

**Root cause:** ROCm/PyTorch packages for Windows are distributed as
prebuilt binary wheels, which are compiled against one exact Python
version's internal API. Newer Python versions don't automatically get
compatible builds — the maintainer has to publish new wheels for each
version, and that lags behind Python's own release schedule.

**Fix:** Documented the exact required Python version, driver version,
and install command in `GPU_TRAINING_SETUP.md`. Also flagged a related
gotcha: installing `ultralytics` *after* the ROCm-enabled PyTorch can
silently pull in a plain CPU-only `torch` as a dependency and overwrite
it — so install order matters, and it's worth re-verifying GPU detection
after every subsequent `pip install`.

**Why this matters:** "Latest version" is not always "most compatible
version" — for compiled/binary packages specifically, match the *exact*
version the specific release you need was actually built for. This is
the same underlying pattern as the LabelImg failure (#3), just the
inverse direction (too new vs. too old).

---

## 14. Second photo batch: circle detector missed almost everything again

**Symptom:** After adding 39 new photos, 6 of them returned exactly 0
draft-labeled boxes from `circle_counter.py`, despite clearly containing
packed bottles.

**Diagnosis:** Tested the same photo with several different radius
ranges directly, rather than assuming the photo itself was somehow bad.
Found that a much smaller radius range (10-25px instead of the tuned
25-55px) picked up 120 circles on a photo that had returned 0.

**Root cause:** The new batch was shot in **landscape** orientation vs.
the first batch's **portrait** orientation. Because the detection
pipeline resizes every photo to a fixed pixel width (900px) before
detecting circles, and a phone's camera sensor has two *different*
angular fields of view along its two axes, rotating the phone swaps which
of those two angles becomes the image's width. Landscape captured a
physically wider slice of the room into the same 900 pixels, so each
real-world-sized bottle cap ended up occupying fewer pixels — falling
below the tuned minimum radius.

**Fix:** Added an optional parameter override to the detection function
and used a widened, batch-specific radius range just for this batch's
draft-labeling pass — without changing the original tuned parameters used
elsewhere.

**Why this matters:** Same root category as issue #2 (perspective
distortion) — any hand-tuned pixel-size assumption is fragile to changes
in shooting setup (distance, zoom, and here, even just camera
*orientation*). This is a concrete illustration of why the project is
moving toward a trained model instead of hand-tuned classical CV: a
trained model generalizes across a reasonable range of apparent scales
without needing per-batch recalibration.

**Follow-up insight (2026-09-25):** this advantage compounds with a
second, separate fact about the production setup — worth keeping as two
distinct points, not one blurred "resolution" concern:

1. **Orientation/spacing (this issue, fully resolved by the fixed mount).**
   The problem here was specifically that rotating the phone changed how
   many pixels the same real-world bottle cap occupied — an *apparent
   size/spacing* problem, not a pixel-density problem. The production
   Arducam sits in one fixed mount, one constant orientation, forever — so
   this exact failure mode structurally cannot recur at inference time,
   full stop. On top of that, YOLO's architecture is natively multi-scale
   (it detects using several internal feature resolutions at once — a
   "feature pyramid" — specifically so one trained model handles both
   large-in-frame and small-in-frame objects), unlike `circle_counter.py`'s
   single fixed radius window, so even residual scale variation (e.g.
   crate placed slightly closer/further) is tolerated far better.
2. **Raw capture pixel density (a separate, still-open concern — issue #8).**
   This is genuinely different from (1): it's about how many actual
   pixels the camera captures per frame, not about orientation or spacing.
   The camera silently defaults to 640×480 unless the code explicitly
   requests higher resolution. That's unrelated to the orientation fix
   above and stays a real thing to get right in the eventual capture loop
   — feeding the trained model a much lower pixel density than it was
   trained on would still degrade accuracy, just gradually rather than the
   hard cliff-to-zero Hough Circles hit.

---

## Recurring patterns across these issues

A few lessons showed up more than once, worth remembering as general
debugging habits rather than one-off fixes:

1. **When something returns a plausible-but-wrong result, remove filters/
   thresholds entirely before assuming they're just miscalibrated** (#1).
   A confidence threshold of 0 still filtering everything out means the
   problem isn't the threshold.
2. **"No error" isn't the same as "correct."** Cameras that open without
   error (#7), settings with silent low defaults (#8), and tools that
   don't throw an exception (#5) can all still be wrong — verify actual
   output content, not just absence of errors.
3. **Version mismatches (too old *or* too new) cause unpredictable,
   hard-to-pin-down failures** (#3, #13) — when a crash has no
   reproducible trigger, check the age/version gap between the tool and
   its runtime environment before debugging deeper.
4. **Hand-tuned numeric assumptions (pixel sizes, thresholds) are
   fragile to any change in input conditions** (#2, #14) — this is the
   core argument for preferring a trained model over hardcoded heuristics
   once the problem is complex enough.
5. **File system operations (moves, imports) can have hidden
   dependencies** (#9, #10) — a folder lock or a broken import path won't
   always announce itself clearly; understand what depends on a path
   before changing it.
6. **Documentation needs the same maintenance discipline as code** (#11)
   — a fact recorded as true when written can silently become false
   later without any single "breaking" event.
