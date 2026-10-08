# Run an RKNN bottle model on the NPU over the val photos; compare counts with labels.
import sys, time, glob, os
import cv2, numpy as np
from rknnlite.api import RKNNLite

MODEL = sys.argv[1]
IMG = 1280
CONF, IOU = 0.5, 0.4   # same production settings as tests/check_model.py

def letterbox(img):
    # Same as Ultralytics: shrink so the long side is 1280, pad the rest with grey (114).
    h, w = img.shape[:2]
    s = IMG / max(h, w)
    nh, nw = round(h * s), round(w * s)
    out = np.full((IMG, IMG, 3), 114, np.uint8)
    top, left = (IMG - nh) // 2, (IMG - nw) // 2
    out[top:top + nh, left:left + nw] = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    return out

def count(pred):
    # pred: (5, N) rows = centre x, centre y, width, height, bottle score
    p = pred.reshape(5, -1).T
    p = p[p[:, 4] > CONF]
    if len(p) == 0:
        return 0
    boxes = [[float(x - w / 2), float(y - h / 2), float(w), float(h)] for x, y, w, h, _ in p]
    keep = cv2.dnn.NMSBoxes(boxes, p[:, 4].astype(float).tolist(), CONF, IOU)
    return len(keep)

rk = RKNNLite(verbose=False)
assert rk.load_rknn(MODEL) == 0
assert rk.init_runtime() == 0
total_err, times = 0, []
for path in sorted(glob.glob('val/*.jpeg')):
    name = os.path.splitext(os.path.basename(path))[0]
    true = sum(1 for l in open('val_labels/%s.txt' % name) if l.strip())
    img = cv2.cvtColor(letterbox(cv2.imread(path)), cv2.COLOR_BGR2RGB)
    t = time.time()
    out = rk.inference(inputs=[img[None]], data_format=['nhwc'])
    times.append(time.time() - t)
    n = count(out[0])
    total_err += abs(n - true)
    print('%-10s true %4d  npu %4d  diff %+4d  %.2fs' % (name, true, n, n - true, times[-1]))
print('TOTAL miscounted %d / 1297 ; median NPU time %.2fs (first run %.2fs)' % (total_err, sorted(times)[len(times)//2], times[0]))
rk.release()
