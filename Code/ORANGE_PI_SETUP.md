# Orange Pi 3B bring-up

Getting the board running and checking each part, one at a time. **Read
`ClaudeContext/Projectsummary.md` for project context** — this file only
covers the board itself.

The rule for this whole stage: **change one thing at a time.** If the board,
the custom LCD, the touch panel and the camera all go in together and
nothing shows up, there is no way to tell which part is at fault.

## Progress (as of 2026-10-06)

| Step | Status |
|---|---|
| 1-2. Download + flash image | ✅ Done (checksum verified) |
| 3. First boot | ✅ Done — after fixing a GPT header bug (see below / ChallengesLog #20) |
| 4. Health check | ✅ Kernel 5.10.160, 3.8 GB RAM, **NPU driver RKNPU v0.9.6**, ~58 °C idle |
| 5. SSH | ✅ `ssh orangepi@192.168.1.115`, key login from the home PC |
| 6a. Camera | ✅ Works, full 3264x2448, focus 150 locked manually |
| 6b. Speaker | ⏳ Not yet |
| 6c-6d. Custom LCD + touch | ⏳ Hardware not here yet |
| 7. Model on the NPU | ✅ 2026-10-07 — FP16 model exact on all val photos, ~0.64 s each (Projectsummary "Model on the NPU") |

**How it currently boots (since 2026-10-07): from the eMMC module alone.**
The system was first brought up on SD card + USB pen drive (see #20 in
the ChallengesLog), then copied onto the eMMC with `pi/install_to_emmc.sh`.
**Keep the old SD card out of the Pi** — it still holds the old system
and the bootloader may try it first. The board's 16 MB SPI flash is
erased (it held a previous project's bootloader). Default password
`orangepi` is unchanged for now. The Ubuntu 24.04 upgrade prompt is
disabled — don't upgrade (RKNN needs 22.04).

**To reinstall onto the eMMC** (e.g. after re-flashing): boot a working
system from SD/USB with the eMMC attached, copy `pi/install_to_emmc.sh`
over, run `sudo bash install_to_emmc.sh` (it checks the target is really
the eMMC and not the running disk, then erases it), shut down, remove
SD/USB, power on.

## 0. What you need on the desk

- Orange Pi 3B (4GB) + **5V / 3A USB-C** power supply (a weak phone charger
  causes random reboots that look like software bugs)
- **microSD card, 32GB or bigger, Class 10 / A1 or A2** + a card reader for
  the PC (or the eMMC module, if you have one — see step 2)
- **A normal HDMI monitor or TV for first boot** — not the custom 10.1"
  LCD yet. First prove the board works on a screen known to be good.
- USB keyboard + mouse
- Network: Ethernet cable to the router (simplest), or Wi-Fi
- Heatsink on the main chip, if you have it

## 1. Download the OS image (on the Windows PC)

Download **`Orangepi3b_1.0.8_ubuntu_jammy_desktop_xfce_linux5.10.160.7z`**
(Ubuntu 22.04 "Jammy", desktop, kernel 5.10) — direct Google Drive link:
https://drive.google.com/file/d/1MkDtsA5fj8KHFZPqwKGoBg0Q7aJK629d/view

Note: `https://www.orangepi.org` refuses connections (checked 2026-10-06),
but plain **`http://www.orangepi.org`** works — the Orange Pi 3B page
there links to Google Drive folders: Ubuntu images
https://drive.google.com/drive/folders/1hWsiaEmjiRFjGMrOw6Z3UoyxGz97Tgve ,
user manual
https://drive.google.com/drive/folders/1MhPt8AREyEo9bwanhUdbQiUne60AoqqJ .
Don't pick the `linux6.6.0-rc5` versions (a pre-release test kernel —
Rockchip's NPU driver is built for 5.10, so it's most likely missing there) or `focal` (Ubuntu 20.04, older).

Why this one specifically:
- **Official Orange Pi image, kernel 5.10**: Rockchip's NPU driver (needed
  to run our model on the AI chip) ships in Rockchip's own 5.10 kernel.
  Community images like Armbian often use the newer "mainline" Linux
  kernel, which doesn't include the driver RKNN needs.
- **Ubuntu 22.04**: the version Rockchip's RKNN tools officially support.
- **Desktop, not server**: our touchscreen app needs a graphical display.

The download is usually a `.7z` or `.zip` — extract it with 7-Zip to get
the `.img` file.

## 2. Flash it to the microSD card

1. Install the **latest balenaEtcher** (older versions are known to produce
   cards that boot-loop on Orange Pi).
2. Flash from file → pick the `.img` → pick the microSD card → Flash.
   **Double-check the target drive** — Etcher erases whatever you select.
3. Eject the card safely.

(eMMC: if you have the eMMC module, still start from microSD — it's easier
to re-flash if something goes wrong. Moving to eMMC can come later.)

## 2b. No screen yet? Run it "headless" (current setup, 2026-10-06)

Right now there's no LCD or spare monitor — only the Pi and the camera.
That's fine: control the Pi from the PC over the network instead.

- **Don't plug the Pi's HDMI into the PC** — a PC's HDMI port only sends a
  picture out, it can't display one coming in.
- Connect the Pi to the **router with an Ethernet cable** (Wi-Fi setup
  normally needs a screen; wired needs nothing).
- Power on, wait ~2 minutes for first boot.
- Find its IP address: router admin page → connected devices (look for
  `orangepi3b` or similar), or ask Claude to scan the network from the PC.
- From PowerShell on the PC: `ssh orangepi@<IP>` — default password
  `orangepi`. Official Orange Pi images usually have SSH on by default.
  Then run `passwd` to change it.
- Then skip to **step 4** (health check) — step 3 is for when a screen is
  connected.

Fallback if no router port is free: a cable straight from PC to Pi, using
Windows "Internet Connection Sharing" — more fiddly, only if needed.

### If boot stops at `(initramfs)` with "UUID=... does not exist"

This is what happened on 2026-10-06 (full story: `ClaudeContext/ChallengesLog.md`
#20). Cause: on first boot, the Pi rewrote the drive's GPT header to fit
the larger disk but left the partition-entry pointer aimed at an empty
spot (LBA 2016 instead of 2), so Linux rejects the whole table. **The fix
is one sector on the drive**: put the pointer back to 2 and recompute the
header checksum — done from the Windows PC with an admin script,
`tools/fix_gpt_entry_pointer.ps1` (run in an **administrator** PowerShell:
`.\tools\fix_gpt_entry_pointer.ps1 -Disk <number from Get-Disk> -Log fix.log`).
It refuses anything that isn't a USB drive under 200 GB, checks the valid
entries really are at LBA 2, and saves the original sector next to the log
before writing. Works for SD cards in a USB card reader too.
Quick test at the `(initramfs)` prompt: `cat /proc/partitions` shows the
drive but no `p1`/`p2` (or `sda1`/`sda2`) entries.

### If the Pi never shows up on the network

Connect a screen once (HDMI + keyboard, HDMI plugged in **before** power)
and look. If it stops at a `(initramfs)` prompt with
`ALERT! UUID=... does not exist`, the OS didn't finish booting — it's not
a network problem — see the section above.

## 3. First boot (with a screen)

1. Card into the Pi. Connect HDMI monitor, keyboard, mouse, Ethernet.
2. **Plug in power last.** First boot can take 1-2 minutes.
3. Log in. Orange Pi's default user is `orangepi`, password `orangepi`
   (check the manual for your image if that fails).
4. Open a terminal and change the password straight away:
   ```
   passwd
   ```

## 4. Basic health check

Run these and note the output (paste it back to Claude):

```
uname -a                                  # kernel version — expect 5.10.x
free -h                                   # RAM — expect ~4GB total (3.7-3.8G shown)
df -h /                                   # disk space on the card
sudo cat /sys/kernel/debug/rknpu/version  # NPU driver version — THE important one
cat /sys/class/thermal/thermal_zone0/temp # chip temperature in thousandths of °C
```

**The NPU line is the one that matters most.** It should print something
like `RKNPU driver: v0.9.x`. If it errors instead, the AI chip isn't usable
with this image yet — stop there and ask, because everything later depends
on it. (Don't worry if there's no `/dev/rknpu` file — on this kernel the
NPU shows up as a graphics-style device instead, so that's normal.)

Then update the system:

```
sudo apt update
sudo apt upgrade -y
```

## 5. Turn on SSH, so the PC can work on the Pi

SSH lets you (and Claude, from the PC) run commands on the Pi over the
network — no need to keep typing at the Pi's own keyboard.

```
sudo systemctl enable --now ssh   # start SSH now and on every boot
hostname -I                        # prints the Pi's IP address, e.g. 192.168.1.42
```

From PowerShell on the Windows PC:

```
ssh orangepi@<the IP address>
```

If that logs you in, tell Claude the IP — from then on Claude can run the
checks below directly.

## 6. Peripheral checks — one at a time

### 6a. Camera (Arducam)
```
lsusb                        # should list an Arducam / USB camera
v4l2-ctl --list-devices      # shows its /dev/videoN number
```
(`v4l2-ctl` comes from `sudo apt install v4l-utils` if missing.) Then
capture a frame at 2592x1944 with a short Python script — same gotchas as
on the laptop: throw away warm-up frames, set the resolution explicitly.

**Results (2026-10-06):**
- Shows up as USB `0c45:6366` "Microdia Webcam Vitade AF" → `/dev/video0`.
- On Linux it offers **3264x2448 (full 8 MP) at 15 fps in MJPG** — more
  than Windows allowed (2592x1944).
- OpenCV: `sudo apt install python3-opencv` (gives 4.5.4). Working capture
  recipe: `cv2.VideoCapture(0, cv2.CAP_V4L2)`, set FOURCC `MJPG`, then
  width 3264 / height 2448, read frames for ~3 s to warm up, then keep one.
- **Focus:** autofocus is off by default. Manual focus is
  `v4l2-ctl -d /dev/video0 -c focus_auto=0 -c focus_absolute=150`
  (range 1-1023, lower = farther). 150 was clearly sharpest at the test
  height — but only measure with the camera resting still; hand-held
  sweeps give random answers (ChallengesLog #21). Re-sweep at the final
  mount height.
- Other controls available: exposure (auto), white balance (auto),
  sharpness 0-6 (default 3). `v4l2-ctl -d /dev/video0 --list-ctrls`.

### 6b. Speaker
```
aplay -l                     # lists sound outputs (headphone jack, HDMI, USB)
speaker-test -t wav -c 2     # plays test sound; Ctrl+C to stop
```

### 6c. Custom LCD (only after 6a and 6b work)
1. Power off the Pi. Swap the monitor's HDMI cable to the LCD driver board
   (HC10MST).
2. Connect the driver board's **own separate 5V supply** — confirm the
   physical connector (micro-USB vs. 2 bare pins) before plugging in.
3. Power the LCD first, then the Pi.
4. If it's blank or the picture is cropped/stretched, the board may be
   sending a resolution the panel doesn't like — likely native 1280x800.

### 6d. Touch panel
1. Connect the touch controller's USB to the Pi.
2. `lsusb` should list it (ILI2511 / ILITEK).
3. Tap the screen — the mouse pointer should follow your finger. If the
   pointer moves but in the wrong place/direction, the touch needs
   calibrating to the screen's rotation — fixable in software.

## 7. Then: the model on the NPU

The model has to be converted to Rockchip's RKNN format **on the PC**
(the converter needs an x86 Linux machine — WSL2 Ubuntu 22.04 on the home
PC), then copied to the Pi and run with `rknn-toolkit-lite2`. Claude will
handle that part once steps 4-5 pass — the first thing to measure there is
how many seconds one count takes at our 1280 image size.
