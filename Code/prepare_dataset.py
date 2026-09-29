"""
Prepare Dataset (auto-labeling step for custom YOLO training)
----------------------------------------------------------------
Why this exists:
Custom YOLO training needs, for every photo, a text file listing a bounding
box around every bottle in it. Drawing all of those by hand for hundreds of
bottles per photo would take forever. Instead, this script reuses
circle_counter.py (which already found real bottle caps correctly on
well-behaved photos like IMG_4723) to generate a STARTING set of labels
automatically, converting each detected circle into a YOLO-format bounding
box.

IMPORTANT — these labels are a draft, not ground truth:
circle_counter.py under-detects on angled photos and misses tilted bottles
entirely (see IMG_4730 / IMG_4743 from our testing). That means the labels
this script writes will have missing boxes and, occasionally, a false-
positive box on background texture. You MUST review and correct every
image's labels in a labeling tool before training — otherwise the model
just learns the circle detector's own mistakes. See LABELING_INSTRUCTIONS.md
(written alongside this dataset) for how to do that review.

YOLO label format (one .txt file per image, same name as the image):
    Each line = one bounding box:  class_id x_center y_center width height
    All four numbers are normalized to 0-1 (fraction of image width/height),
    not raw pixel coordinates. class_id 0 = "bottle" (our only class).

Usage:
    python prepare_dataset.py
"""

import os
import shutil
import random
import cv2
from circle_counter import HOUGH_PARAMS, PROCESS_WIDTH
import numpy as np

SOURCE_FOLDER = 'data/Bottle Images (Upright)'
DATASET_FOLDER = 'data/dataset'
VAL_FRACTION = 0.2  # ~20% of photos held out to check training progress
RANDOM_SEED = 42     # fixed seed so the train/val split is reproducible

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png')


def detect_circles_full_res(image_path, hough_params=None):
    """
    Same detection logic as circle_counter.py, but returns the raw list of
    circles (in ORIGINAL full-resolution pixel coordinates) instead of just
    a count — because training labels need real coordinates, not a picture
    with circles drawn on it.

    hough_params: optional override dict (same shape as circle_counter.py's
    HOUGH_PARAMS). Defaults to that module's tuned values if not given —
    useful when a different photo batch has differently-sized caps in frame
    (e.g. a wider-angle/landscape shot) that the original tuning misses.
    """
    if hough_params is None:
        hough_params = HOUGH_PARAMS

    image = cv2.imread(image_path)
    height, width = image.shape[:2]
    scale = PROCESS_WIDTH / width
    resized = cv2.resize(image, (PROCESS_WIDTH, int(height * scale)))

    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.medianBlur(gray, 5)
    circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, **hough_params)

    if circles is None:
        return [], width, height

    circles = np.round(circles[0, :]).astype(float)
    # Scale circle coordinates back up from the resized image to the
    # original photo's full resolution.
    circles /= scale
    return circles, width, height


def circles_to_yolo_lines(circles, image_width, image_height):
    """Convert (x, y, r) circles into YOLO-format label lines."""
    lines = []
    for (x, y, r) in circles:
        # Treat each circle as a square bounding box around it.
        box_w = box_h = 2 * r
        x_center_norm = x / image_width
        y_center_norm = y / image_height
        w_norm = box_w / image_width
        h_norm = box_h / image_height
        lines.append(f"0 {x_center_norm:.6f} {y_center_norm:.6f} "
                      f"{w_norm:.6f} {h_norm:.6f}")
    return lines


def main():
    image_names = sorted(
        name for name in os.listdir(SOURCE_FOLDER)
        if name.lower().endswith(IMAGE_EXTENSIONS)
    )
    if not image_names:
        print(f"No images found in '{SOURCE_FOLDER}'.")
        return

    # Shuffle deterministically, then split into train/val.
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
            src_path = os.path.join(SOURCE_FOLDER, name)
            dst_image_path = os.path.join(images_dir, name)
            shutil.copy2(src_path, dst_image_path)

            circles, width, height = detect_circles_full_res(src_path)
            lines = circles_to_yolo_lines(circles, width, height)

            label_name = os.path.splitext(name)[0] + '.txt'
            label_path = os.path.join(labels_dir, label_name)
            with open(label_path, 'w') as f:
                f.write('\n'.join(lines))

            print(f"[{split}] {name}: {len(lines)} draft box(es) written")

    # data.yaml tells YOLO where the images/labels live and what the
    # classes are. Paths are relative to this file's location.
    data_yaml_path = os.path.join(DATASET_FOLDER, 'data.yaml')
    with open(data_yaml_path, 'w') as f:
        f.write(
            "train: images/train\n"
            "val: images/val\n"
            "nc: 1\n"
            "names: ['bottle']\n"
        )

    print(f"\nDataset written to '{DATASET_FOLDER}/'.")
    print(f"  train: {len(train_names)} photos, val: {len(val_names)} photos")
    print("\nNEXT STEP (required): review and correct the draft labels "
          "before training. See LABELING_INSTRUCTIONS.md.")


if __name__ == '__main__':
    main()
