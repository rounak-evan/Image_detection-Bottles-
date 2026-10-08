# Laptop quick-start: taking Arducam photos

For using this project folder on the **Windows laptop** (no GPU) to collect
real crate photos with the Arducam. Full project context:
`ClaudeContext/Projectsummary.md` (read "Where things stand" first).

## 1. Copy the project onto the laptop

Copy the whole `ML_Project` folder from the pen drive onto the laptop's
disk (e.g. `C:\ML_Project`). Working straight off the pen drive also works,
but is slower.

**Don't use the `Code\venv` folder on the laptop.** It's the Python setup
for the home PC (tied to that PC's folders and its AMD GPU) and won't run
here. Use the laptop's own Python instead — the one used before
(see step 2).

## 2. Check the laptop's Python has what it needs

Open a terminal in the `Code` folder and run:

```
python -c "import cv2; print(cv2.__version__)"
```

If that prints a version number, you're set for taking photos. If it says
`No module named 'cv2'`, install it:

```
pip install opencv-python
```

(Only needed if you also want to run the model on the laptop: `pip install
ultralytics`. Not needed just to take photos — counting can happen on the
home PC or the Pi.)

## 3. Take the photos

1. Plug the Arducam into the laptop.
2. Rest the camera **steady, pointing straight down** at a crate of
   bottles, at roughly the height it will be mounted. Not hand-held —
   hand-held shots vary too much (ChallengesLog #21).
3. From the `Code` folder:
   ```
   python capture_photos.py
   ```
   A live preview opens. Click on the preview window, then:
   - **SPACE** = save a photo
   - **Q** = quit
4. If the terminal shows a WARNING about resolution, the wrong camera
   opened — quit and run `python capture_photos.py 0` instead (camera 1 is
   the Arducam on the laptop; camera 0 is the laptop's own IR camera).

Photos are saved to `Code/data/Bottle Images (arducam)/` at 2592x1944
(the most Windows allows from this camera).

### What makes a good set of photos
- 30-50 photos, different crates: sparse, half-full, full, packed.
- **Rearrange the bottles between shots** — the same crate photographed
  several times in a row teaches the model less and makes tests look
  better than they really are.
- The lighting the real site will have.
- If you can, write down the hand count of each crate as you go.

## 4. Bring them back

Copy `Code/data/Bottle Images (arducam)/` back onto the pen drive and
into the same place on the home PC. Then the next steps (in Claude) are:
run the trained model on them to see how it does on real Arducam photos,
label them in makesense.ai (drafts from the model), and retrain if needed.
