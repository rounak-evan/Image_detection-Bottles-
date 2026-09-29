import cv2

for i in range(5):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"Camera index {i}: working, frame size {frame.shape}")
        cap.release()
    else:
        print(f"Camera index {i}: not available")