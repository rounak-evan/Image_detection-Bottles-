"""
Batch Test
----------
Runs the bottle-counting function (from imagedetcode.py) on every photo in a
folder, instead of calling it one photo at a time. Useful for checking how
CONFIDENCE_THRESHOLD performs across many real photos at once.

Usage (run from the Code/ folder, not from inside tests/):
    python tests/batch_test.py "data/Bottle Images (Upright)"

For each photo found, this:
  - Prints the detected count to the terminal.
  - Saves an annotated copy (green boxes + count) into tests/outputs/batch_results/,
    using the same filename, so you can open each one and visually check it
    against the printed number.
"""

import sys
import os

# This script lives in tests/, but circle_counter.py lives one folder up in
# Code/ — add that parent folder to Python's search path so the import
# below can still find it.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Reuse the count_bottles_topdown() function we already built and verified,
# instead of duplicating detection logic here. (The original YOLO-based
# count_bottles() from imagedetcode.py doesn't work for these top-down crate
# photos — see circle_counter.py's docstring for why.)
from circle_counter import count_bottles_topdown as count_bottles

# Common photo file extensions to look for. Anything else in the folder
# (e.g. a "results" subfolder, a README) is ignored.
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png')


def batch_test(folder_path):
    # os.listdir() gives every file/folder name inside folder_path, but not
    # full paths — we build those ourselves with os.path.join below.
    filenames = sorted(os.listdir(folder_path))
    image_filenames = [
        name for name in filenames
        if name.lower().endswith(IMAGE_EXTENSIONS)
    ]

    if not image_filenames:
        print(f"No image files found in '{folder_path}'.")
        return

    # Save annotated results into tests/outputs/batch_results/ (relative to
    # the Code/ folder), so the originals stay untouched and test outputs
    # stay grouped together instead of cluttering the source photo folder.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    results_folder = os.path.join(script_dir, 'outputs', 'batch_results')
    os.makedirs(results_folder, exist_ok=True)

    print(f"Found {len(image_filenames)} photo(s) in '{folder_path}'.\n")

    total = 0
    for name in image_filenames:
        image_path = os.path.join(folder_path, name)
        save_path = os.path.join(results_folder, name)

        count = count_bottles(image_path, save_path=save_path)
        total += count
        print(f"{name}: {count} bottle(s) detected")

    print(f"\nTotal across all photos: {total}")
    print(f"Annotated images saved to: {results_folder}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python tests/batch_test.py "folder_name"')
        sys.exit(1)

    batch_test(sys.argv[1])
