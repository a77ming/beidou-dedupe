"""
Video processing module for short video repurposing.
Handles picture-in-picture, effects, and output generation.
"""

import os
import sys
import random
import logging
from typing import Tuple, Optional, Callable
from pathlib import Path

import numpy as np
import cv2
from moviepy import VideoFileClip, ColorClip, CompositeVideoClip
from PIL import Image

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.config import (
    CANVAS_WIDTH, CANVAS_HEIGHT,
    VIDEO_CODEC, AUDIO_CODEC, BITRATE, X264_PRESET,
    get_random_bg_color, get_random_bg_image, get_snow_particle_count,
    get_output_filename, BG_MODE_SOLID, generate_zoom_keyframes, get_scale_at_time,
    get_random_mirror, generate_gif_stickers, generate_mirror_intervals, should_mirror_at_time,
    get_random_rotation_angle, generate_frame_drop_intervals, should_drop_frame_at_time,
    get_random_film_grain_params
)
from core.effects import (
    SnowEffect, TextOverlay, create_background, ProgressBarOverlay,
    VideoFrameEffects, StickerOverlay, BlurBarOverlay, create_rounded_mask,
    generate_random_stickers, SideTextOverlay, generate_random_side_texts,
    GIFStickerOverlay, GlassmorphismSubtitleOverlay, FilmGrain,
    GeometricTransform, ColorAdjustments, SharpnessEffects,
    TextureOverlay, EdgeEffects
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoProcessor:
    """Main video processor class for repurposing short videos."""

    def __init__(self, input_path: str):
        """
        Initialize video processor.

        Args:
            input_path: Path to the input video file
        """
        self.input_path = input_path
        self.clip: Optional[VideoFileClip] = None
        self._validate_input()

    def _validate_input(self) -> None:
        """Validate that input file exists and has supported format."""
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(f"Input video not found: {self.input_path}")

        ext = Path(self.input_path).suffix.lower()
        supported_formats = ['.mp4', '.mov', '.avi', '.mkv']
        if ext not in supported_formats:
            raise ValueError(f"Unsupported video format: {ext}. Supported: {supported_formats}")

        logger.info(f"Input video validated: {self.input_path}")

    def get_video_info(self) -> dict:
        """
        Get information about the input video.

        Returns:
            Dictionary containing video information
        """
        if self.clip is None:
            self.clip = VideoFileClip(self.input_path)

        return {
            "width": self.clip.w,
            "height": self.clip.h,
            "duration": self.clip.duration,
            "fps": self.clip.fps,
            "aspect_ratio": self.clip.w / self.clip.h if self.clip.h > 0 else 0
        }

    def _create_pip_frame(self, frame: np.ndarray, scale: Optional[float],
                          bg_color: Optional[Tuple[int, int, int]],
                          bg_image_path: Optional[str] = None,
                          video_border_width: int = 0,
                          video_border_color: Tuple[int, int, int] = (255, 255, 255),
                          corner_radius: int = 0,
                          enable_mirror: bool = False,
                          rotation_angle: float = 0.0) -> np.ndarray:
        """
        Create a picture-in-picture frame.

        Args:
            frame: Original video frame
            scale: Canvas coverage ratio for the picture-in-picture (0.75-0.90), None to disable scaling
            bg_color: Background color as RGB tuple, None to disable background
            bg_image_path: Optional path to background image
            video_border_width: Border width around video
            video_border_color: Border color
            corner_radius: Corner radius for rounded corners
            enable_mirror: Whether to mirror the video horizontally
            rotation_angle: Rotation angle in degrees (1-2 degrees recommended)

        Returns:
            Processed frame with pip effect
        """
        # If scale and bg_color are both None, return original frame (all disabled)
        if scale is None and bg_color is None:
            result = frame.copy()

            # Still apply mirror and rotation if enabled
            if enable_mirror:
                result = cv2.flip(result, 1)

            if rotation_angle != 0.0:
                h, w = result.shape[:2]
                center = (w // 2, h // 2)
                matrix = cv2.getRotationMatrix2D(center, rotation_angle, 1.0)
                result = cv2.warpAffine(result, matrix, (w, h))

            return result

        # Get frame dimensions
        original_height, original_width = frame.shape[:2]

        # Use default scale if None but bg is enabled
        if scale is None:
            scale = 0.85  # Default scale when background is enabled but no scale specified

        # Use default bg color if None but scale is enabled
        if bg_color is None:
            bg_color = (200, 224, 255)  # Default light blue background

        # Create background - use image if provided, otherwise use color
        if bg_image_path and os.path.exists(bg_image_path):
            # Load and resize background image to canvas size
            bg_image = cv2.imread(bg_image_path)
            if bg_image is not None:
                background = cv2.resize(bg_image, (CANVAS_WIDTH, CANVAS_HEIGHT))
            else:
                background = create_background(CANVAS_WIDTH, CANVAS_HEIGHT, bg_color, BG_MODE_SOLID)
                logger.warning(f"Failed to load background image: {bg_image_path}")
        else:
            background = create_background(CANVAS_WIDTH, CANVAS_HEIGHT, bg_color, BG_MODE_SOLID)

        # Calculate scaled dimensions based on canvas coverage ratio
        fit_scale = min(CANVAS_WIDTH / original_width, CANVAS_HEIGHT / original_height)
        actual_scale = fit_scale * scale
        scaled_width = int(original_width * actual_scale)
        scaled_height = int(original_height * actual_scale)

        # Resize original frame
        resized = cv2.resize(frame, (scaled_width, scaled_height))

        # Apply mirror effect if enabled (flip horizontally)
        if enable_mirror:
            resized = cv2.flip(resized, 1)  # 1 = horizontal flip

        # Apply rotation if enabled (small angle 1-2 degrees)
        if rotation_angle != 0.0:
            # Get rotation matrix
            center = (scaled_width // 2, scaled_height // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, rotation_angle, 1.0)

            # Calculate new dimensions to avoid cropping
            cos_a = abs(rotation_matrix[0, 0])
            sin_a = abs(rotation_matrix[0, 1])
            new_width = int((scaled_height * sin_a) + (scaled_width * cos_a))
            new_height = int((scaled_height * cos_a) + (scaled_width * sin_a))

            # Adjust translation
            rotation_matrix[0, 2] += (new_width / 2) - center[0]
            rotation_matrix[1, 2] += (new_height / 2) - center[1]

            # Create new canvas for rotation with extra space
            rotated_canvas = np.zeros((new_height, new_width, 3), dtype=np.uint8)
            resized = cv2.warpAffine(resized, rotation_matrix, (new_width, new_height),
                                    borderMode=cv2.BORDER_CONSTANT, borderValue=bg_color)
            scaled_width = new_width
            scaled_height = new_height

        # Calculate center position
        x_offset = (CANVAS_WIDTH - scaled_width) // 2
        y_offset = (CANVAS_HEIGHT - scaled_height) // 2

        # Apply rounded corners if requested
        if corner_radius > 0:
            # Create rounded mask
            mask = create_rounded_mask(scaled_width, scaled_height, corner_radius)
            # Resize mask to match resized frame
            resized_mask = cv2.resize(mask, (scaled_width, scaled_height))
            # Apply mask to create rounded corners
            resized = cv2.bitwise_and(resized, resized, mask=resized_mask)

        # Draw border if requested (around the video)
        if video_border_width > 0:
            # Create border rectangle
            border_x1 = x_offset - video_border_width
            border_y1 = y_offset - video_border_width
            border_x2 = x_offset + scaled_width + video_border_width
            border_y2 = y_offset + scaled_height + video_border_width

            # Draw filled border rectangle
            cv2.rectangle(background,
                         (border_x1, border_y1),
                         (border_x2, border_y2),
                         video_border_color, -1)

        # Place resized frame on background
        background[y_offset:y_offset + scaled_height,
                   x_offset:x_offset + scaled_width] = resized

        return background

    def _process_frame(self, frame: np.ndarray, scale: float,
                       bg_color: Tuple[int, int, int],
                       snow_effect: Optional[SnowEffect],
                       text_overlay: TextOverlay,
                       bg_image_path: Optional[str] = None,
                       progress_bar: Optional[ProgressBarOverlay] = None,
                       video_progress: float = 0.0,
                       video_border_width: int = 0,
                       video_border_color: Tuple[int, int, int] = (255, 255, 255),
                       corner_radius: int = 0,
                       video_frame_effects: Optional[VideoFrameEffects] = None,
                       stickers: list = None,
                       sticker_overlay: Optional[StickerOverlay] = None,
                       blur_bar: Optional[BlurBarOverlay] = None,
                       side_text: Optional[SideTextOverlay] = None,
                       frame_index: int = 0,
                       enable_mirror: bool = False,
                       rotation_angle: float = 0.0,
                       gif_sticker_overlay: Optional['GIFStickerOverlay'] = None,
                       video_fps: float = 30.0,
                       glass_subtitle_overlay: Optional['GlassmorphismSubtitleOverlay'] = None,
                       current_time: float = 0.0,
                       film_grain: Optional[FilmGrain] = None,
                       # Advanced deduplication parameters
                       geometric_transform: Optional['GeometricTransform'] = None,
                       color_adjustments: Optional['ColorAdjustments'] = None,
                       sharpness_effects: Optional['SharpnessEffects'] = None,
                       texture_overlay: Optional['TextureOverlay'] = None,
                       edge_effects: Optional['EdgeEffects'] = None) -> np.ndarray:
        """
        Process a single frame with all effects.

        Args:
            frame: Original frame
            scale: Scale factor for pip
            bg_color: Background color
            snow_effect: Optional snow effect instance
            text_overlay: Text overlay instance
            bg_image_path: Optional background image path
            progress_bar: Optional progress bar overlay
            video_progress: Progress value 0.0-1.0 for video progress bar
            video_border_width: Border width around video
            video_border_color: Border color
            corner_radius: Corner radius for rounded corners
            video_frame_effects: Optional video frame effects (filters)
            stickers: List of stickers to overlay
            blur_bar: Optional blur bar overlay
            side_text: Optional side text overlay
            frame_index: Current frame index for sticker animation
            enable_mirror: Whether to mirror the video horizontally
            rotation_angle: Rotation angle in degrees
            gif_sticker_overlay: Optional GIF sticker overlay
            video_fps: Video FPS for GIF animation timing
            glass_subtitle_overlay: Optional glassmorphism subtitle overlay
            current_time: Current video time in seconds
            film_grain: Optional film grain effect to apply
            geometric_transform: Optional geometric transform effects
            color_adjustments: Optional color adjustment effects
            sharpness_effects: Optional sharpness effects
            texture_overlay: Optional texture overlay effects
            edge_effects: Optional edge detection effects

        Returns:
            Processed frame
        """
        # Create pip frame with border and rounded corners
        processed = self._create_pip_frame(
            frame, scale, bg_color, bg_image_path,
            video_border_width, video_border_color, corner_radius,
            enable_mirror, rotation_angle
        )

        # Apply snow effect if enabled
        if snow_effect:
            processed = snow_effect.apply_to_frame(processed)

        # Apply video frame effects (filters)
        if video_frame_effects:
            processed = video_frame_effects.apply_frame_effects(processed)

        # Apply text overlay
        if text_overlay:
            processed = text_overlay.apply_to_frame(processed)

        # Apply stickers if enabled
        if stickers and sticker_overlay:
            processed = sticker_overlay.apply_to_frame(processed, stickers, frame_index)

        # Apply blur bar if enabled (to cover subtitles)
        if blur_bar:
            processed = blur_bar.apply_to_frame(processed)

        # Apply side text if enabled (left and right vertical text)
        if side_text:
            processed = side_text.apply_to_frame(processed)

        # Apply GIF stickers if enabled
        if gif_sticker_overlay:
            processed = gif_sticker_overlay.apply_to_frame(
                processed, frame_index, video_fps
            )

        # Apply video progress bar if enabled
        if progress_bar:
            processed = progress_bar.apply_to_frame(processed, video_progress)

        # Apply glassmorphism subtitle overlay if enabled
        if glass_subtitle_overlay:
            processed = glass_subtitle_overlay.apply_to_frame(processed, current_time)

        # ============== Apply Advanced Deduplication Effects ==============

        # Apply geometric transforms (crop, perspective, displacement)
        if geometric_transform:
            processed = geometric_transform.apply_to_frame(processed, frame_index)

        # Apply color adjustments (brightness, saturation, hue, gamma, LUT filters)
        if color_adjustments:
            processed = color_adjustments.apply_to_frame(processed)

        # Apply sharpness effects (blur, sharpen, denoise)
        if sharpness_effects:
            processed = sharpness_effects.apply_to_frame(processed)

        # Apply texture overlay (scratches, dust, light leak)
        if texture_overlay:
            processed = texture_overlay.apply_to_frame(processed)

        # Apply edge effects (edge detection, cartoon)
        if edge_effects:
            processed = edge_effects.apply_to_frame(processed)

        # Apply film grain if enabled (breaks color histograms)
        if film_grain:
            processed = film_grain.apply_to_frame(processed)

        return processed

    def _frame_generator(self, clip: VideoFileClip, scale: float,
                         bg_color: Tuple[int, int, int],
                         enable_snow: bool,
                         text_overlay: TextOverlay,
                         bg_image_path: Optional[str] = None):
        """
        Generator function to process frames.

        Args:
            clip: VideoFileClip to process
            scale: Scale factor for pip
            bg_color: Background color
            enable_snow: Whether to enable snow effect
            text_overlay: Text overlay instance
            bg_image_path: Optional background image path

        Yields:
            Processed frames as numpy arrays
        """
        # Initialize snow effect
        snow_effect = None
        if enable_snow:
            particle_count = get_snow_particle_count()
            snow_effect = SnowEffect(CANVAS_WIDTH, CANVAS_HEIGHT, particle_count)
            logger.info(f"Enabled snow effect with {particle_count} particles")

        for frame in clip.iter_frames(progress_bar=True):
            yield self._process_frame(
                frame, scale, bg_color, snow_effect, text_overlay, bg_image_path,
                stickers=None, sticker_overlay=None
            )

    def process_single(self, output_path: str,
                       scale: Optional[float] = None,
                       speed: Optional[float] = None,
                       enable_snow: bool = False,
                       bg_color: Optional[Tuple[int, int, int]] = None,
                       bg_image_path: Optional[str] = None,
                       enable_video_progress_bar: bool = False,
                       video_progress_bar_character: str = "santa",
                       video_border_width: int = 0,
                       video_border_color: Tuple[int, int, int] = (255, 255, 255),
                       corner_radius: int = 0,
                       enable_warmth: bool = False,
                       warmth_value: int = 5,
                       enable_contrast: bool = False,
                       contrast_value: float = -3.0,
                       enable_stickers: bool = False,
                       enable_blur_bar: bool = False,
                       blur_bar_height: int = 150,
                       enable_side_text: bool = False,
                       side_left_texts: list = None,
                       side_right_texts: list = None,
                       enable_dynamic_zoom: bool = False,
                       zoom_keyframes: Optional[list] = None,
                       mirror_mode: str = "off",  # "off", "on", "random"
                       rotation_mode: str = "off",  # "off", "on", "random"
                       frame_drop_mode: str = "off",  # "off", "on", "random"
                       film_grain_mode: str = "off",  # "off", "on", "random"
                       enable_gif_stickers: bool = False,
                       # Glassmorphism subtitle settings
                       enable_glass_subtitle: bool = False,
                       subtitles: list = None,
                       glass_bar_height: int = 200,
                       glass_bar_opacity: int = 180,
                       glass_blur_amount: int = 30,
                       glass_corner_radius: int = 30,
                       glass_text_color: Tuple[int, int, int] = (0, 0, 0),
                       glass_text_size: int = 36,
                       # ============== Advanced Deduplication Parameters ==============
                       # Geometric transforms
                       enable_crop: bool = False,
                       crop_params: dict = None,
                       enable_perspective: bool = False,
                       perspective_params: list = None,
                       enable_displacement: bool = False,
                       displacement_params: dict = None,
                       # Color adjustments
                       enable_brightness: bool = False,
                       brightness_value: float = 0.0,
                       enable_saturation: bool = False,
                       saturation_value: float = 1.0,
                       enable_hue_shift: bool = False,
                       hue_shift_value: float = 0.0,
                       enable_gamma: bool = False,
                       gamma_value: float = 1.0,
                       lut_filter: str = None,
                       # Sharpness effects
                       enable_gaussian_blur: bool = False,
                       gaussian_blur_value: float = 0.0,
                       enable_sharpen: bool = False,
                       sharpen_strength: float = 1.5,
                       enable_denoise: bool = False,
                       denoise_strength: int = 5,
                       # Texture effects
                       enable_scratches: bool = False,
                       scratches_density: float = 0.02,
                       enable_dust: bool = False,
                       dust_density: float = 0.05,
                       enable_light_leak: bool = False,
                       light_leak_intensity: float = 0.1,
                       # Edge effects
                       enable_edge_detect: bool = False,
                       edge_threshold: int = 50,
                       enable_cartoon: bool = False,
                       cartoon_level: int = 5,
                       # Audio effects
                       enable_volume_adjust: bool = False,
                       volume_gain_db: float = 0.0,
                       enable_compressor: bool = False,
                       enable_reverb: bool = False,
                       enable_bass_treble: bool = False,
                       bass_gain: float = 0.0,
                       treble_gain: float = 0.0,
                       # Encoding settings
                       output_codec: str = "h264",
                       output_quality: str = "medium",
                       output_crf: int = 23,
                       output_preset: str = "medium",
                       color_space: str = "bt709",
                       pixel_format: str = "yuv420p",
                       remove_metadata: bool = False,
                       # Preview settings
                       preview_duration: Optional[float] = None,
                       progress_callback: Optional[Callable] = None,
                       keep_open: bool = False) -> dict:
        """
        Process a single video with specified parameters.

        Args:
            output_path: Path for output video
            scale: Canvas coverage ratio for pip (0.75-0.90) - ignored if dynamic_zoom enabled
            speed: Speed factor (1.0-1.5)
            enable_snow: Whether to enable snow effect
            bg_color: Background color
            bg_image_path: Optional path to background image
            enable_video_progress_bar: Whether to add video progress bar overlay
            video_progress_bar_character: Character for progress bar ("santa" or "pikachu")
            video_border_width: Border width around video
            video_border_color: Border color
            corner_radius: Corner radius for rounded video corners
            enable_warmth: Enable warmth filter
            warmth_value: Warmth adjustment (-20 to 20)
            enable_contrast: Enable contrast filter
            contrast_value: Contrast adjustment (-10 to 10)
            enable_stickers: Enable sticker overlays
            enable_blur_bar: Enable blur bar to cover subtitles
            blur_bar_height: Height of blur bar
            enable_side_text: Enable side text overlay (left/right vertical text)
            side_left_texts: Custom left side texts (list of strings)
            side_right_texts: Custom right side texts (list of strings)
            enable_dynamic_zoom: Enable dynamic zoom effect (scale changes over time)
            zoom_keyframes: Optional list of (time, scale) tuples for zoom keyframes
            mirror_mode: Mirror mode - "off", "on", or "random"
            rotation_mode: Rotation mode - "off", "on", or "random" (applies small 1-2 degree rotation)
            frame_drop_mode: Frame drop mode - "off", "on", or "random" (randomly drops 1-2 frames every 2-4 seconds)
            film_grain_mode: Film grain mode - "off", "on", or "random" (adds film noise to break color histograms)
            enable_gif_stickers: Enable GIF sticker overlays
            enable_glass_subtitle: Enable glassmorphism subtitle overlay
            subtitles: List of subtitle dictionaries
            glass_bar_height: Height of the glass bar
            glass_bar_opacity: Opacity of the glass bar (0-255)
            glass_blur_amount: Blur amount for the glass effect
            glass_corner_radius: Corner radius for the glass bar
            glass_text_color: Text color for subtitles
            glass_text_size: Font size for subtitles
            # Advanced deduplication parameters
            enable_crop: Enable crop effect
            crop_params: Crop parameters dict
            enable_perspective: Enable perspective transform
            perspective_params: Perspective transform points
            enable_displacement: Enable displacement (shake/slide)
            displacement_params: Displacement parameters dict
            enable_brightness: Enable brightness adjustment
            brightness_value: Brightness value (-0.1 to 0.1)
            enable_saturation: Enable saturation adjustment
            saturation_value: Saturation multiplier (0.9 to 1.15)
            enable_hue_shift: Enable hue shift
            hue_shift_value: Hue shift in degrees (-10 to 10)
            enable_gamma: Enable gamma correction
            gamma_value: Gamma value (0.9 to 1.1)
            lut_filter: LUT filter name (vintage, cool, warm, bw, sepia, negate)
            enable_gaussian_blur: Enable Gaussian blur
            gaussian_blur_value: Blur kernel size (0.1 to 1.0)
            enable_sharpen: Enable sharpening
            sharpen_strength: Sharpening strength (1.0 to 3.0)
            enable_denoise: Enable denoising
            denoise_strength: Denoising strength (1 to 10)
            enable_scratches: Enable scratch texture
            scratches_density: Scratch density (0.0 to 1.0)
            enable_dust: Enable dust texture
            dust_density: Dust density (0.0 to 1.0)
            enable_light_leak: Enable light leak effect
            light_leak_intensity: Light leak intensity (0.0 to 1.0)
            enable_edge_detect: Enable edge detection
            edge_threshold: Edge detection threshold (0 to 255)
            enable_cartoon: Enable cartoon effect
            cartoon_level: Cartoon effect level (1 to 10)
            enable_volume_adjust: Enable volume adjustment
            volume_gain_db: Volume gain in dB (-3 to 3)
            enable_compressor: Enable audio compressor
            enable_reverb: Enable reverb effect
            enable_bass_treble: Enable bass/treble adjustment
            bass_gain: Bass gain in dB (-10 to 10)
            treble_gain: Treble gain in dB (-10 to 10)
            output_codec: Output video codec (h264, h265, vp9, av1)
            output_quality: Output quality preset (low, medium, high, ultra)
            output_crf: Output CRF value (18 to 28)
            output_preset: Encoding preset (veryslow, slow, medium, fast, veryfast)
            color_space: Color space (bt709, bt2020, bt601)
            pixel_format: Pixel format (yuv420p, yuv422p, yuv444p)
            remove_metadata: Whether to remove metadata from output
            preview_duration: If set, only process this many seconds (for preview)
            progress_callback: Optional callback for progress updates
            keep_open: If True, keep clip open for reuse (for batch processing)

        Returns:
            Dictionary with processing results
        """
        # Load video clip
        if self.clip is None:
            self.clip = VideoFileClip(self.input_path)

        # Get video info
        info = self.get_video_info()
        logger.info(f"Processing video: {info['width']}x{info['height']}, {info['duration']:.2f}s")

        # Check if all basic effects are disabled (for advanced deduplication only mode)
        # IMPORTANT: This check must happen BEFORE any random values are generated!
        basic_effects_disabled = (
            scale is None and
            (speed is None or speed == 1.0) and
            bg_color is None and
            bg_image_path is None and
            not enable_snow and
            not enable_video_progress_bar and
            video_border_width == 0 and
            corner_radius == 0 and
            not enable_warmth and
            not enable_contrast and
            not enable_stickers and
            not enable_blur_bar and
            not enable_side_text and
            not enable_gif_stickers and
            not enable_glass_subtitle and
            mirror_mode == "off" and
            rotation_mode == "off" and
            frame_drop_mode == "off" and
            film_grain_mode == "off"
        )

        if basic_effects_disabled:
            logger.info("Basic effects disabled - only advanced deduplication will be applied")
            # Set minimal defaults - no background, no scaling, no text
            final_bg_image_path = None
            final_bg_color = None
            text_overlay = None
            # Keep scale as None to avoid canvas resizing
            final_scale = None
        else:
            # Apply random values if not specified (legacy behavior)
            from config import get_random_scale, get_random_bg_color, get_random_bg_image

            # Set scale if not specified
            if scale is None:
                scale = get_random_scale()
            final_scale = scale

            # Set background color if not specified
            if bg_color is None:
                bg_color = get_random_bg_color()
            final_bg_color = bg_color

            # Get random bg image if bg_image_path is not provided
            final_bg_image_path = bg_image_path
            if final_bg_image_path is None:
                final_bg_image_path = get_random_bg_image()

            if final_bg_image_path:
                logger.info(f"Using background image: {final_bg_image_path}")

            # Initialize text overlay
            text_overlay = TextOverlay()

        # Initialize video progress bar if enabled
        final_progress_bar = None
        if enable_video_progress_bar:
            final_progress_bar = ProgressBarOverlay(
                CANVAS_WIDTH, CANVAS_HEIGHT,
                character=video_progress_bar_character
            )
            logger.info(f"Enabled video progress bar with {video_progress_bar_character} character")

        # Initialize video frame effects (filters)
        final_frame_effects = None
        if enable_warmth or enable_contrast:
            final_frame_effects = VideoFrameEffects(
                CANVAS_WIDTH, CANVAS_HEIGHT,
                enable_warmth=enable_warmth,
                warmth_value=warmth_value,
                enable_contrast=enable_contrast,
                contrast_value=contrast_value
            )
            logger.info(f"Enabled frame effects: warmth={enable_warmth}, contrast={enable_contrast}")

        # Initialize stickers if enabled
        final_stickers = None
        final_sticker_overlay = None
        if enable_stickers:
            # Generate random stickers aligned to the main video area
            final_stickers = generate_random_stickers(
                CANVAS_WIDTH, CANVAS_HEIGHT, count=10, video_scale=scale
            )
            final_sticker_overlay = StickerOverlay(CANVAS_WIDTH, CANVAS_HEIGHT)
            logger.info(f"Enabled stickers: {len(final_stickers)} random stickers generated")

        # Initialize blur bar if enabled
        final_blur_bar = None
        if enable_blur_bar:
            final_blur_bar = BlurBarOverlay(
                CANVAS_WIDTH, CANVAS_HEIGHT,
                bar_height=blur_bar_height
            )
            logger.info(f"Enabled blur bar with height {blur_bar_height}")

        # Initialize side text if enabled
        final_side_text = None
        if enable_side_text:
            # Use custom texts if provided, otherwise generate random
            left_texts = side_left_texts if side_left_texts else []
            right_texts = side_right_texts if side_right_texts else []

            if not left_texts and not right_texts:
                left_texts, right_texts = generate_random_side_texts()

            final_side_text = SideTextOverlay(
                CANVAS_WIDTH, CANVAS_HEIGHT,
                left_texts=left_texts,
                right_texts=right_texts,
                video_scale=scale
            )
            logger.info(f"Enabled side text: left={len(left_texts)}, right={len(right_texts)}")

        # Save video duration for progress calculation
        video_duration = info['duration']

        # Save original get_frame for use in closure
        original_get_frame = self.clip.get_frame

        # Initialize snow effect once to avoid per-frame allocation
        final_snow_effect = None
        if enable_snow:
            final_snow_effect = SnowEffect(
                CANVAS_WIDTH, CANVAS_HEIGHT, get_snow_particle_count()
            )

        # Initialize dynamic zoom keyframes
        final_zoom_keyframes = None
        if enable_dynamic_zoom:
            if zoom_keyframes is None:
                from config import SCALE_MIN, SCALE_MAX
                final_zoom_keyframes = generate_zoom_keyframes(
                    duration=video_duration,
                    scale_min=SCALE_MIN,
                    scale_max=SCALE_MAX
                )
            else:
                final_zoom_keyframes = zoom_keyframes
            logger.info(f"Enabled dynamic zoom with {len(final_zoom_keyframes)} keyframes")

        # Determine mirror setting based on mirror_mode
        final_mirror_intervals = None
        final_mirror_mode = mirror_mode
        if mirror_mode == "on":
            # Always mirror - create intervals covering entire video
            final_mirror_intervals = [(0, video_duration, True)]
            logger.info("Mirror effect: always enabled")
        elif mirror_mode == "random":
            # Generate random mirror intervals (2-5 seconds each)
            final_mirror_intervals = generate_mirror_intervals(video_duration, min_interval=2.0, max_interval=5.0)
            mirrored_count = sum(1 for _, _, is_mirrored in final_mirror_intervals if is_mirrored)
            logger.info(f"Mirror effect (random): {mirrored_count}/{len(final_mirror_intervals)} intervals mirrored")
        else:
            # Off - create intervals with no mirroring
            final_mirror_intervals = [(0, video_duration, False)]
            logger.info("Mirror effect: disabled")

        # Determine rotation setting based on rotation_mode
        final_rotation_angle = 0.0
        final_rotation_mode = rotation_mode
        if rotation_mode == "on":
            # Always apply rotation - use random angle between 1-2 degrees
            final_rotation_angle = get_random_rotation_angle()
            if final_rotation_angle > 0:
                final_rotation_angle = final_rotation_angle if random.random() > 0.5 else -final_rotation_angle
            logger.info(f"Rotation effect: enabled ({abs(final_rotation_angle):.2f}°)")
        elif rotation_mode == "random":
            # Randomly decide if rotation should be applied
            if random.choice([True, False]):
                final_rotation_angle = get_random_rotation_angle()
                final_rotation_angle = final_rotation_angle if random.random() > 0.5 else -final_rotation_angle
                logger.info(f"Rotation effect (random): enabled ({abs(final_rotation_angle):.2f}°)")
            else:
                logger.info("Rotation effect (random): disabled")
        else:
            logger.info("Rotation effect: disabled")

        # Determine frame drop intervals based on frame_drop_mode
        final_frame_drop_intervals = None
        final_frame_drop_mode = frame_drop_mode
        if frame_drop_mode == "on":
            # Always apply frame dropping
            final_frame_drop_intervals = generate_frame_drop_intervals(video_duration)
            total_drops = sum(len(info['drop_frames']) for info in final_frame_drop_intervals.values())
            logger.info(f"Frame drop effect: enabled (will drop {total_drops} frames)")
        elif frame_drop_mode == "random":
            # Randomly decide if frame dropping should be applied
            if random.choice([True, False]):
                final_frame_drop_intervals = generate_frame_drop_intervals(video_duration)
                total_drops = sum(len(info['drop_frames']) for info in final_frame_drop_intervals.values())
                logger.info(f"Frame drop effect (random): enabled (will drop {total_drops} frames)")
            else:
                logger.info("Frame drop effect (random): disabled")
        else:
            logger.info("Frame drop effect: disabled")

        # Determine film grain settings based on film_grain_mode
        final_film_grain = None
        final_film_grain_mode = film_grain_mode
        if film_grain_mode == "on":
            # Always apply film grain
            intensity, color = get_random_film_grain_params()
            final_film_grain = FilmGrain(CANVAS_WIDTH, CANVAS_HEIGHT, intensity, color)
            logger.info(f"Film grain effect: enabled (intensity={intensity:.3f}, color={color})")
        elif film_grain_mode == "random":
            # Randomly decide if film grain should be applied
            if random.choice([True, False]):
                intensity, color = get_random_film_grain_params()
                final_film_grain = FilmGrain(CANVAS_WIDTH, CANVAS_HEIGHT, intensity, color)
                logger.info(f"Film grain effect (random): enabled (intensity={intensity:.3f}, color={color})")
            else:
                logger.info("Film grain effect (random): disabled")
        else:
            logger.info("Film grain effect: disabled")

        # Initialize GIF stickers
        final_gif_sticker_overlay = None
        if enable_gif_stickers:
            gif_stickers = generate_gif_stickers(CANVAS_WIDTH, CANVAS_HEIGHT)
            if gif_stickers:
                final_gif_sticker_overlay = GIFStickerOverlay(
                    CANVAS_WIDTH, CANVAS_HEIGHT, gif_stickers
                )
                logger.info(f"Enabled GIF stickers: {len(gif_stickers)} stickers")

        # Initialize glassmorphism subtitle overlay
        final_glass_subtitle_overlay = None
        if enable_glass_subtitle and subtitles:
            # Get the actual scale being used (dynamic or fixed)
            final_scale = scale
            if enable_dynamic_zoom and final_zoom_keyframes:
                # Use average scale for positioning
                final_scale = sum(s for _, s in final_zoom_keyframes) / len(final_zoom_keyframes)

            final_glass_subtitle_overlay = GlassmorphismSubtitleOverlay(
                CANVAS_WIDTH, CANVAS_HEIGHT,
                subtitles=subtitles,
                bar_height=glass_bar_height,
                bar_opacity=glass_bar_opacity,
                blur_amount=glass_blur_amount,
                corner_radius=glass_corner_radius,
                text_color=glass_text_color,
                text_size=glass_text_size,
                video_scale=final_scale
            )
            logger.info(f"Enabled glassmorphism subtitle overlay with {len(subtitles)} subtitles (scale={final_scale:.2f})")

        # ============== Initialize Advanced Deduplication Effects ==============

        # Initialize geometric transform effects
        final_geometric_transform = None
        if enable_crop or enable_perspective or enable_displacement:
            final_geometric_transform = GeometricTransform(
                crop_params=crop_params if enable_crop else None,
                perspective_params=perspective_params if enable_perspective else None,
                displacement_params=displacement_params if enable_displacement else None
            )
            if enable_crop:
                logger.info(f"Enabled crop effect: {crop_params.get('type', 'unknown')}")
            if enable_perspective:
                logger.info("Enabled perspective transform")
            if enable_displacement:
                logger.info(f"Enabled displacement: {displacement_params.get('type', 'unknown')}")

        # Initialize color adjustments
        final_color_adjustments = None
        if (enable_brightness or enable_saturation or enable_hue_shift or
            enable_gamma or lut_filter):
            # Use existing warmth/contrast if enabled, otherwise use defaults
            final_color_adjustments = ColorAdjustments(
                brightness=brightness_value if enable_brightness else 0.0,
                contrast=contrast_value if enable_contrast else 1.0,
                saturation=saturation_value if enable_saturation else 1.0,
                hue_shift=hue_shift_value if enable_hue_shift else 0.0,
                gamma=gamma_value if enable_gamma else 1.0,
                lut_filter=lut_filter
            )
            logger.info("Enabled color adjustments")
            if enable_brightness:
                logger.info(f"  Brightness: {brightness_value:.2f}")
            if enable_saturation:
                logger.info(f"  Saturation: {saturation_value:.2f}x")
            if enable_hue_shift:
                logger.info(f"  Hue shift: {hue_shift_value:.1f}°")
            if enable_gamma:
                logger.info(f"  Gamma: {gamma_value:.2f}")
            if lut_filter:
                logger.info(f"  LUT filter: {lut_filter}")

        # Initialize sharpness effects
        final_sharpness_effects = None
        if enable_gaussian_blur or enable_sharpen or enable_denoise:
            final_sharpness_effects = SharpnessEffects(
                gaussian_blur=gaussian_blur_value if enable_gaussian_blur else 0.0,
                sharpen_strength=sharpen_strength if enable_sharpen else 0.0,
                denoise_strength=denoise_strength if enable_denoise else 0
            )
            logger.info("Enabled sharpness effects")
            if enable_gaussian_blur:
                logger.info(f"  Gaussian blur: {gaussian_blur_value:.2f}")
            if enable_sharpen:
                logger.info(f"  Sharpen: {sharpen_strength:.2f}x")
            if enable_denoise:
                logger.info(f"  Denoise: {denoise_strength}")

        # Initialize texture overlay
        final_texture_overlay = None
        if enable_scratches or enable_dust or enable_light_leak:
            final_texture_overlay = TextureOverlay(
                scratch_density=scratches_density if enable_scratches else 0.0,
                dust_density=dust_density if enable_dust else 0.0,
                leak_intensity=light_leak_intensity if enable_light_leak else 0.0
            )
            logger.info("Enabled texture effects")
            if enable_scratches:
                logger.info(f"  Scratches: {scratches_density:.3f}")
            if enable_dust:
                logger.info(f"  Dust: {dust_density:.3f}")
            if enable_light_leak:
                logger.info(f"  Light leak: {light_leak_intensity:.3f}")

        # Initialize edge effects
        final_edge_effects = None
        if enable_edge_detect or enable_cartoon:
            final_edge_effects = EdgeEffects(
                edge_threshold=edge_threshold,
                cartoon_level=cartoon_level,
                enable_edges=enable_edge_detect,
                enable_cartoon=enable_cartoon
            )
            logger.info("Enabled edge effects")
            if enable_edge_detect:
                logger.info(f"  Edge detection (threshold: {edge_threshold})")
            if enable_cartoon:
                logger.info(f"  Cartoon effect (level: {cartoon_level})")

        # Get FPS for GIF animation
        video_fps = info['fps']

        # Frame counter for sticker animation
        frame_counter = [0]
        # Cache for previous processed frame (for frame dropping)
        prev_processed_frame = [None]

        # Apply speed change and frame transformation
        def make_processed_frame(t):
            """Generate processed frame at time t."""
            nonlocal frame_counter, prev_processed_frame

            # Check if frames should be dropped at current time
            should_drop = should_drop_frame_at_time(final_frame_drop_intervals, t, video_fps) if final_frame_drop_intervals else False

            # If we should drop this frame, return the previous frame
            if should_drop and prev_processed_frame[0] is not None:
                # Increment frame counter even when dropping
                frame_counter[0] += 1
                return prev_processed_frame[0]

            # Get frame from the original clip
            frame = original_get_frame(t)

            # Calculate video progress (0.0 to 1.0)
            video_progress = t / video_duration if video_duration > 0 else 0.0

            # Get current frame index for animation
            current_frame_index = frame_counter[0]
            frame_counter[0] += 1

            # Calculate current scale - use dynamic zoom if enabled
            if enable_dynamic_zoom and final_zoom_keyframes:
                current_scale = get_scale_at_time(final_zoom_keyframes, t)
            else:
                current_scale = final_scale

            # Determine if mirror should be enabled at current time
            current_enable_mirror = should_mirror_at_time(final_mirror_intervals, t)

            # Process the frame
            processed = self._process_frame(
                frame, current_scale, final_bg_color,
                final_snow_effect,
                text_overlay, final_bg_image_path,
                final_progress_bar, video_progress,
                video_border_width, video_border_color, corner_radius,
                final_frame_effects, final_stickers, final_sticker_overlay,
                final_blur_bar, final_side_text, current_frame_index,
                current_enable_mirror,  # Use time-based mirror decision
                final_rotation_angle,  # Use rotation angle
                final_gif_sticker_overlay,
                video_fps,
                final_glass_subtitle_overlay,
                t,
                final_film_grain,  # Apply film grain
                # Advanced deduplication effects
                final_geometric_transform,
                final_color_adjustments,
                final_sharpness_effects,
                final_texture_overlay,
                final_edge_effects
            )

            # Cache the processed frame for potential frame dropping
            prev_processed_frame[0] = processed

            return processed

        # Create processed clip with updated frame function
        processed_clip = self.clip.with_updated_frame_function(make_processed_frame)

        # Attach audio before speed change to keep A/V in sync
        if self.clip.audio:
            processed_clip = processed_clip.with_audio(self.clip.audio)

        # Apply speed change if needed
        if speed and speed != 1.0:
            processed_clip = processed_clip.with_speed_scaled(speed)
            logger.info(f"Applied speed factor: {speed}x")
            if self.clip.audio:
                processed_clip = processed_clip.with_audio(
                    self.clip.audio.with_speed_scaled(speed)
                )

        # Set fps
        processed_clip = processed_clip.with_fps(info['fps'])

        # Write output video
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        logger.info(f"Writing output to: {output_path}")

        # Determine output duration (use preview_duration if set, otherwise full video)
        # In moviepy 2.x, we need to use subclipped() instead of duration parameter
        if preview_duration and preview_duration > 0:
            output_duration = min(preview_duration, video_duration)
            logger.info(f"Preview mode: limiting output to {output_duration:.2f} seconds")
            processed_clip = processed_clip.subclipped(0, output_duration)

        processed_clip.write_videofile(
            output_path,
            codec=VIDEO_CODEC,
            audio_codec=AUDIO_CODEC,
            bitrate=BITRATE,
            fps=info['fps'],
            ffmpeg_params=["-preset", X264_PRESET],
            logger=None  # Disable moviepy's logger
        )

        # Clean up - only close if not keeping open for batch processing
        if not keep_open:
            self.clip.close()
            self.clip = None

        result = {
            "input_path": self.input_path,
            "output_path": output_path,
            "scale": scale,
            "speed": speed,
            "bg_color": bg_color,
            "bg_image": final_bg_image_path,
            "snow_enabled": enable_snow,
            "video_progress_bar_enabled": enable_video_progress_bar,
            "video_progress_bar_character": video_progress_bar_character if enable_video_progress_bar else None,
            "video_border_width": video_border_width,
            "corner_radius": corner_radius,
            "filters_enabled": enable_warmth or enable_contrast,
            "stickers_enabled": enable_stickers,
            "blur_bar_enabled": enable_blur_bar,
            "side_text_enabled": enable_side_text,
            "dynamic_zoom_enabled": enable_dynamic_zoom,
            "zoom_keyframes": final_zoom_keyframes,
            "mirror_mode": mirror_mode,
            "mirror_intervals": final_mirror_intervals,
            "rotation_mode": rotation_mode,
            "rotation_angle": final_rotation_angle,
            "frame_drop_mode": frame_drop_mode,
            "frame_drop_intervals": final_frame_drop_intervals,
            "film_grain_mode": film_grain_mode,
            "film_grain_enabled": final_film_grain is not None,
            "gif_stickers_enabled": enable_gif_stickers,
            "glass_subtitle_enabled": enable_glass_subtitle,
            "subtitle_count": len(subtitles) if subtitles else 0,
            "canvas_size": (CANVAS_WIDTH, CANVAS_HEIGHT)
        }

        if progress_callback:
            progress_callback(100, result)

        logger.info(f"Processing complete: {output_path}")
        return result

    def process_batch(self, output_dir: str, count: int,
                      scale_range: Optional[Tuple[float, float]] = None,
                      speed_range: Optional[Tuple[float, float]] = None,
                      enable_snow: bool = False) -> list:
        """
        Process video with multiple random variations.

        Args:
            output_dir: Directory for output files
            count: Number of versions to generate
            scale_range: Optional (min, max) for random scale
            speed_range: Optional (min, max) for random speed
            enable_snow: Whether to enable snow effect

        Returns:
            List of processing results for each version
        """
        from config import get_random_scale, get_random_speed

        results = []

        for i in range(1, count + 1):
            # Generate random parameters
            scale = get_random_scale() if scale_range is None else \
                random.uniform(*scale_range)
            speed = get_random_speed() if speed_range is None else \
                random.uniform(*speed_range)
            bg_color = get_random_bg_color()

            # Generate output path
            output_path = get_output_filename(self.input_path, i, output_dir)

            logger.info(f"Processing version {i}/{count}")
            logger.info(f"  Scale: {scale:.2f}, Speed: {speed:.2f}, BG: {bg_color}")

            # Keep clip open for all iterations except the last
            keep_open = (i < count)

            result = self.process_single(
                output_path=output_path,
                scale=scale,
                speed=speed,
                enable_snow=enable_snow,
                bg_color=bg_color,
                keep_open=keep_open
            )

            results.append(result)

        logger.info(f"Batch processing complete: {len(results)} versions generated")
        return results

    def close(self) -> None:
        """Clean up resources."""
        if self.clip:
            self.clip.close()
            self.clip = None


def process_video(input_path: str, output_path: str,
                  scale: float = None, speed: float = 1.2,
                  enable_snow: bool = False,
                  bg_color: tuple = None) -> dict:
    """
    Convenience function to process a single video.

    Args:
        input_path: Path to input video
        output_path: Path for output video
        scale: Scale factor for pip
        speed: Speed factor
        enable_snow: Enable snow effect
        bg_color: Background color

    Returns:
        Processing result dictionary
    """
    processor = VideoProcessor(input_path)
    try:
        return processor.process_single(
            output_path=output_path,
            scale=scale,
            speed=speed,
            enable_snow=enable_snow,
            bg_color=bg_color
        )
    finally:
        processor.close()


def batch_process(input_path: str, output_dir: str,
                  count: int = 3,
                  enable_snow: bool = False) -> list:
    """
    Convenience function to batch process a video.

    Args:
        input_path: Path to input video
        output_dir: Directory for output files
        count: Number of versions to generate
        enable_snow: Enable snow effect

    Returns:
        List of processing result dictionaries
    """
    processor = VideoProcessor(input_path)
    try:
        return processor.process_batch(
            output_dir=output_dir,
            count=count,
            enable_snow=enable_snow
        )
    finally:
        processor.close()
