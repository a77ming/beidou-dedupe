import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def normalize_params(raw: dict) -> dict:
    if raw is None:
        return {}

    params = dict(raw)

    # Remove non-process_single params
    invalid_params = {
        "enable",
        "name",
        "category",
        "dimension",
        "canvas_size_preset",
        "preset_name",
        "canvas_size",
        "target_fps",
        "speed_curve",
        "enable_transition",
        "transition_type",
        "aspect_ratio",
    }

    for key in list(params.keys()):
        if key in invalid_params:
            params.pop(key, None)

    # Add enable flags when value exists
    def enable_if_value(value_key: str, enable_key: str):
        if value_key in params and params.get(value_key) is not None:
            params[enable_key] = True

    enable_if_value("brightness_value", "enable_brightness")
    enable_if_value("saturation_value", "enable_saturation")
    enable_if_value("hue_shift_value", "enable_hue_shift")
    enable_if_value("gamma_value", "enable_gamma")
    enable_if_value("gaussian_blur_value", "enable_gaussian_blur")
    enable_if_value("sharpen_strength", "enable_sharpen")
    enable_if_value("denoise_strength", "enable_denoise")
    enable_if_value("scratches_density", "enable_scratches")
    enable_if_value("dust_density", "enable_dust")
    enable_if_value("light_leak_intensity", "enable_light_leak")
    enable_if_value("edge_threshold", "enable_edge_detect")
    enable_if_value("cartoon_level", "enable_cartoon")
    enable_if_value("volume_gain_db", "enable_volume_adjust")

    if params.get("crop_params") is not None:
        params["enable_crop"] = True
    if params.get("perspective_params") is not None:
        params["enable_perspective"] = True
    if params.get("displacement_params") is not None:
        params["enable_displacement"] = True

    # Coerce output CRF to min 28 like auto_processor
    if "output_crf" in params:
        try:
            crf = int(params.get("output_crf") or 0)
            if crf < 28:
                params["output_crf"] = 28
        except Exception:
            params.pop("output_crf", None)

    return params


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--strategy-json", required=True)
    parser.add_argument("--processor-root", required=True)
    args = parser.parse_args()

    processor_root = args.processor_root
    if not os.path.isdir(processor_root):
        print(json.dumps({"error": f"Processor root not found: {processor_root}"}))
        sys.exit(1)

    sys.path.insert(0, os.path.abspath(processor_root))

    try:
        from core.video_processor import VideoProcessor
    except Exception as exc:
        print(json.dumps({"error": f"Failed to import VideoProcessor: {exc}"}))
        sys.exit(1)

    try:
        raw_params = json.loads(args.strategy_json)
    except Exception as exc:
        print(json.dumps({"error": f"Invalid strategy JSON: {exc}"}))
        sys.exit(1)

    params = normalize_params(raw_params)

    input_path = args.input
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)
    # MoviePy sometimes creates temp files using relative paths (TEMP_MPY_*).
    # Ensure the current working directory is writable.
    os.chdir(output_dir)

    video_name = Path(input_path).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"{video_name}_processed_{timestamp}.mp4")

    try:
        processor = VideoProcessor(input_path)
        result = processor.process_single(
            output_path=output_path,
            scale=None,
            speed=None,
            enable_snow=False,
            bg_color=None,
            bg_image_path=None,
            enable_video_progress_bar=False,
            video_border_width=0,
            corner_radius=0,
            enable_warmth=False,
            enable_contrast=False,
            enable_stickers=False,
            enable_blur_bar=False,
            enable_side_text=False,
            enable_gif_stickers=False,
            mirror_mode="off",
            rotation_mode="off",
            frame_drop_mode="off",
            film_grain_mode="off",
            **params
        )
        processor.close()
    except Exception as exc:
        print(json.dumps({"error": f"Processing failed: {exc}"}))
        sys.exit(1)

    print(json.dumps({
        "input_path": input_path,
        "output_path": output_path,
        "params": params,
        "result": result
    }))


if __name__ == "__main__":
    main()
