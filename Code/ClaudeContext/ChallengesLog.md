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

## 15. GPU training crashed with `miopenStatusUnknownError` (2026-10-03)

**Symptom:** With PyTorch correctly detecting the RX 9070 XT, `train.py`
still crashed during training with `miopenStatusUnknownError`.

**Root cause:** MIOpen is AMD's library of hand-optimized GPU routines for
neural-network operations (AMD's equivalent of NVIDIA's cuDNN). The
Windows ROCm 7.2.1 release is new, and MIOpen hit an internal error on
this card/workload — a bug in the library, not in our code or setup.

**Fix:** Added `torch.backends.cudnn.enabled = False` at the top of
`train.py`. On a ROCm build of PyTorch, this "cudnn" switch actually
controls MIOpen, so turning it off makes PyTorch use its own built-in GPU
code instead. Training still runs on the GPU — and it was fast anyway
(~2.3 minutes for the whole run).

**Why this matters:** "The GPU is detected" (`torch.cuda.is_available()`
→ `True`) only proves the basic connection works — the optimized libraries
layered on top can still fail. When a newly-released stack crashes inside
an optimization library, switching that one optimization off is a quick,
low-risk way to get unblocked. Also: on AMD, many settings still carry
NVIDIA names (`cuda`, `cudnn`) for compatibility — the name doesn't tell
you which vendor's code is actually running.

---

## 16. Training results saved to an unexpected nested folder (2026-10-03)

**Symptom:** `train.py` printed that weights were saved under
`models/runs/bottle_detector/`, but they actually landed in
`runs/detect/models/runs/bottle_detector-2/`.

**Root cause (two separate behaviors):**
- Newer Ultralytics versions treat a *relative* `project=` path as
  relative to their own default `runs/detect/` folder, not to the current
  folder — so `models/runs` became `runs/detect/models/runs`.
- By default Ultralytics never overwrites a previous run's folder; if
  `bottle_detector` already exists (e.g. from an earlier crashed attempt),
  it silently creates `bottle_detector-2`, `-3`, etc.

**Fix:** Moved the results to `models/runs/bottle_detector/`, deleted the
stray `runs/` folder, and changed `train.py` to build an absolute path
from the script's own location
(`Path(__file__).parent / 'models' / 'runs'`) and pass `exist_ok=True`.

**Why this matters:** The success message at the end of `train.py` was a
hardcoded string, not the real save location — it said "saved to X" no
matter where the files actually went. Trust the tool's own reported path
(here, Ultralytics' "Results saved to ..." line) over a message you wrote
yourself ahead of time. Same family as pattern #2 below: "no error" isn't
"correct."

---

## 17. Densest crates exceed the model's default detection limit (open)

**Symptom:** A warning during training: dataset images contain up to 337
objects, but `max_det=300`.

**Root cause:** Ultralytics caps how many detections it reports per image
(default 300) to keep post-processing fast. Most use cases never come
close; our densest crates do.

**Status: handled in `tests/check_model.py`** (`max_det=1000`), which
confirmed the 337-bottle photos are counted exactly once the cap is
raised. The trained model itself is fine — the cap is only applied when
*reporting* results — but every future counting script (UI, Orange Pi
loop) must pass a higher `max_det` too.

**Why this matters:** A silent upper limit on output turns into a silent
undercount exactly in the hardest cases (the fullest crates). Same lesson
as #8 (camera resolution default): safe defaults built for typical use
can quietly be wrong for yours — read warnings even when training
"succeeds."

---

## 18. Near-perfect training scores, but counts 13% too high (2026-10-03)

**Symptom:** Training reported precision 0.999 / recall 0.998, yet the
first real count check (`tests/check_model.py`, Ultralytics' default
settings) overcounted 4 of the 11 val photos badly — IMG_4732 got 189
instead of 126 (+50%). 167 extra bottles in total.

**Diagnosis:** Matched every predicted box to every labeled box (by
overlap) instead of only comparing totals. Result: **zero** missed bottles
on any photo; every extra box overlapped another predicted box and had low
confidence (median 0.3-0.44 vs ~0.85 for real hits). Drawing them showed
each one was a second, slightly larger box around a cap that already had
a correct box.

**Root cause:** YOLO removes duplicate boxes with a step called NMS
(non-maximum suppression), but only if two boxes overlap by more than a
threshold — default 70% (`iou=0.7`). A slightly bigger box wrapped around
a smaller one overlaps by less than that, so both survive. Training's
precision didn't show it because Ultralytics reports precision at
whichever confidence cutoff gives the best score — and that cutoff was
above these low-confidence duplicates.

**Fix:** No retraining needed — settings only. Swept confidence
(0.25-0.6) × overlap (0.7/0.5/0.4); chose `conf=0.5, iou=0.4`. Result:
**all 11 val photos counted exactly (1297/1297)**, and on the 44 training
photos 40/44 are exact — the rest are #19 plus a one-bottle undercount
on two photos (see below). Bottle caps in a crate sit side by side and never genuinely
overlap 40%, so the lower overlap threshold doesn't risk merging two real
bottles.

**Remaining small undercount:** IMG_4823 and IMG_4824 — model counted
21, labels say 22. Initially suspected a label mistake (the unmatched
label in each is a zero-height entry), but the user re-checked both in
makesense.ai and confirmed the labels are correct. The makesense.ai labels
are the ground truth for this project, so this is recorded as a −1 model
error on each.

**Why this matters:** A summary score answers a slightly different
question than the one you care about. "Precision at the best threshold"
isn't "count at the threshold I'll actually use." Always measure the
real end-goal (here, count per photo) with the real settings — and when
a total is off, look at *which* boxes are wrong before deciding whether
the model, the settings, or the labels are at fault.

---

## 19. The model counts every bottle it can see — including outside the crate

**Symptom:** IMG_4818 counted 164 vs 150 labeled; IMG_4819 156 vs 150.

**Diagnosis:** The extra boxes were all high-confidence (~0.82), not
duplicates. Viewed them: they're real bottles in a cardboard box / the
neighbouring crate at the edge of the photo, outside the crate being
counted — correctly *not* labeled, since they aren't in this crate.

**Root cause:** Not a model error — the model was asked "find bottles"
and did. It has no concept of "the crate I'm supposed to count."

**Status: open, needs a production decision.** Options: (1) mount and
frame the camera so only the crate is visible, (2) crop each frame to a
fixed crate region before counting (easy, since the mount is fixed), or
(3) later, teach the model "crate" too. (1) + (2) together are simplest.

**Why this matters:** Labels encode a *rule* ("only bottles in this
crate") that the model can only learn if it's visible in the data. When
a rule depends on context the model never learned, enforce it in code or
in the physical setup rather than hoping the model infers it.

---

## 20. Orange Pi 3B stuck at `(initramfs)` on first boot (2026-10-06, SOLVED)

> **Short version:** the real cause was a **corrupted GPT header**, not the
> SD card, the SD slot, or the SPI bootloader. On first boot, something on
> the Pi (almost certainly Rockchip U-Boot's GPT "repair" for a disk larger
> than the image) rewrote the primary GPT header with the partition-entry
> pointer changed from LBA 2 to LBA 2016 — where no entries exist. Linux
> checks the entry CRC, finds garbage, rejects the table and (without the
> `gpt` boot flag) never falls back to the valid backup → no partitions.
> Fixed by setting the pointer back to 2 and recomputing the header CRC.
> Read the "Resolution" section below; the hypotheses in between were wrong
> but are kept as a record of how we got there.

**Symptom:** After flashing the official image
(`Orangepi3b_1.0.8_ubuntu_jammy_desktop_xfce_linux5.10.160.img`, SHA-256
verified, Etcher-verified), the Pi never appeared on the network. Status
LEDs looked healthy (red steady = power, green blinking = kernel
heartbeat, LAN port blinking). With an HDMI screen attached: boot stopped
at a BusyBox `(initramfs)` prompt — `ALERT! UUID=fbf3a91f-48ba-4b71-acfd-2d0bb10d259c does not exist`.

**Diagnosis (step by step):**
- Network scans (IPv4 ping sweep, SSH port scan, IPv6 link-local) found
  nothing — because the OS never got far enough to start networking. The
  router was never the problem.
- `fbf3a91f-…` was confirmed (read straight out of the `.img` file) to be
  the image's own root partition — so the early bootloader *did* read the
  SD card correctly.
- `cat /proc/partitions` showed the SD card (`mmcblk1`, correct 59.7 GB
  size) but **no partitions under it** — Linux could see the card but not
  read its partition table.
- An eMMC module with an older OS was attached (`mmcblk0`, with its own
  different UUIDs). Removed it — same failure, so it wasn't the (only) cause.
- Card checked back on the PC: GPT partition table intact and identical to
  the image (partition 1 GUID matches the `ubootpart=` the Pi reported).

**Likely root cause:** SD card ↔ board compatibility. The bootloader reads
the card in a slow, conservative mode (works); the Linux kernel switches it
to a high-speed mode, which fails with this card (EVM Elite 64GB), so the
partition table can't be read. Not a bad flash and not card damage.

**Confirmed via the kernel log** (`grep -i mmc /dev/kmsg` at the
initramfs prompt): on the SD slot (`mmc1`, `fe2b0000.dwmmc`) the kernel
tries UHS SDR104 (~150 MHz), gets `All phases bad!` /
`tuning execution failed: -5` / `error -5 whilst initialising SD card`
(twice), falls back to 50 MHz high-speed mode and detects the card
(`mmcblk1 … 59.7 GiB`) — but the partitions still never appear. The
Wi-Fi chip (`mmc2`) tunes fine at full speed, and the eMMC controller
(`fe310000.sdhci`) read the old eMMC OS's partitions fine on the first
boot. So the failure is specific to the SD slot + this card; the log
can't say whether the card or the slot's signal is the weak side.

**Update — decision changed:** the user then mentioned this board came
from an earlier project that booted it fine from a **SanDisk** SD card
(that project's OS is also what was on the eMMC). So the SD slot is known
good → the EVM card is the incompatible side. **Next step: SanDisk card**
(the old project's card if it's free to wipe — back it up to the PC first
if unsure — or a new SanDisk Ultra/Extreme 32-64GB). The eMMC becomes a
later upgrade: once booted from SD, the system can be copied onto the
eMMC from the Pi itself, no adapter needed. eMMC-via-USB-adapter remains
the fallback if a SanDisk card also fails.

**Update 2 — the card wasn't the cause either:** a new SanDisk 64GB card
(flashed + verified) failed identically. Next suspect: the board's 16 MB
SPI flash held a custom U-Boot (`U-Boot 2017.09-orangepi (Sep 21 2026 -
12:26:41 +0530)`, built by the previous project) that the boot ROM runs
before eMMC/SD. With the user's go-ahead it was erased from the initramfs
prompt (`cat /dev/zero > /dev/mtdblock0`, then `sync` — the flush takes
minutes; `grep -a -c 'U-Boot' /dev/mtdblock0` → `0` confirmed empty).
**Still the same failure**: SDR104 tuning fails, falls back to 50 MHz,
card detected (`mmcblk1: mmc1:aaaa SK64G 59.5 GiB`), no partitions.
Conclusion: the SD slot fails under this image's kernel on this board
regardless of card or bootloader — likely a device-tree/board-revision
mismatch or a hardware quirk in the slot's voltage switching (unproven).
Note the previous project's SPI U-Boot is now gone — their eMMC OS may
need its bootloader reinstalled if they ever reuse this board.

**Workaround chosen:** flash the same image to a USB pen drive and boot
with SD + USB both inserted. The bootloader still loads the kernel from
the SD (which works at low speed), and the kernel then finds root
`UUID=fbf3a91f-…` on the USB drive (identical image → identical UUID).
Once booted: install to eMMC from the running system (Linux reads the
eMMC fine — seen on the first boot), then investigate the SD slot.

**The USB drive failed the same way — which killed the "SD slot" theory.**
`sda` appeared with no partitions, so the problem wasn't SD-specific.

**Resolution — what was actually wrong:**
1. At the initramfs prompt, proved the Pi reads the USB drive correctly:
   `grep -a -m 1 -c "EFI PART" /dev/sda` → `1`, and
   `cmp /dev/sda /dev/mtdblock0` → `differ: char 449`, exactly the first
   non-zero byte computed from the `.img` on the PC (the erased SPI chip
   is all zeros, so it works as a reference). `blockdev --rereadpt
   /dev/sda` → still no partitions. So: data read fine, table *rejected*.
2. Back on the PC (elevated, read-only dump of LBA 0-33 and the last 34
   sectors), compared byte-by-byte with the image. The pen drive's
   primary header had been **rewritten after flashing**: alternate-header
   LBA and last-usable LBA moved to the true end of the 57 GB drive
   (fine), but the **partition-entry LBA changed from 2 to 2016**, and no
   entries were ever written at 2016. The real entries were still intact
   at LBA 2, and a fully valid backup GPT (header + entries) had been
   written at the end of the disk.
3. Linux's GPT parser verifies the entries' CRC at the pointed-to LBA →
   fails → rejects the primary, and only tries the backup if booted with
   the `gpt` kernel parameter → no partitions at all, and no log message
   (the kernel prints nothing when no parser recognises a table).
4. **Fix:** rewrote LBA 1 only — entry pointer back to 2, header CRC
   recomputed (script `fix_entlba.ps1` in the session scratchpad; it
   refuses non-USB or >200 GB disks, verifies the entries CRC at LBA 2
   before writing, and saves the original sector first). The Pi then
   booted straight to the desktop.
5. Confirmed on the running Pi: the SanDisk SD card has **the same damage**
   (entry pointer 2016, backup moved to its last LBA 124735487). So both
   SD cards were always fine — the SDR104 tuning warnings were real but
   harmless (fallback to 50 MHz works).
6. Rebooted to check the "repair" doesn't recur: pen-drive pointer still
   2 after reboot — it only happens once, while the GPT doesn't match the
   disk size.

**Current boot setup (2026-10-06):** SanDisk SD card (U-Boot + kernel are
loaded from it — U-Boot reads the backup GPT fine) + USB pen drive
(SanDisk 3.2 Gen1, 57.3 GB; Linux root `/dev/sda2`, auto-expanded to
55.7 GB). Both hold the same image, but only the USB's partitions are
visible to Linux, so there's no duplicate-UUID clash. **If the SD card's
GPT is ever fixed too, both drives would expose the same UUIDs — don't
fix it without removing the USB setup first.**

**Why this was so hard to find:** every symptom pointed somewhere else
first — no network (looked like the router), SD tuning errors (looked
like the card/slot), a custom bootloader on SPI (looked like a mismatch).
Each was real but harmless. The decisive steps were (1) proving the
*data* was readable before blaming hardware, and (2) comparing the actual
bytes on the drive against the known-good image instead of trusting
"Etcher verified it" — the damage happened *after* flashing, on the Pi.

**Lesson:** ask about the hardware's history early — "this board already
booted from a SanDisk card" pointed at the card, but "with a different,
custom-built OS" was the more important half of that sentence. Also noted: the board has a 16 MB SPI flash chip
(`mtdblock0`) — the boot ROM checks SPI before eMMC/SD, so if a new card
still fails, check whether an old bootloader lives there.

**Why this matters:** Status lights and "it powers on" only prove the
earliest stages work. When something is invisible on the network, look at
the device directly (a screen, once) before debugging the network — here
the network was fine and the OS simply never finished booting. And
"verified flash" proves the card *holds* the right data, not that the
target device can *read* it.

---

## 21. Hand-held focus tuning gave contradictory answers (2026-10-06)

**Symptom:** Sweeping the Arducam's manual focus over a keyboard while
holding the camera by hand: first sweep said focus 150 was best
(sharpness 103), a second sweep minutes later gave 150 only 37 and picked
focus 1, with scores bouncing up and down instead of forming one peak.

**Root cause:** small changes in hand height/angle between shots changed
sharpness more than the focus setting did — the measurement was noisier
than the thing being measured.

**Fix:** rested the camera on something steady and re-swept: a clean,
single peak at **focus 150** (~330, falling off on both sides), and three
follow-up shots all scored ~330. Also found the camera ships with
autofocus **off**; enabling it chose a softer focus (144) — for a fixed
mount, locked manual focus is preferable anyway.

**Why this matters:** before trusting a measurement, check it's
repeatable — take the same measurement twice. If the repeat disagrees
with the original, fix the setup (here: hold the camera still) before
tuning anything.

---

## 22. Windows Smart App Control blocked a GPU library (2026-10-06)

**Symptom:** Running the model on the PC failed with
`OSError: [WinError 4551] An Application Control policy has blocked this
file` while importing PyTorch — after working all day.

**Diagnosis:** Windows' Code Integrity event log
(`Microsoft-Windows-CodeIntegrity/Operational`) named the file:
`venv\Lib\site-packages\_rocm_sdk_libraries_custom\bin\rocrand.dll`, blocked
by **Smart App Control** (state: On) for not meeting its signing level.

**Fix:** retried — it loaded fine the second time (Smart App Control's
reputation check is not always consistent). If it keeps recurring, the
options are adding an exception or turning Smart App Control off (a
security trade-off — the user's call).

**Why this matters:** when a setup that worked suddenly fails with a
"blocked"/"access" error and nothing in the project changed, look at the
OS's security logs before debugging your own code.

---

## 23. INT8 NPU model counted zero bottles (2026-10-07, open — not blocking)

**Symptom:** Converted the same ONNX model twice for the RK3566 NPU. FP16
counted all 11 val photos exactly; INT8 counted **0** on every photo.

**Root cause:** the YOLOv8 export has one output tensor `(5, 33600)`
holding box coordinates (0-1280) *and* class scores (0-1) together. INT8
quantization gives a whole tensor one scale/step size — sized for values
up to ~1280, one step is ~5, so every score (0-1) rounds to 0 and nothing
passes the 0.5 threshold.

**Status:** using FP16 (0.64 s/photo, exact). If speed matters later,
export with boxes and scores as separate outputs (Rockchip model-zoo style)
so each gets its own scale, then re-quantize (~0.23 s/photo expected).

**Also hit along the way:** `rknn-toolkit2` pins `onnxoptimizer==0.3.8`,
which has no prebuilt aarch64 wheel — pip tries to compile it and fails.
Installing the toolkit with `--no-deps` and the other dependencies by hand
worked; conversion doesn't need onnxoptimizer for this model.

**Why this matters:** "the file converted" ≠ "the model works". Always
re-run the real end-to-end check (here: counts on the val photos) after
any conversion or compression step — this one failed silently with
plausible-looking output (zero detections, no error).

---

## Recurring patterns across these issues

A few lessons showed up more than once, worth remembering as general
debugging habits rather than one-off fixes:

1. **When something returns a plausible-but-wrong result, remove filters/
   thresholds entirely before assuming they're just miscalibrated** (#1).
   A confidence threshold of 0 still filtering everything out means the
   problem isn't the threshold.
2. **"No error" isn't the same as "correct."** Cameras that open without
   error (#7), settings with silent low defaults (#8, #17), tools that
   don't throw an exception (#5), and success messages that don't reflect
   where output really went (#16) can all still be wrong — verify actual
   output content, not just absence of errors.
3. **Version mismatches (too old *or* too new) cause unpredictable,
   hard-to-pin-down failures** (#3, #13, #15) — when a crash has no
   reproducible trigger, check the age/version gap between the tool and
   its runtime environment before debugging deeper.
4. **Hand-tuned numeric assumptions (pixel sizes, thresholds) are
   fragile to any change in input conditions** (#2, #14) — this is the
   core argument for preferring a trained model over hardcoded heuristics
   once the problem is complex enough.
5. **Prove which layer is broken before fixing any of them** (#20) —
   test "can it read the data?" separately from "does it understand the
   data?". Compare actual bytes against a known-good reference rather
   than trusting a tool's "verified" message from an earlier moment.
6. **File system operations (moves, imports) can have hidden
   dependencies** (#9, #10) — a folder lock or a broken import path won't
   always announce itself clearly; understand what depends on a path
   before changing it.
7. **Measure the actual goal, with the actual settings** (#18) — a
   summary metric (precision, mAP) can look perfect while the thing you
   really need (a correct count) is off by 50%.
8. **Documentation needs the same maintenance discipline as code** (#11)
   — a fact recorded as true when written can silently become false
   later without any single "breaking" event.
