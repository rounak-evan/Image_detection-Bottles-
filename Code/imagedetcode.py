"""
Bottle Counter
--------------
Detects and counts bottles in a photo using a pretrained YOLOv8 model.
No training required as "bottle" is already one of the 80 objects this
model learned from the COCO dataset.

Usage:
    python imagedetcode.py your_photo.jpg
"""

import sys
import cv2
from ultralytics import YOLO

model = YOLO('models/yolov8n.pt')

TARGET_CLASS = 'bottle'
CONFIDENCE_THRESHOLD = 0.4


def count_bottles(image_path, save_path='tests/outputs/result.jpg'):
    results = model(image_path, verbose=False)
    result = results[0]

    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(
            f"Could not open image at '{image_path}' — check the path is "
            "correct and the file exists."
        )
    count = 0

    for box in result.boxes:
        class_id = int(box.cls[0])
        class_name = model.names[class_id]
        confidence = float(box.conf[0])

        if class_name == TARGET_CLASS and confidence >= CONFIDENCE_THRESHOLD:
            count += 1
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 3)
            cv2.putText(image, f'{class_name} {confidence:.2f}', (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    cv2.putText(image, f'Count: {count}', (20, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 4)
    cv2.imwrite(save_path, image)

    return count


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python imagedetcode.py your_photo.jpg')
        sys.exit(1)

    photo_path = sys.argv[1]
    bottle_count = count_bottles(photo_path)
    print(f'Bottles found: {bottle_count}')
    print('Annotated image saved to tests/outputs/result.jpg')