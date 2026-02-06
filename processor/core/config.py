"""
Configuration module for short video repurposing tool.
Contains all configurable parameters for video processing.
"""

import os
import random
import logging
import json
import re
from typing import Tuple, List, Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# ============== Canvas Settings ==============
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920

# ============== Picture-in-Picture Settings ==============
SCALE_MIN = 0.80
SCALE_MAX = 0.90

# ============== Speed Settings ==============
SPEED_MIN = 1.1
SPEED_MAX = 1.3
DEFAULT_SPEED = 1.2

# ============== Rotation Settings ==============
ROTATION_MIN_DEGREES = 1.0
ROTATION_MAX_DEGREES = 2.0

# ============== Frame Dropping Settings ==============
FRAME_DROP_INTERVAL_MIN = 2.0  # Minimum seconds between drops
FRAME_DROP_INTERVAL_MAX = 4.0  # Maximum seconds between drops
FRAME_DROP_COUNT_MIN = 1  # Min frames to drop per interval
FRAME_DROP_COUNT_MAX = 2  # Max frames to drop per interval

# ============== Film Grain Settings ==============
FILM_GRAIN_INTENSITY_MIN = 0.03
FILM_GRAIN_INTENSITY_MAX = 0.05
FILM_GRAIN_COLOR_OPTIONS = ["gray", "white", "colored"]


# ============== Background Settings ==============
BG_COLORS = [
    (240, 200, 220),  # Pink
    (200, 220, 255),  # Blue
    (255, 240, 200),  # Orange
    (220, 255, 220),  # Green
    (255, 220, 220),  # Red
]

BG_MODE_SOLID = "solid"
BG_MODE_IMAGE = "image"
BG_MODE_GRADIENT = "gradient"
BG_MODE_BLUR = "blur"
SUPPORTED_BG_MODES = [BG_MODE_SOLID, BG_MODE_IMAGE, BG_MODE_GRADIENT, BG_MODE_BLUR]

# Background image folder
BG_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bg")

# ============== Snow Effect Settings ==============
SNOW_PARTICLE_COUNT_MIN = 50
SNOW_PARTICLE_COUNT_MAX = 150
SNOW_SIZE_MIN = 2
SNOW_SIZE_MAX = 5
SNOW_SPEED_MIN = 1
SNOW_SPEED_MAX = 3

# ============== Text Overlay Settings ==============
TEXT_CONTENT = "Watch full video in comments"
TEXT_COLOR = (255, 140, 0)  # Orange
TEXT_STROKE_COLOR = (255, 255, 255)
TEXT_STROKE_WIDTH = 2
TEXT_FONT_SIZE = 48
TEXT_POSITION = "top"  # top, center, bottom

# ============== Output Settings ==============
OUTPUT_FORMAT = "mp4"
VIDEO_CODEC = "libx264"
AUDIO_CODEC = "aac"
BITRATE = "8000k"
X264_PRESET = "veryfast"

# ============== Batch Processing ==============
DEFAULT_BATCH_COUNT = 3
MIN_BATCH_COUNT = 1
MAX_BATCH_COUNT = 10

# ============== Dynamic Zoom Settings ==============
DYNAMIC_ZOOM_MIN_KEYPOINTS = 2
DYNAMIC_ZOOM_MAX_KEYPOINTS = 5
DYNAMIC_ZOOM_MIN_INTERVAL = 2.0  # Minimum seconds between keypoints
DYNAMIC_ZOOM_MAX_INTERVAL = 5.0  # Maximum seconds between keypoints

# ============== Mirror Settings ==============
MIRROR_MODE_OFF = "off"
MIRROR_MODE_ON = "on"
MIRROR_MODE_RANDOM = "random"
MIRROR_MODES = [MIRROR_MODE_OFF, MIRROR_MODE_ON, MIRROR_MODE_RANDOM]

# ============== GIF Sticker Settings ==============
GIF_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gif")
GIF_STICKER_COUNT = 2  # Number of GIF stickers to add

# ============== LLM Subtitle Rewrite Settings ==============
LLM_API_BASE = "https://yunwu.ai"
LLM_API_KEY = "sk-JiDUxeYDc9EnJ5Gmni1tYOvucP8o8WNmY78dvnV8lQq0wKW7"
LLM_MODEL = "gpt-4o-mini"

# ============== Glassmorphism Subtitle Settings ==============
GLASS_BAR_HEIGHT = 200
GLASS_BAR_COLOR = (255, 255, 255)  # White base
GLASS_BAR_OPACITY = 180  # Semi-transparent (0-255)
GLASS_BLUR_AMOUNT = 30  # Blur radius
GLASS_CORNER_RADIUS = 30
GLASS_TEXT_COLOR = (0, 0, 0)  # Black text
GLASS_TEXT_SIZE = 36
GLASS_TEXT_STROKE = 2
GLASS_TEXT_STROKE_COLOR = (255, 255, 255)

# ============== Logging Settings ==============
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"


def get_random_scale() -> float:
    """Get random scale factor within configured range."""
    return random.uniform(SCALE_MIN, SCALE_MAX)


def get_random_speed() -> float:
    """Get random speed factor within configured range."""
    return random.uniform(SPEED_MIN, SPEED_MAX)


def get_random_bg_color() -> Tuple[int, int, int]:
    """Get random background color from presets."""
    return random.choice(BG_COLORS)


def get_random_bg_image() -> Optional[str]:
    """
    Get random background image path from bg folder.

    Returns:
        Path to random background image, or None if folder is empty/not found
    """
    if not os.path.exists(BG_FOLDER):
        logger = logging.getLogger(__name__)
        logger.warning(f"Background image folder not found: {BG_FOLDER}")
        return None

    # Get all image files
    image_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    bg_images = [
        os.path.join(BG_FOLDER, f) for f in os.listdir(BG_FOLDER)
        if os.path.isfile(os.path.join(BG_FOLDER, f)) and
           os.path.splitext(f)[1].lower() in image_extensions
    ]

    if not bg_images:
        logger = logging.getLogger(__name__)
        logger.warning(f"No images found in background folder: {BG_FOLDER}")
        return None

    return random.choice(bg_images)


def get_snow_particle_count() -> int:
    """Get random snow particle count."""
    return random.randint(SNOW_PARTICLE_COUNT_MIN, SNOW_PARTICLE_COUNT_MAX)


def get_random_mirror() -> bool:
    """
    Get random mirror decision.

    Returns:
        True if should mirror, False otherwise
    """
    return random.choice([True, False])


def generate_mirror_intervals(duration: float, min_interval: float = 2.0, max_interval: float = 5.0) -> list:
    """
    Generate random time intervals for mirror effect.

    Args:
        duration: Total video duration in seconds
        min_interval: Minimum interval duration in seconds
        max_interval: Maximum interval duration in seconds

    Returns:
        List of (start_time, end_time, is_mirrored) tuples
    """
    intervals = []
    current_time = 0.0

    while current_time < duration:
        # Random interval duration
        interval_duration = random.uniform(min_interval, max_interval)
        end_time = min(current_time + interval_duration, duration)

        # Randomly decide if this interval should be mirrored
        is_mirrored = random.choice([True, False])

        intervals.append((current_time, end_time, is_mirrored))
        current_time = end_time

    return intervals


def should_mirror_at_time(mirror_intervals: list, time: float) -> bool:
    """
    Check if video should be mirrored at given time.

    Args:
        mirror_intervals: List of (start_time, end_time, is_mirrored) tuples
        time: Current time in seconds

    Returns:
        True if should mirror at this time, False otherwise
    """
    for start_time, end_time, is_mirrored in mirror_intervals:
        if start_time <= time < end_time:
            return is_mirrored
    return False


def get_random_rotation_angle() -> float:
    """
    Get random rotation angle in degrees.

    Returns:
        Random angle between ROTATION_MIN_DEGREES and ROTATION_MAX_DEGREES
    """
    return random.uniform(ROTATION_MIN_DEGREES, ROTATION_MAX_DEGREES)


def generate_frame_drop_intervals(duration: float) -> dict:
    """
    Generate random intervals for frame dropping.

    Args:
        duration: Total video duration in seconds

    Returns:
        Dictionary with {interval_index: drop_frames} mapping
        where drop_frames is a list of frame indices to drop
    """
    intervals = {}
    fps = 30  # Assume 30 fps
    total_frames = int(duration * fps)
    current_frame = 0

    while current_frame < total_frames:
        # Random interval duration in frames
        interval_frames = int(random.uniform(FRAME_DROP_INTERVAL_MIN, FRAME_DROP_INTERVAL_MAX) * fps)
        interval_end = min(current_frame + interval_frames, total_frames)

        # Random number of frames to drop in this interval
        drop_count = random.randint(FRAME_DROP_COUNT_MIN, FRAME_DROP_COUNT_MAX)

        # Randomly select frames to drop within this interval
        drop_frames = []
        available_frames = list(range(current_frame, interval_end))
        if available_frames:
            # Randomly select unique frames to drop
            drop_frames = random.sample(available_frames, min(drop_count, len(available_frames)))

        # Store the interval
        intervals[current_frame] = {
            'end_frame': interval_end,
            'drop_frames': drop_frames
        }

        current_frame = interval_end

    return intervals


def should_drop_frame_at_time(frame_drop_intervals: dict, time: float, fps: int = 30) -> bool:
    """
    Check if current frame should be dropped.

    Args:
        frame_drop_intervals: Dictionary with {start_frame: {'end_frame': n, 'drop_frames': [list]}}
        time: Current time in seconds
        fps: Frames per second

    Returns:
        True if this frame should be dropped, False otherwise
    """
    current_frame = int(time * fps)

    for start_frame, info in frame_drop_intervals.items():
        end_frame = info['end_frame']
        drop_frames = info['drop_frames']
        if start_frame <= current_frame < end_frame:
            return current_frame in drop_frames
    return False


def get_random_film_grain_params() -> tuple:
    """
    Get random film grain parameters.

    Returns:
        Tuple of (intensity, color)
    """
    intensity = random.uniform(FILM_GRAIN_INTENSITY_MIN, FILM_GRAIN_INTENSITY_MAX)
    color = random.choice(FILM_GRAIN_COLOR_OPTIONS)
    return (intensity, color)


def get_random_gif_files(count: int = 2) -> list:
    """
    Get random GIF files from the gif folder.

    Args:
        count: Number of GIF files to return

    Returns:
        List of paths to random GIF files
    """
    if not os.path.exists(GIF_FOLDER):
        logger = logging.getLogger(__name__)
        logger.warning(f"GIF folder not found: {GIF_FOLDER}")
        return []

    # Get all GIF files
    gif_files = [
        os.path.join(GIF_FOLDER, f) for f in os.listdir(GIF_FOLDER)
        if os.path.isfile(os.path.join(GIF_FOLDER, f)) and
           f.lower().endswith('.gif')
    ]

    if not gif_files:
        logger.warning(f"No GIF files found in: {GIF_FOLDER}")
        return []

    # Return random selection (without replacement)
    return random.sample(gif_files, k=min(count, len(gif_files)))


def generate_gif_stickers(canvas_width: int, canvas_height: int,
                          gif_count: int = GIF_STICKER_COUNT) -> list:
    """
    Generate random GIF sticker positions.

    Args:
        canvas_width: Canvas width
        canvas_height: Canvas height
        gif_count: Number of GIF stickers to generate

    Returns:
        List of GIF sticker dictionaries with path and position
    """
    stickers = []

    # Define positions for GIF stickers (top-left and top-right corners as per image)
    positions = [
        {'x': 20, 'y': 20, 'scale': 0.25},  # Top-left
        {'x': canvas_width - 150, 'y': 20, 'scale': 0.25},  # Top-right
    ]

    # Get random GIF files
    gif_files = get_random_gif_files(gif_count)

    for i, gif_path in enumerate(gif_files):
        if i < len(positions):
            pos = positions[i]
            stickers.append({
                'path': gif_path,
                'x': pos['x'],
                'y': pos['y'],
                'scale': pos['scale']
            })

    return stickers


def get_gif_count() -> int:
    """
    Get random GIF sticker count.

    Returns:
        Number of GIF stickers to add
    """
    return GIF_STICKER_COUNT


def get_output_filename(input_path: str, index: int, output_dir: str) -> str:
    """
    Generate output filename for processed video.

    Args:
        input_path: Original video file path
        index: Version index (1-based)
        output_dir: Output directory path

    Returns:
        Full path for output video file
    """
    basename = os.path.splitext(os.path.basename(input_path))[0]
    filename = f"{basename}_v{index}.{OUTPUT_FORMAT}"
    return os.path.join(output_dir, filename)


def generate_zoom_keyframes(duration: float,
                            num_keypoints: Optional[int] = None,
                            min_interval: float = DYNAMIC_ZOOM_MIN_INTERVAL,
                            max_interval: float = DYNAMIC_ZOOM_MAX_INTERVAL,
                            scale_min: float = SCALE_MIN,
                            scale_max: float = SCALE_MAX) -> List[Tuple[float, float]]:
    """
    Generate random zoom keyframes for dynamic zoom effect.

    Args:
        duration: Video duration in seconds
        num_keypoints: Number of keypoints (random if None)
        min_interval: Minimum seconds between keypoints
        max_interval: Maximum seconds between keypoints
        scale_min: Minimum scale value
        scale_max: Maximum scale value

    Returns:
        List of (time, scale) tuples, sorted by time
    """
    import random

    if num_keypoints is None:
        num_keypoints = random.randint(DYNAMIC_ZOOM_MIN_KEYPOINTS, DYNAMIC_ZOOM_MAX_KEYPOINTS)

    # Always include start and end points
    keyframes = [(0.0, random.uniform(scale_min, scale_max))]

    # Generate intermediate keypoints
    current_time = 0.0
    remaining_time = duration

    for _ in range(num_keypoints - 2):
        # Calculate time for next keypoint
        max_next_interval = min(max_interval, remaining_time / 2)
        if max_next_interval <= min_interval:
            break

        interval = random.uniform(min_interval, max_next_interval)
        current_time += interval
        remaining_time = duration - current_time

        if remaining_time < min_interval:
            break

        scale = random.uniform(scale_min, scale_max)
        keyframes.append((current_time, scale))

    # Always add end point
    keyframes.append((duration, random.uniform(scale_min, scale_max)))

    # Sort by time
    keyframes.sort(key=lambda x: x[0])

    return keyframes


def get_scale_at_time(keyframes: List[Tuple[float, float]], time: float) -> float:
    """
    Get the scale value at a specific time by interpolating between keyframes.

    Args:
        keyframes: List of (time, scale) tuples
        time: Current time in seconds

    Returns:
        Scale value at the given time
    """
    if not keyframes:
        return random.uniform(SCALE_MIN, SCALE_MAX)

    if len(keyframes) == 1:
        return keyframes[0][1]

    # Find the keyframes surrounding the current time
    for i in range(len(keyframes) - 1):
        t0, s0 = keyframes[i]
        t1, s1 = keyframes[i + 1]

        if t0 <= time <= t1:
            # Linear interpolation
            if t1 == t0:
                return s0
            ratio = (time - t0) / (t1 - t0)
            return s0 + (s1 - s0) * ratio

    # If time is beyond all keyframes, return last scale
    return keyframes[-1][1]


def validate_params(scale: Optional[float] = None,
                    speed: Optional[float] = None,
                    count: Optional[int] = None) -> Tuple[bool, str]:
    """
    Validate processing parameters.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if scale is not None and (scale < SCALE_MIN or scale > SCALE_MAX):
        return False, f"Scale must be between {SCALE_MIN} and {SCALE_MAX}"

    if speed is not None and (speed < SPEED_MIN or speed > SPEED_MAX):
        return False, f"Speed must be between {SPEED_MIN} and {SPEED_MAX}"

    if count is not None and (count < MIN_BATCH_COUNT or count > MAX_BATCH_COUNT):
        return False, f"Count must be between {MIN_BATCH_COUNT} and {MAX_BATCH_COUNT}"

    return True, ""


# ============== Template Settings ==============
TEMPLATE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

# Ensure template folder exists
os.makedirs(TEMPLATE_FOLDER, exist_ok=True)


def save_template(name: str, params: dict) -> bool:
    """
    Save processing parameters as a template.

    Args:
        name: Template name
        params: Dictionary of parameters to save

    Returns:
        True if successful, False otherwise
    """
    import json

    # Sanitize filename
    safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
    if not safe_name:
        safe_name = "template"

    filename = f"{safe_name}.json"
    filepath = os.path.join(TEMPLATE_FOLDER, filename)

    # Add metadata
    template_data = {
        "name": name,
        "created_at": str(__import__('datetime').datetime.now()),
        "params": params
    }

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Template saved: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to save template: {e}")
        return False


def load_template(filepath: str) -> Optional[dict]:
    """
    Load a template from file.

    Args:
        filepath: Path to template file

    Returns:
        Template data dictionary or None if failed
    """
    import json

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        return template_data
    except Exception as e:
        logger.error(f"Failed to load template: {e}")
        return None


def get_template_list() -> List[dict]:
    """
    Get list of all saved templates.

    Returns:
        List of template metadata dictionaries
    """
    import json

    templates = []
    if not os.path.exists(TEMPLATE_FOLDER):
        return templates

    for filename in os.listdir(TEMPLATE_FOLDER):
        if filename.endswith('.json'):
            filepath = os.path.join(TEMPLATE_FOLDER, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                    template_data['filename'] = filename
                    template_data['filepath'] = filepath
                    templates.append(template_data)
            except Exception as e:
                logger.warning(f"Failed to load template {filename}: {e}")

    # Sort by name
    templates.sort(key=lambda x: x.get('name', ''))
    return templates


def delete_template(filepath: str) -> bool:
    """
    Delete a template file.

    Args:
        filepath: Path to template file

    Returns:
        True if successful, False otherwise
    """
    try:
        os.remove(filepath)
        logger.info(f"Template deleted: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete template: {e}")
        return False


def params_to_text(params: dict) -> str:
    """
    Convert parameters to human-readable text format.

    Args:
        params: Dictionary of parameters

    Returns:
        Formatted text string
    """
    lines = ["📋 视频处理参数", "=" * 30]

    # Scale mode
    if params.get('scale_mode') == 'dynamic':
        lines.append(f"🔍 缩放模式: 动态缩放")
        lines.append(f"   关键帧数量: {params.get('zoom_keypoint_count', 3)}")
        lines.append(f"   最小间隔: {params.get('zoom_min_interval', 2.0)}秒")
        lines.append(f"   最大间隔: {params.get('zoom_max_interval', 5.0)}秒")
    elif params.get('scale_mode') == 'fixed':
        lines.append(f"🔍 缩放模式: 固定值")
        lines.append(f"   缩放比例: {params.get('scale', 0.85):.2f}")
    else:
        lines.append(f"🔍 缩放模式: 随机")

    # Speed mode
    if params.get('speed_mode') == 'fixed':
        lines.append(f"🚀 视频速度: {params.get('speed', 1.2):.2f}x (固定)")
    else:
        lines.append(f"🚀 视频速度: 随机")

    # Mirror mode
    mirror_mode = params.get('mirror_mode', 'off')
    if mirror_mode == 'on':
        lines.append(f"🔄 镜像翻转: 开启")
    elif mirror_mode == 'random':
        lines.append(f"🔄 镜像翻转: 随机")
    else:
        lines.append(f"🔄 镜像翻转: 关闭")

    # Background
    if params.get('bg_mode') == 'custom':
        bg_color = params.get('bg_color', (200, 220, 255))
        lines.append(f"🎨 背景: 自定义 RGB{bg_color}")
    elif params.get('bg_mode') == 'image':
        lines.append(f"🎨 背景: 图片背景")
    else:
        lines.append(f"🎨 背景: 随机颜色")

    # Effects
    lines.append(f"\n✨ 特效设置:")
    lines.append(f"   飘雪特效: {'✅ 启用' if params.get('enable_snow') else '❌ 关闭'}")
    lines.append(f"   显示文案: {'✅ 启用' if params.get('enable_text') else '❌ 关闭'}")
    if params.get('enable_text'):
        lines.append(f"   文案内容: {params.get('text_content', '')}")

    # Video effects
    lines.append(f"\n🎨 视频画面特效:")
    lines.append(f"   圆角视频: {'✅ ' if params.get('enable_rounded_corners') else '❌ '}({params.get('corner_radius', 0)}px)")
    lines.append(f"   视频边框: {'✅ ' if params.get('enable_border') else '❌ '}({params.get('video_border_width', 0)}px)")

    # Filters
    if params.get('enable_warmth'):
        lines.append(f"   暖色调滤镜: ✅ ({params.get('warmth_value', 5)})")
    if params.get('enable_contrast'):
        lines.append(f"   对比度调整: ✅ ({params.get('contrast_value', -3.0)})")

    # Other effects
    lines.append(f"\n🎀 其他特效:")
    lines.append(f"   视频内进度条: {'✅ ' if params.get('enable_video_progress_bar') else '❌ '}")
    lines.append(f"   添加贴纸: {'✅ ' if params.get('enable_stickers') else '❌ '}")
    lines.append(f"   GIF贴纸: {'✅ ' if params.get('enable_gif_stickers') else '❌ '}")
    lines.append(f"   底部遮挡条: {'✅ ' if params.get('enable_blur_bar') else '❌ '}")
    if params.get('enable_blur_bar'):
        lines.append(f"   遮挡条高度: {params.get('blur_bar_height', 150)}px")
    lines.append(f"   两侧文字: {'✅ ' if params.get('enable_side_text') else '❌ '}")

    # Batch
    lines.append(f"\n📦 批量生成: {params.get('count', 3)} 个版本")

    lines.append("=" * 30)
    lines.append("🎬 Short Video Repurposing Tool")

    return "\n".join(lines)


# ============== SRT Subtitle Parsing ==============

def parse_srt(srt_content: str) -> List[Dict]:
    """
    Parse SRT subtitle content into a list of subtitle entries.

    Args:
        srt_content: Raw SRT file content

    Returns:
        List of dictionaries containing 'id', 'start_time', 'end_time', 'text'
    """
    subtitles = []
    pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n([\s\S]*?)(?=\n\n|\Z)'

    matches = re.findall(pattern, srt_content + '\n\n')

    for match in matches:
        subtitle = {
            'id': int(match[0]),
            'start_time': match[1],
            'end_time': match[2],
            'text': match[3].strip()
        }
        subtitles.append(subtitle)

    return subtitles


def time_to_seconds(time_str: str) -> float:
    """
    Convert SRT time format (HH:MM:SS,mmm) to seconds.

    Args:
        time_str: Time string in SRT format

    Returns:
        Time in seconds
    """
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds_parts = parts[2].split(',')
    seconds = int(seconds_parts[0])
    milliseconds = int(seconds_parts[1])

    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0


def seconds_to_time(seconds: float) -> str:
    """
    Convert seconds to SRT time format (HH:MM:SS,mmm).

    Args:
        seconds: Time in seconds

    Returns:
        Time string in SRT format
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"


# ============== LLM Subtitle Rewrite ==============

def rewrite_subtitles_with_llm(subtitles: List[Dict],
                                api_base: str = LLM_API_BASE,
                                api_key: str = LLM_API_KEY,
                                model: str = LLM_MODEL,
                                style: str = "natural") -> List[Dict]:
    """
    Use LLM to rewrite subtitles with different expressions.

    Args:
        subtitles: List of subtitle dictionaries
        api_base: LLM API base URL
        api_key: LLM API key
        model: Model name
        style: Rewrite style - "natural", "humorous", "professional", "concise"

    Returns:
        List of subtitle dictionaries with rewritten text
    """
    import requests
    import json

    # Extract original texts
    original_texts = [s['text'] for s in subtitles]
    texts_json = json.dumps(original_texts, ensure_ascii=False)

    # System prompt based on style
    style_prompts = {
        "natural": "将字幕改写成自然、口语化的表达，保持原意但换一种说法。",
        "humorous": "将字幕改写成幽默、轻松的语气，可以适当加入网络流行语。",
        "professional": "将字幕改写成专业、正式的表达，适合知识类内容。",
        "concise": "将字幕改写成简洁精炼的表达，去除冗余词语。"
    }

    style_prompt = style_prompts.get(style, style_prompts["natural"])

    system_prompt = f"""你是一个视频字幕改写助手。你的任务是改写给定的字幕列表。

要求：
1. {style_prompt}
2. 保持每条字幕的长度适中，适合视频观看
3. 不要改变字幕的时间戳
4. 只返回改写后的字幕列表，不要添加任何解释
5. 返回JSON数组格式，直接是可解析的字幕文本列表

返回格式：JSON数组，每个元素是对应位置的改写后字幕文本。"""

    user_prompt = f"请改写以下字幕列表（保持原顺序）：\n{texts_json}"

    try:
        response = requests.post(
            f"{api_base}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7
            },
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']

            # Try to parse the response as JSON
            try:
                # Clean up the response (remove markdown code blocks if present)
                content = content.strip()
                if content.startswith('```json'):
                    content = content[7:]
                if content.endswith('```'):
                    content = content[:-3]
                content = content.strip()

                rewritten_texts = json.loads(content)

                # Ensure we have the same number of subtitles
                if len(rewritten_texts) == len(subtitles):
                    for i, subtitle in enumerate(subtitles):
                        subtitle['text'] = rewritten_texts[i]
                    logger.info(f"Successfully rewrote {len(subtitles)} subtitles with LLM")
                else:
                    logger.warning(f"Rewritten text count mismatch: {len(rewritten_texts)} vs {len(subtitles)}")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"Response content: {content}")

        else:
            logger.error(f"LLM API error: {response.status_code} - {response.text}")

    except Exception as e:
        logger.error(f"Failed to call LLM API: {e}")

    return subtitles


def process_srt_file(srt_path: str,
                     api_base: str = LLM_API_BASE,
                     api_key: str = LLM_API_KEY,
                     model: str = LLM_MODEL,
                     rewrite: bool = False,
                     style: str = "natural") -> Optional[List[Dict]]:
    """
    Load and optionally rewrite an SRT file.

    Args:
        srt_path: Path to SRT file
        api_base: LLM API base URL
        api_key: LLM API key
        model: Model name
        rewrite: Whether to rewrite subtitles with LLM
        style: Rewrite style

    Returns:
        List of subtitle dictionaries or None if failed
    """
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()

        subtitles = parse_srt(content)
        logger.info(f"Loaded {len(subtitles)} subtitles from {srt_path}")

        if rewrite and subtitles:
            subtitles = rewrite_subtitles_with_llm(
                subtitles, api_base, api_key, model, style
            )

        return subtitles

    except Exception as e:
        logger.error(f"Failed to process SRT file: {e}")
        return None


def generate_srt_content(subtitles: List[Dict]) -> str:
    """
    Generate SRT content from subtitle list.

    Args:
        subtitles: List of subtitle dictionaries

    Returns:
        SRT formatted string
    """
    lines = []
    for sub in subtitles:
        lines.append(str(sub['id']))
        lines.append(f"{sub['start_time']} --> {sub['end_time']}")
        lines.append(sub['text'])
        lines.append("")  # Empty line between subtitles

    return "\n".join(lines)


def save_srt_file(subtitles: List[Dict], output_path: str) -> bool:
    """
    Save subtitles to SRT file.

    Args:
        subtitles: List of subtitle dictionaries
        output_path: Output file path

    Returns:
        True if successful, False otherwise
    """
    try:
        content = generate_srt_content(subtitles)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"Failed to save SRT file: {e}")
        return False


# ============== Advanced Video Deduplication Settings ==============
# ============== 一、画面维度 (Visual Dimension) ==============

# 1.1 几何变换类 (Geometric Transformations)
# 1.1.1 镜像翻转
MIRROR_HORIZONTAL = "hflip"  # 水平翻转
MIRROR_VERTICAL = "vflip"    # 垂直翻转

# 1.1.2 旋转变换
ROTATION_MIN_DEGREES = 0.5
ROTATION_MAX_DEGREES = 3.0
ROTATION_FIXED_ANGLES = [90, 180, 270]  # 固定角度
ROTATION_DYNAMIC_MIN = -2.0  # 动态旋转范围
ROTATION_DYNAMIC_MAX = 2.0

# 1.1.3 缩放操作
SCALE_ZOOM_MIN = 1.01
SCALE_ZOOM_MAX = 1.15
SCALE_BREATH_MIN = 0.98  # 呼吸效果
SCALE_BREATH_MAX = 1.05
SCALE_BREATH_PERIOD = 2.0  # 呼吸周期(秒)

# 1.1.4 裁剪操作
CROP_EDGE_MIN = 1
CROP_EDGE_MAX = 20
CROP_CENTER_RATIO = 0.9  # 中心裁剪比例

# 1.1.5 透视变换
PERSPECTIVE_MIN = 0.02
PERSPECTIVE_MAX = 0.1

# 1.1.6 位移操作
DISPLACEMENT_MIN = 5
DISPLACEMENT_MAX = 30
SHAKE_INTENSITY = 3  # 抖动强度

# 1.2 色彩调整类 (Color Adjustments)
# 1.2.1 基础调色
BRIGHTNESS_MIN = -0.1
BRIGHTNESS_MAX = 0.1
CONTRAST_MIN = 0.95
CONTRAST_MAX = 1.1
SATURATION_MIN = 0.9
SATURATION_MAX = 1.15
HUE_SHIFT_MIN = -10
HUE_SHIFT_MAX = 10
GAMMA_MIN = 0.9
GAMMA_MAX = 1.1

# 1.2.2 高级调色
CURVES_STRENGTH = 0.3  # 曲线调整强度
LEVELS_SHADOW = 10
LEVELS_HIGHLIGHT = 245
COLOR_TEMP_MIN = -20  # 色温
COLOR_TEMP_MAX = 20

# 1.2.3 滤镜效果
LUT_FILTERS = ["vintage", "cool", "warm", "bw", "sepia", "negate"]
POSTERIZE_LEVELS = 8

# 1.2.4 通道操作
CHANNEL_MIX_PRESETS = [
    {"name": "normal", "r": 1.0, "g": 1.0, "b": 1.0},
    {"name": "swap_rg", "r": 0.0, "g": 1.0, "b": 0.0},
    {"name": "grayscale", "r": 0.33, "g": 0.33, "b": 0.33},
]

# 1.3 清晰度调整类 (Sharpness Adjustments)
# 1.3.1 模糊效果
GAUSSIAN_BLUR_MIN = 0.1
GAUSSIAN_BLUR_MAX = 1.0
MOTION_BLUR_ANGLE_MIN = 0
MOTION_BLUR_ANGLE_MAX = 360
MOTION_BLUR_INTENSITY = 5

# 1.3.2 锐化效果
SHARPEN_STRENGTH = 1.5
USM_AMOUNT = 1.0
USM_RADIUS = 2.0
USM_THRESHOLD = 10

# 1.3.3 降噪处理
DENOISE_STRENGTH = 5
DENOISE_LUM = 3
DENOISE_CHROM = 5

# 1.4 纹理添加类 (Texture Additions)
# 1.4.1 噪点效果
FILM_GRAIN_INTENSITY_MIN = 0.01
FILM_GRAIN_INTENSITY_MAX = 0.08
NOISE_DENSITY = 0.05
TEMPORAL_NOISE_AMOUNT = 3

# 1.4.2 叠加纹理
SCRATCH_DENSITY = 0.02
DUST_DENSITY = 0.05
LEAK_INTENSITY = 0.1

# 1.4.3 抖动效果
DITHERING_LEVEL = 2
QUANTIZE_LEVELS = 64

# 1.5 边缘检测类 (Edge Detection)
EDGE_THRESHOLD = 50
CARTOON_LEVEL = 5


# ============== 二、音频维度 (Audio Dimension) ==============

# 2.1 音量控制类 (Volume Control)
VOLUME_GAIN_MIN = -3  # dB
VOLUME_GAIN_MAX = 3
COMPRESSOR_RATIO = 4.0
COMPRESSOR_THRESHOLD = -20
LIMITER_THRESHOLD = -1

FADE_DURATION = 1.0  # 秒
LOUDNORM_TARGET_I = -16  # LUFS
LOUDNORM_TARGET_TP = -1.5
LOUDNORM_TARGET_LRA = 11.0

# 2.2 音调速率类 (Pitch & Rate)
ATEMP_MIN = 0.95
ATEMP_MAX = 1.05
PITCH_SHIFT_MIN = -200  # 音分
PITCH_SHIFT_MAX = 200
RUBBERBAND_PITCH = 1.0

# 2.3 频率处理类 (Frequency Processing)
BASS_GAIN_MIN = -10
BASS_GAIN_MAX = 10
TREBLE_GAIN_MIN = -10
TREBLE_GAIN_MAX = 10
EQUALIZER_BANDS = [60, 230, 910, 3600, 14000]  # Hz

HIGHPASS_FREQ = 80
LOWPASS_FREQ = 12000
BANDPASS_CENTER = 1000
BANDPASS_WIDTH = 500

# 2.4 效果器类 (Audio Effects)
REVERB_ROOM_SIZE = 0.7
REVERB_DAMPING = 0.5
REVERB_WET_LEVEL = 0.3
ECHO_DELAY = 500  # ms
ECHO_DECAY = 0.5
DELAY_TIME = 250  # ms

# 2.5 叠加混音类 (Audio Mixing)
BG_VOLUME = 0.03  # 背景音量 3%
NOISE_FLOOR = -60  # dB


# ============== 三、容器维度 (Container Dimension) ==============

# 3.1 画布布局类 (Canvas Layout)
ASPECT_RATIOS = {
    "16:9": (16, 9),
    "9:16": (9, 16),
    "1:1": (1, 1),
    "4:3": (4, 3),
    "2.35:1": (2.35, 1),
}

CANVAS_SIZES = {
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "2K": (2560, 1440),
    "vertical": (1080, 1920),
    "square": (1080, 1080),
}

# 3.1.3 边框效果
BORDER_STYLES = ["phone", "film", "frame", "none"]
BORDER_THICKNESS = 20
PHONE_FRAME_COLOR = (30, 30, 30)
FIRM_FRAME_ASPect = 2.35

# 3.2 分辨率类 (Resolution)
NON_STANDARD_RESOLUTIONS = [
    (1920, 1072), (1920, 1088), (1918, 1080), (1922, 1078)
]


# ============== 四、内容维度 (Content Dimension) ==============

# 4.1 时间序列类 (Time Series)
# 4.1.1 变速操作
SPEED_CURVE_PRESETS = ["linear", "ease_in", "ease_out", "ease_in_out"]

# 4.1.2 帧率操作
FPS_TARGETS = [24, 25, 30, 50, 60]
FRAME_DROP_PATTERN = [1, 0, 0, 0]  # 每4帧删1帧

# 4.1.3 帧操作
FRAME_SHUFFLE_CHUNK = 5  # 每5帧可能打乱
KEYFRAME_INTERVAL = 2.0  # 秒

# 4.1.4 转场效果
TRANSITION_DURATION = 0.5  # 秒
TRANSITION_TYPES = ["fade", "flash", "wipe"]


# ============== 五、元数据/编码维度 (Metadata & Encoding) ==============

# 5.1 编码参数类 (Encoding Parameters)
VIDEO_CODECS = {
    "h264": "libx264",
    "h265": "libx265",
    "vp9": "libvpx-vp9",
    "av1": "libaom-av1",
}

BITRATE_PRESETS = {
    "low": "3000k",
    "medium": "6000k",
    "high": "12000k",
    "ultra": "25000k",
}

X264_PRESETS = ["veryslow", "slow", "medium", "fast", "veryfast", "superfast"]
X264_PROFILES = ["baseline", "main", "high"]

GOP_LENGTH_MIN = 50
GOP_LENGTH_MAX = 250
B_FRAMES_COUNT = 4

CRF_MIN = 18
CRF_MAX = 28
DEFAULT_CRF = 23

# 5.2 色彩空间类 (Color Space)
COLOR_SPACES = ["bt709", "bt2020", "bt601"]
COLOR_RANGES = ["limited", "full"]
PIXEL_FORMATS = ["yuv420p", "yuv422p", "yuv444p"]

# 5.3 元数据操作类 (Metadata Operations)
REMOVE_ALL_METADATA = False
STRIP_GPS = True
STRIP_CREATION_TIME = False

MODIFIED_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
CUSTOM_TAGS = {}


# ============== Helper Functions for Advanced Deduplication ==============

def get_random_crop_params(canvas_width: int, canvas_height: int) -> dict:
    """获取随机裁剪参数"""
    crop_amount = random.randint(CROP_EDGE_MIN, CROP_EDGE_MAX)
    crop_type = random.choice(["edge", "center", "random"])

    if crop_type == "edge":
        return {
            "type": "edge",
            "top": crop_amount,
            "bottom": crop_amount,
            "left": crop_amount,
            "right": crop_amount,
        }
    elif crop_type == "center":
        ratio = random.uniform(0.85, CROP_CENTER_RATIO)
        return {
            "type": "center",
            "ratio": ratio,
        }
    else:  # random
        return {
            "type": "random",
            "top": random.randint(0, crop_amount),
            "bottom": random.randint(0, crop_amount),
            "left": random.randint(0, crop_amount),
            "right": random.randint(0, crop_amount),
        }


def get_color_adjustment_params() -> dict:
    """获取随机色彩调整参数"""
    return {
        "brightness": random.uniform(BRIGHTNESS_MIN, BRIGHTNESS_MAX),
        "contrast": random.uniform(CONTRAST_MIN, CONTRAST_MAX),
        "saturation": random.uniform(SATURATION_MIN, SATURATION_MAX),
        "hue_shift": random.uniform(HUE_SHIFT_MIN, HUE_SHIFT_MAX),
        "gamma": random.uniform(GAMMA_MIN, GAMMA_MAX),
    }


def get_audio_effect_params() -> dict:
    """获取随机音效参数"""
    return {
        "volume_gain": random.uniform(VOLUME_GAIN_MIN, VOLUME_GAIN_MAX),
        "bass_gain": random.uniform(BASS_GAIN_MIN, BASS_GAIN_MAX),
        "treble_gain": random.uniform(TREBLE_GAIN_MIN, TREBLE_GAIN_MAX),
        "enable_compressor": random.choice([True, False]),
        "enable_reverb": random.choice([True, False]),
    }


def get_encoding_params(codec: str = "h264", quality: str = "medium") -> dict:
    """获取编码参数"""
    return {
        "codec": VIDEO_CODECS.get(codec, "libx264"),
        "bitrate": BITRATE_PRESETS.get(quality, "6000k"),
        "preset": random.choice(X264_PRESETS),
        "profile": random.choice(X264_PROFILES),
        "crf": random.randint(CRF_MIN, CRF_MAX) if quality == "medium" else CRF_MIN,
        "gop_size": random.randint(GOP_LENGTH_MIN, GOP_LENGTH_MAX),
        "b_frames": B_FRAMES_COUNT,
    }


def get_canvas_size(preset: str = "1080p") -> tuple:
    """获取画布尺寸"""
    return CANVAS_SIZES.get(preset, (1920, 1080))


def get_aspect_ratio(name: str = "16:9") -> tuple:
    """获取宽高比"""
    return ASPECT_RATIOS.get(name, (16, 9))


def apply_random_metadata_modification(original_path: str, output_path: str) -> bool:
    """应用随机元数据修改"""
    try:
        import subprocess
        import datetime

        # 生成随机时间戳
        random_date = datetime.datetime.now() - datetime.timedelta(
            days=random.randint(1, 365)
        )
        date_str = random_date.strftime(MODIFIED_DATE_FORMAT)

        # 使用FFmpeg移除/修改元数据
        cmd = [
            "ffmpeg", "-i", original_path,
            "-c", "copy",
            "-map_metadata", "-1",  # 移除全局元数据
            "-movflags", "+faststart",
        ]

        # 添加随机字节数据以改变MD5
        random_bytes = bytes([random.randint(0, 255) for _ in range(16)])

        cmd.extend([
            "-metadata", f"creation_time={date_str}",
            "-f", "null",  # 不实际写入，仅作示例
            "-",
        ])

        return True
    except Exception as e:
        logger.error(f"Failed to apply metadata modification: {e}")
        return False


def get_perspective_transform_params(width: int, height: int) -> list:
    """获取透视变换参数"""
    intensity = random.uniform(PERSPECTIVE_MIN, PERSPECTIVE_MAX)

    # 原始四个角点
    src_points = [
        [0, 0],
        [width, 0],
        [width, height],
        [0, height]
    ]

    # 目标点（轻微偏移）
    max_offset = min(width, height) * intensity
    dst_points = [
        [random.uniform(0, max_offset), random.uniform(0, max_offset)],
        [width - random.uniform(0, max_offset), random.uniform(0, max_offset)],
        [width - random.uniform(0, max_offset), height - random.uniform(0, max_offset)],
        [random.uniform(0, max_offset), height - random.uniform(0, max_offset)]
    ]

    return list(zip(src_points, dst_points))


def get_displacement_params(canvas_width: int, canvas_height: int) -> dict:
    """获取位移参数"""
    displacement_type = random.choice(["fixed", "shake", "slide"])

    if displacement_type == "fixed":
        return {
            "type": "fixed",
            "x": random.randint(-DISPLACEMENT_MAX, DISPLACEMENT_MAX),
            "y": random.randint(-DISPLACEMENT_MAX, DISPLACEMENT_MAX),
        }
    elif displacement_type == "shake":
        return {
            "type": "shake",
            "intensity": SHAKE_INTENSITY,
            "frequency": random.uniform(5, 15),  # Hz
        }
    else:  # slide
        return {
            "type": "slide",
            "direction": random.choice(["left", "right", "up", "down"]),
            "distance": random.randint(DISPLACEMENT_MIN, DISPLACEMENT_MAX),
        }


def get_filter_params() -> dict:
    """获取滤镜参数"""
    return {
        "lut_filter": random.choice(LUT_FILTERS),
        "posterize_levels": POSTERIZE_LEVELS,
        "channel_mix": random.choice(CHANNEL_MIX_PRESETS),
    }


def get_sharpness_params() -> dict:
    """获取清晰度参数"""
    return {
        "gaussian_blur": random.uniform(GAUSSIAN_BLUR_MIN, GAUSSIAN_BLUR_MAX),
        "sharpen_strength": SHARPEN_STRENGTH,
        "usm_amount": USM_AMOUNT,
        "usm_radius": USM_RADIUS,
        "denoise_strength": DENOISE_STRENGTH,
    }


def get_texture_params() -> dict:
    """获取纹理参数"""
    return {
        "grain_intensity": random.uniform(FILM_GRAIN_INTENSITY_MIN, FILM_GRAIN_INTENSITY_MAX),
        "noise_density": NOISE_DENSITY,
        "scratch_density": SCRATCH_DENSITY,
        "dust_density": DUST_DENSITY,
        "dithering_level": DITHERING_LEVEL,
    }


# ============== Strategy Combination Generator ==============

DEDUPLICATION_STRATEGIES = {
    # Visual Dimension (画面维度)
    "visual": {
        "crop": {"enable": False, "params": None, "name": "裁剪效果", "category": "几何变换"},
        "perspective": {"enable": False, "params": None, "name": "透视变换", "category": "几何变换"},
        "displacement": {"enable": False, "params": None, "name": "位移效果", "category": "几何变换"},
        "brightness": {"enable": False, "value": 0.0, "name": "亮度调整", "category": "色彩"},
        "saturation": {"enable": False, "value": 1.0, "name": "饱和度", "category": "色彩"},
        "hue_shift": {"enable": False, "value": 0.0, "name": "色相偏移", "category": "色彩"},
        "gamma": {"enable": False, "value": 1.0, "name": "伽马校正", "category": "色彩"},
        "lut_filter": {"enable": False, "value": None, "name": "LUT滤镜", "category": "色彩"},
        "gaussian_blur": {"enable": False, "value": 0.0, "name": "高斯模糊", "category": "清晰度"},
        "sharpen": {"enable": False, "value": 0.0, "name": "锐化", "category": "清晰度"},
        "denoise": {"enable": False, "value": 0, "name": "降噪", "category": "清晰度"},
        "scratches": {"enable": False, "value": 0.0, "name": "划痕", "category": "纹理"},
        "dust": {"enable": False, "value": 0.0, "name": "灰尘", "category": "纹理"},
        "light_leak": {"enable": False, "value": 0.0, "name": "漏光", "category": "纹理"},
        "edge_detect": {"enable": False, "threshold": 50, "name": "边缘检测", "category": "特效"},
        "cartoon": {"enable": False, "level": 5, "name": "卡通效果", "category": "特效"},
    },
    # Audio Dimension (音频维度)
    "audio": {
        "volume_adjust": {"enable": False, "value": 0.0, "name": "音量调整", "category": "音量"},
        "compressor": {"enable": False, "name": "压缩器", "category": "效果器"},
        "reverb": {"enable": False, "name": "混响", "category": "效果器"},
        "bass_treble": {"enable": False, "bass": 0.0, "treble": 0.0, "name": "低音高音", "category": "均衡器"},
    },
    # Container Dimension (容器维度)
    "container": {
        "aspect_ratio": {"enable": False, "value": "16:9", "name": "宽高比", "category": "画布"},
        "canvas_size": {"enable": False, "value": "1080p", "name": "画布尺寸", "category": "画布"},
    },
    # Content Dimension (内容维度)
    "content": {
        "speed_curve": {"enable": False, "value": "linear", "name": "变速曲线", "category": "时间"},
        "target_fps": {"enable": False, "value": "30", "name": "目标帧率", "category": "时间"},
        "transition": {"enable": False, "type": "fade", "name": "转场", "category": "时间"},
    },
    # Metadata Dimension (元数据维度)
    "metadata": {
        "codec": {"enable": False, "value": "h264", "name": "编码器", "category": "编码"},
        "crf": {"enable": False, "value": 23, "name": "CRF值", "category": "编码"},
        "color_space": {"enable": False, "value": "bt709", "name": "色彩空间", "category": "编码"},
        "pixel_format": {"enable": False, "value": "yuv420p", "name": "像素格式", "category": "编码"},
        "remove_metadata": {"enable": False, "name": "移除元数据", "category": "元数据"},
    }
}


def generate_random_strategy(level: str = "minimal") -> dict:
    """
    生成随机去重策略组合

    Args:
        level: 策略级别
            - "minimal": 最小有效组合 (3-5项)
            - "moderate": 中度组合 (8-12项)
            - "deep": 深度组合 (15+项)

    Returns:
        策略组合字典
    """
    # 定义不同级别的策略数量范围
    level_config = {
        "minimal": {"min": 3, "max": 5, "name": "最小有效组合"},
        "moderate": {"min": 8, "max": 12, "name": "中度组合"},
        "deep": {"min": 15, "max": 25, "name": "深度组合"}
    }

    config = level_config.get(level, level_config["minimal"])
    min_count = config["min"]
    max_count = config["max"]
    target_count = random.randint(min_count, max_count)

    # 收集所有可用的策略
    all_strategies = []
    for dimension, strategies in DEDUPLICATION_STRATEGIES.items():
        for key, strategy in strategies.items():
            all_strategies.append({
                "dimension": dimension,
                "key": key,
                "strategy": strategy
            })

    # 随机选择策略
    selected = random.sample(all_strategies, min(target_count, len(all_strategies)))

    # 生成策略参数
    result = {
        "level": level,
        "level_name": config["name"],
        "count": len(selected),
        "strategies": {},
        "enabled_list": []
    }

    for item in selected:
        dimension = item["dimension"]
        key = item["key"]
        strategy = item["strategy"]

        # 生成随机参数值
        if key == "crop":
            crop_type = random.choice(["edge", "center", "random"])
            if crop_type == "edge":
                amount = random.randint(CROP_EDGE_MIN, CROP_EDGE_MAX)
                params = {
                    "type": "edge",
                    "top": amount,
                    "bottom": amount,
                    "left": amount,
                    "right": amount
                }
            elif crop_type == "center":
                ratio = random.uniform(0.85, CROP_CENTER_RATIO)
                params = {"type": "center", "ratio": ratio}
            else:
                params = {"type": "random"}

            result["strategies"][key] = {
                "enable": True,
                "crop_params": params,
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "perspective":
            result["strategies"][key] = {
                "enable": True,
                "perspective_params": get_perspective_transform_params(1920, 1080),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "displacement":
            disp_type = random.choice(["fixed", "shake", "slide"])
            if disp_type == "fixed":
                params = {
                    "type": "fixed",
                    "x": random.randint(-DISPLACEMENT_MAX, DISPLACEMENT_MAX),
                    "y": random.randint(-DISPLACEMENT_MAX, DISPLACEMENT_MAX)
                }
            elif disp_type == "shake":
                params = {
                    "type": "shake",
                    "intensity": random.randint(1, 10),
                    "frequency": random.uniform(5, 15)
                }
            else:
                params = {
                    "type": "slide",
                    "direction": random.choice(["left", "right", "up", "down"]),
                    "distance": random.randint(DISPLACEMENT_MIN, DISPLACEMENT_MAX)
                }

            result["strategies"][key] = {
                "enable": True,
                "displacement_params": params,
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "brightness":
            result["strategies"][key] = {
                "enable": True,
                "brightness_value": random.uniform(BRIGHTNESS_MIN, BRIGHTNESS_MAX),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "saturation":
            result["strategies"][key] = {
                "enable": True,
                "saturation_value": random.uniform(SATURATION_MIN, SATURATION_MAX),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "hue_shift":
            result["strategies"][key] = {
                "enable": True,
                "hue_shift_value": random.uniform(HUE_SHIFT_MIN, HUE_SHIFT_MAX),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "gamma":
            result["strategies"][key] = {
                "enable": True,
                "gamma_value": random.uniform(GAMMA_MIN, GAMMA_MAX),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "lut_filter":
            result["strategies"][key] = {
                "enable": True,
                "lut_filter": random.choice(LUT_FILTERS),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "gaussian_blur":
            result["strategies"][key] = {
                "enable": True,
                "gaussian_blur_value": random.uniform(GAUSSIAN_BLUR_MIN, GAUSSIAN_BLUR_MAX),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "sharpen":
            result["strategies"][key] = {
                "enable": True,
                "sharpen_strength": random.uniform(1.0, 3.0),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "denoise":
            result["strategies"][key] = {
                "enable": True,
                "denoise_strength": random.randint(1, 10),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "scratches":
            result["strategies"][key] = {
                "enable": True,
                "scratches_density": random.uniform(0.01, 0.1),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "dust":
            result["strategies"][key] = {
                "enable": True,
                "dust_density": random.uniform(0.01, 0.15),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "light_leak":
            result["strategies"][key] = {
                "enable": True,
                "light_leak_intensity": random.uniform(0.05, 0.3),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "edge_detect":
            result["strategies"][key] = {
                "enable": True,
                "edge_threshold": random.randint(10, 150),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "cartoon":
            result["strategies"][key] = {
                "enable": True,
                "cartoon_level": random.randint(1, 10),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "volume_adjust":
            result["strategies"][key] = {
                "enable": True,
                "volume_gain_db": random.uniform(VOLUME_GAIN_MIN, VOLUME_GAIN_MAX),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "compressor":
            result["strategies"][key] = {
                "enable": True,
                "enable_compressor": True,
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "reverb":
            result["strategies"][key] = {
                "enable": True,
                "enable_reverb": True,
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "bass_treble":
            result["strategies"][key] = {
                "enable": True,
                "enable_bass_treble": True,
                "bass_gain": random.uniform(BASS_GAIN_MIN, BASS_GAIN_MAX),
                "treble_gain": random.uniform(TREBLE_GAIN_MIN, TREBLE_GAIN_MAX),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "aspect_ratio":
            result["strategies"][key] = {
                "enable": True,
                "aspect_ratio": random.choice(list(ASPECT_RATIOS.keys())),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "canvas_size":
            result["strategies"][key] = {
                "enable": True,
                "canvas_size_preset": random.choice(list(CANVAS_SIZES.keys())),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "speed_curve":
            result["strategies"][key] = {
                "enable": True,
                "speed_curve": random.choice(SPEED_CURVE_PRESETS),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "target_fps":
            result["strategies"][key] = {
                "enable": True,
                "target_fps": random.choice([str(f) for f in FPS_TARGETS]),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "transition":
            result["strategies"][key] = {
                "enable": True,
                "enable_transition": True,
                "transition_type": random.choice(TRANSITION_TYPES),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "codec":
            result["strategies"][key] = {
                "enable": True,
                "output_codec": random.choice(list(VIDEO_CODECS.keys())),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "crf":
            result["strategies"][key] = {
                "enable": True,
                "output_crf": random.randint(CRF_MIN, CRF_MAX),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "color_space":
            result["strategies"][key] = {
                "enable": True,
                "color_space": random.choice(COLOR_SPACES),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "pixel_format":
            result["strategies"][key] = {
                "enable": True,
                "pixel_format": random.choice(PIXEL_FORMATS),
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        elif key == "remove_metadata":
            result["strategies"][key] = {
                "enable": True,
                "remove_metadata": True,
                "name": strategy["name"],
                "category": strategy["category"],
                "dimension": dimension
            }

        # 添加到启用列表
        result["enabled_list"].append(f"{strategy['category']} - {strategy['name']}")

    return result


def format_strategy_for_display(strategy: dict) -> str:
    """
    格式化策略组合为可读文本

    Args:
        strategy: 策略字典

    Returns:
        格式化的文本
    """
    lines = []
    lines.append(f"# {strategy['level_name']} (共{strategy['count']}项)")
    lines.append("")

    # 按维度分组显示
    dimension_names = {
        "visual": "🎨 画面维度",
        "audio": "🔊 音频维度",
        "container": "📦 容器维度",
        "content": "📝 内容维度",
        "metadata": "⚙️ 元数据维度"
    }

    for dim, strategies in DEDUPLICATION_STRATEGIES.items():
        dim_items = []
        for key in strategies.keys():
            if key in strategy["strategies"]:
                item = strategy["strategies"][key]
                dim_items.append(f"  ✅ {item['category']}: {item['name']}")

        if dim_items:
            lines.append(f"{dimension_names.get(dim, dim)}")
            lines.extend(dim_items)
            lines.append("")

    return "\n".join(lines)


def strategy_to_params(strategy: dict) -> dict:
    """
    将策略字典转换为app.py可用的参数字典

    Args:
        strategy: 策略字典

    Returns:
        参数字典
    """
    params = {}

    for key, config in strategy["strategies"].items():
        # 直接合并所有参数
        params.update(config)

        # 移除非参数字段
        params.pop("name", None)
        params.pop("category", None)
        params.pop("dimension", None)

    return params
