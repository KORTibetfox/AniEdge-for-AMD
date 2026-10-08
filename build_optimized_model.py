"""Build RGB8 I/O Real-CUGAN graphs; optional FP16 convolution conversion.

Build-only dependencies: onnx, onnxconverter-common, protobuf, ml_dtypes.
No training or source-weight modification beyond FP16 conversion is performed.
"""
from pathlib import Path
import argparse
import copy


def convert(source, destination, fp16=False):
    import numpy as np
    import onnx
    from onnx import helper as h, TensorProto as T, numpy_helper
    model = onnx.load(str(source))
    if fp16:
        from onnxconverter_common import float16
        # Legacy model uses dynamic reflection padding. ONNX's offline shape inference
        # invents conflicting concrete dimensions here; DirectML resolves real shapes.
        model = float16.convert_float_to_float16(model, keep_io_types=False,
                                                disable_shape_infer=True, op_block_list=[])
    input_name = model.graph.input[0].name
    output_name = model.graph.output[0].name
    dtype = T.FLOAT16 if fp16 else T.FLOAT
    prefix = "rx_sr_"
    scalars = {"normalize": 0.7 / 255.0, "offset": 0.15, "denormalize": 255.0 / 0.7,
               "zero": 0.0, "max": 255.0}
    for name, value in scalars.items():
        model.graph.initializer.append(numpy_helper.from_array(np.array(value, dtype=np.float32), prefix + name))
    pre = [h.make_node("Cast", ["rgb8"], [prefix + "float_hwc"], to=T.FLOAT),
           h.make_node("Transpose", [prefix + "float_hwc"], [prefix + "float_chw"], perm=[0, 3, 1, 2]),
           h.make_node("Mul", [prefix + "float_chw", prefix + "normalize"], [prefix + "scaled"]),
           h.make_node("Add", [prefix + "scaled", prefix + "offset"], [prefix + "normalized"]),
           h.make_node("Cast", [prefix + "normalized"], [input_name], to=dtype)]
    post = [h.make_node("Cast", [output_name], [prefix + "output_float"], to=T.FLOAT),
            h.make_node("Sub", [prefix + "output_float", prefix + "offset"], [prefix + "output_centered"]),
            h.make_node("Mul", [prefix + "output_centered", prefix + "denormalize"], [prefix + "output_scaled"]),
            h.make_node("Clip", [prefix + "output_scaled", prefix + "zero", prefix + "max"], [prefix + "clipped"]),
            h.make_node("Cast", [prefix + "clipped"], [prefix + "uint8_chw"], to=T.UINT8),
            h.make_node("Transpose", [prefix + "uint8_chw"], ["restored_rgb8"], perm=[0, 2, 3, 1])]
    nodes = list(model.graph.node)
    model.graph.ClearField("node")
    model.graph.node.extend(pre + nodes + post)
    model.graph.value_info.extend([copy.deepcopy(model.graph.input[0]), copy.deepcopy(model.graph.output[0])])
    model.graph.ClearField("input")
    model.graph.ClearField("output")
    model.graph.input.append(h.make_tensor_value_info("rgb8", T.UINT8, [1, "height", "width", 3]))
    model.graph.output.append(h.make_tensor_value_info("restored_rgb8", T.UINT8, [1, "output_height", "output_width", 3]))
    h.set_model_props(model, {"optimization": "RGB8 I/O; GPU Pro normalization; " + ("FP16" if fp16 else "FP32"),
                              "source_model": source.name,
                              "validated_target": "AMD Radeon RX 9070 XT / DirectML",
                              "trained": "false"})
    onnx.checker.check_model(model)
    onnx.save(model, str(destination))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--fp16", action="store_true")
    args = parser.parse_args()
    convert(args.source, args.destination, args.fp16)
