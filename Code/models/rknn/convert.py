# Convert best.onnx into RKNN models for the RK3566 NPU.
import sys
from rknn.api import RKNN

def convert(quantize, out_path):
    rknn = RKNN(verbose=False)
    # The model expects pixel values 0-1; the NPU gets 0-255, so divide by 255 on the chip.
    rknn.config(mean_values=[[0, 0, 0]], std_values=[[255, 255, 255]], target_platform='rk3566')
    assert rknn.load_onnx(model='best.onnx') == 0, 'load_onnx failed'
    assert rknn.build(do_quantization=quantize, dataset='dataset.txt') == 0, 'build failed'
    assert rknn.export_rknn(out_path) == 0, 'export failed'
    rknn.release()
    print('OK', out_path)

convert(False, 'best_fp16.rknn')
convert(True, 'best_int8.rknn')
