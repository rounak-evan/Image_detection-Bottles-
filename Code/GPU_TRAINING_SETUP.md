# Setting up GPU training on the home PC (AMD RX 9070 XT)

This is for the **home PC** (AMD Radeon RX 9070 XT, 16GB VRAM, 32GB DDR5
RAM) — not this Windows laptop, which has no GPU and was running `train.py`
on CPU only (very slow: potentially several hours for this dataset).

**Read `ClaudeContext/Projectsummary.md` first** for full project context —
this file only covers the GPU/training environment setup itself.

**Status (2026-10-03): this setup works.** Training ran successfully on the
9070 XT with Python 3.12.10, torch 2.9.1+rocm7.2.1, Ultralytics 8.4.171 —
the full run took ~2.3 minutes. One extra fix was needed beyond the steps
below: see "MIOpen crash during training" at the end.

The venv lives at `Code/venv/` — run scripts with
`.\venv\Scripts\python.exe <script>` from the `Code/` folder.

**Known hiccup (2026-10-06):** Windows **Smart App Control** sometimes
blocks one ROCm library (`rocrand.dll`) with "An Application Control
policy has blocked this file". Retrying usually works — see
`ClaudeContext/ChallengesLog.md` #22.

## Why this is more involved than a normal `pip install torch`

NVIDIA GPUs use CUDA, which PyTorch supports out of the box via a simple
pip install. AMD GPUs use a different system called **ROCm**. ROCm's
primary, most mature support target is Linux — Windows support is newer
and less battle-tested. As of early 2026, AMD ships an official
**"PyTorch on Windows" edition** that explicitly supports the RX 9070 XT,
which is the path below. It's the officially documented route, but it's a
fairly new release — expect a real (not zero) chance of hitting friction
along the way. If Windows setup fails despite following this closely, the
fallback is running Linux (dual-boot or a Linux install) where ROCm is
much more mature.

## 1. Requirements (check these before installing anything)

- **Windows 11** — required; ROCm-on-Windows for consumer GPUs does not
  support Windows 10.
- **Python 3.12** — specifically this version. The prebuilt wheels below
  are built for Python 3.12; other versions (e.g. 3.13, 3.14) won't have
  matching wheels. Download from https://www.python.org/downloads/ if not
  already installed. You can have multiple Python versions installed side
  by side — just make sure the virtual environment in step 3 is created
  with 3.12 specifically.
- **AMD graphics driver 26.2.2 or newer** — update via AMD Adrenalin
  software if not already current.

## 2. Install/update the AMD driver

Open AMD Software (Adrenalin), check for updates, confirm you're on
26.2.2 or newer before proceeding. A mismatched/older driver is a common
cause of ROCm failing to detect the GPU even when everything else is
installed correctly.

## 3. Create a Python 3.12 virtual environment

Isolates this project's packages from anything else on the system, and
guarantees the right Python version is used:

```
py -3.12 -m venv venv
venv\Scripts\activate
```

(If `py -3.12` isn't recognized, Python 3.12 either isn't installed or
isn't on PATH — revisit step 1.)

## 4. Install PyTorch with ROCm support

**Do this BEFORE installing `ultralytics`** — see the warning in step 5
for why the order matters.

```
pip install --no-cache-dir ^
  https://repo.radeon.com/rocm/windows/rocm-rel-7.2.1/rocm_sdk_core-7.2.1-py3-none-win_amd64.whl ^
  https://repo.radeon.com/rocm/windows/rocm-rel-7.2.1/rocm_sdk_devel-7.2.1-py3-none-win_amd64.whl ^
  https://repo.radeon.com/rocm/windows/rocm-rel-7.2.1/rocm_sdk_libraries_custom-7.2.1-py3-none-win_amd64.whl ^
  https://repo.radeon.com/rocm/windows/rocm-rel-7.2.1/rocm-7.2.1.tar.gz
```

This installs ROCm 7.2.1 plus PyTorch 2.9.1 (built against ROCm) in one
go. The `^` line continuations are PowerShell/cmd syntax — if running this
in a different shell, join it into one line instead.

## 5. Verify PyTorch sees the GPU — do this before moving on

```
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no GPU detected')"
```

Should print `True` and `AMD Radeon RX 9070 XT` (ROCm presents itself
through PyTorch's CUDA-compatible API, so `torch.cuda...` is correct here
even though this is an AMD card, not an NVIDIA one — that's not a typo).

**If this prints `False`**, stop and fix it before installing anything
else — don't proceed to training on what would silently be CPU-only.
Recheck the driver version and that the venv is really using Python 3.12
(`python --version` inside the activated venv).

## 6. Install the rest of the project's dependencies

```
pip install ultralytics opencv-python
```

**Important — check afterward that `ultralytics` didn't silently replace
your GPU-enabled PyTorch.** `ultralytics` lists `torch` as a dependency
and pip may pull in a plain CPU-only build over the top of the ROCm one
just installed. Re-run the verification command from step 5 after this
install. If it now prints `False`, re-run the step 4 install command again
to reinstall the ROCm build on top.

## 7. Copy the project files over

Copy the whole `Code/` folder from the laptop to this PC (USB drive,
cloud sync, network share — whichever's convenient). Every script in this
project uses relative paths only (`models/yolov8n.pt`,
`data/dataset/data.yaml`, etc.) — nothing is hardcoded to the laptop's
file layout, so the folder works unchanged wherever it's placed, as long
as its internal structure stays intact (see the "Folder structure" section
in `Projectsummary.md`).

## 8. Run training

From inside the copied `Code/` folder, with the venv activated:

```
python train.py
```

Watch the first few lines of output — Ultralytics prints which device
it's training on. Confirm it says something GPU-related, not `cpu`,
before letting it run for a while. (On the working setup it prints
`CUDA:0 (AMD Radeon RX 9070 XT, 16304MiB)`.)

Results land in `models/runs/bottle_detector/` — the trained model is
`weights/best.pt`. Re-running `train.py` overwrites that same folder.
To keep a copy of the console output, run
`python train.py > train_log.txt` instead.

## MIOpen crash during training (hit and fixed 2026-10-03)

Even with step 5 passing, training crashed with
`miopenStatusUnknownError`. MIOpen is AMD's optimized neural-network
library, and it has a bug on this card with this ROCm release. **Already
fixed in `train.py`** with this line near the top:

```python
torch.backends.cudnn.enabled = False
```

On ROCm, PyTorch's "cudnn" switch controls MIOpen, so this turns MIOpen
off and PyTorch uses its own GPU code instead — still on the GPU, still
fast. Any *other* script that trains on this PC (or runs heavy GPU work
and hits the same error) needs the same line.

## Known issue to be aware of

At least one user has reported being unable to get PyTorch to detect a
9070 XT on Windows 11 despite following AMD's official docs closely (see
the GitHub issue linked below). If step 5 keeps printing `False` after
double-checking driver version, Python version, and reinstall order, this
may be a known rough edge rather than a setup mistake — worth searching
that issue / ROCm's GitHub for recent workarounds before spending too long
on it.

## Sources

- [Windows support matrices by ROCm version — AMD ROCm docs](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/windows/windows_compatibility.html)
- [Install PyTorch via PIP — AMD ROCm docs](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/install/installrad/windows/install-pytorch.html)
- [AMD Software: PyTorch on Windows Edition 7.2.1 Release Notes](https://www.amd.com/en/resources/support-articles/release-notes/RN-AMDGPU-WINDOWS-PYTORCH-7-2-1.html)
- [Issue: can't use PyTorch on Windows 11 on 9070 XT — ROCm/TheRock #5113](https://github.com/ROCm/TheRock/issues/5113)
