"""
Add New Photos (extends the dataset with a second batch, without touching
the first batch's already-corrected labels)
--------------------------------------------------------------------------
prepare_dataset.py builds a dataset from scratch — great for the first
batch, but re-running it on the whole "data/dataset/" folder would
overwrite the 16 original photos' labels, throwing away all the manual
corrections done in makesense.ai. This script instead ADDS a second batch
(e.g. "data/Bottle Images (new)/") alongside what's already there:
  - Generates draft labels (via the same circle_counter.py logic) for ONLY
    the new photos.
  - Splits just the new photos into train/val.
  - Copies them into the existing dataset/images/{train,val} and
    dataset/labels/{train,val} folders, alongside the existing files —
    doesn't touch anything already there.

As with prepare_dataset.py, these are DRAFT labels — review/correct them
in makesense.ai before training, same as the first batch (see
LABELING_INSTRUCTIONS.md).

Usage:
    python add_new_photos.py
"""

import os
import shutil
import random

from prepare_dataset import (
    detect_circles_full_res,
    circles_to_yolo_lines,
    DATASET_FOLDER,
    IMAGE_EXTENSIONS,
    HOUGH_PARAMS,
)

NEW_SOURCE_FOLDER = 'data/Bottle Images (new)'
VAL_FRACTION = 0.2   # same ratio as the first batch, for consistency
RANDOM_SEED = 43      # different seed than prepare_dataset.py's 42 — just
                       # needs to be fixed/reproducible, not the same value

# This batch's photos are landscape-oriented with a wider field of view, so
# bottle caps appear smaller in pixels than the first batch's — the
# production HOUGH_PARAMS (tuned for the first batch) missed most caps here
# (several photos got 0 draft boxes). Widen just the radius range for THIS
# batch's draft-labeling pass only — doesn't touch circle_counter.py's
# actual tuned parameters used elsewhere.
NEW_BATCH_HOUGH_PARAMS = dict(HOUGH_PARAMS, minRadius=12, maxRadius=40)


def main():
    image_names = sorted(
        name for name in os.listdir(NEW_SOURCE_FOLDER)
        if name.lower().endswith(IMAGE_EXTENSIONS)
    )
    if not image_names:
        print(f"No images found in '{NEW_SOURCE_FOLDER}'.")
        return

    # Skip any photo that's already been added before (in case this script
    # gets run more than once) — checks by filename in either split.
    already_present = set()
    for split in ('train', 'val'):
        images_dir = os.path.join(DATASET_FOLDER, 'images', split)
        if os.path.isdir(images_dir):
            already_present.update(os.listdir(images_dir))
    image_names = [n for n in image_names if n not in already_present]
    if not image_names:
        print("All photos in this folder are already in the dataset — "
              "nothing new to add.")
        return

    random.Random(RANDOM_SEED).shuffle(image_names)
    val_count = max(1, round(len(image_names) * VAL_FRACTION))
    val_names = set(image_names[:val_count])
    train_names = [n for n in image_names if n not in val_names]

    for split, names in (('train', train_names), ('val', sorted(val_names))):
        images_dir = os.path.join(DATASET_FOLDER, 'images', split)
        labels_dir = os.path.join(DATASET_FOLDER, 'labels', split)
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(labels_dir, exist_ok=True)

        for name in names:
            src_path = os.path.join(NEW_SOURCE_FOLDER, name)
            dst_image_path = os.path.join(images_dir, name)
            shutil.copy2(src_path, dst_image_path)

            circles, width, height = detect_circles_full_res(
                src_path, hough_params=NEW_BATCH_HOUGH_PARAMS
            )
            lines = circles_to_yolo_lines(circles, width, height)

            label_name = os.path.splitext(name)[0] + '.txt'
            label_path = os.path.join(labels_dir, label_name)
            with open(label_path, 'w') as f:
                f.write('\n'.join(lines))

            print(f"[{split}] {name}: {len(lines)} draft box(es) written")

    print(f"\nAdded {len(image_names)} new photo(s): "
          f"{len(train_names)} train, {len(val_names)} val.")
    print("These are DRAFT labels — review/correct them in makesense.ai "
          "before training. See LABELING_INSTRUCTIONS.md.")


if __name__ == '__main__':
    main()
