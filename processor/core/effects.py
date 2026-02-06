"""
Effects module for video processing.
Contains visual effects like snow particles, text overlays, etc.
"""

import os
import sys
import random
import logging
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from typing import List, Tuple, Optional, Dict

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logger = logging.getLogger(__name__)
from core.config import (
    CANVAS_WIDTH, CANVAS_HEIGHT,
    TEXT_CONTENT, TEXT_COLOR, TEXT_STROKE_COLOR, TEXT_STROKE_WIDTH,
    TEXT_FONT_SIZE, TEXT_POSITION,
    SNOW_SIZE_MIN, SNOW_SIZE_MAX, SNOW_SPEED_MIN, SNOW_SPEED_MAX,
    GLASS_BAR_HEIGHT, GLASS_BAR_COLOR, GLASS_BAR_OPACITY,
    GLASS_BLUR_AMOUNT, GLASS_CORNER_RADIUS,
    GLASS_TEXT_COLOR, GLASS_TEXT_SIZE, GLASS_TEXT_STROKE, GLASS_TEXT_STROKE_COLOR
)

def _load_font_from_candidates(candidates: List[str], size: int) -> ImageFont.ImageFont:
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _get_text_font(size: int) -> ImageFont.ImageFont:
    import platform

    system = platform.system()
    font_paths = {
        "Darwin": [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ],
        "Windows": [
            "C:\\Windows\\Fonts\\msyh.ttc",
            "C:\\Windows\\Fonts\\arial.ttf",
        ],
        "Linux": [
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ],
    }

    return _load_font_from_candidates(font_paths.get(system, []), size)


def _get_emoji_font(size: int) -> ImageFont.ImageFont:
    import platform

    system = platform.system()
    font_paths = {
        "Darwin": [
            "/System/Library/Fonts/Apple Color Emoji.ttc",
            "/System/Library/Fonts/Apple Color Emoji.ttf",
        ],
        "Windows": [
            "C:\\Windows\\Fonts\\seguiemj.ttf",
        ],
        "Linux": [
            "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
        ],
    }

    font = _load_font_from_candidates(font_paths.get(system, []), size)
    if isinstance(font, ImageFont.FreeTypeFont):
        return font
    return _get_text_font(size)


def _split_graphemes(text: str) -> List[str]:
    clusters: List[str] = []
    current = ""
    for ch in text:
        if not current:
            current = ch
            continue
        code = ord(ch)
        if ch in ("\uFE0F", "\u200D") or 0x1F3FB <= code <= 0x1F3FF:
            current += ch
            continue
        if current.endswith("\u200D"):
            current += ch
            continue
        clusters.append(current)
        current = ch
    if current:
        clusters.append(current)
    return clusters


def _is_emoji(text: str) -> bool:
    for ch in text:
        code = ord(ch)
        if (
            0x1F000 <= code <= 0x1FAFF
            or 0x1F1E6 <= code <= 0x1F1FF
            or 0x2600 <= code <= 0x27BF
            or 0x2300 <= code <= 0x23FF
        ):
            return True
    return False


class SnowParticle:
    """Represents a single snow particle."""

    def __init__(self, canvas_width: int, canvas_height: int):
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.reset(random_y=True)

    def reset(self, random_y: bool = False) -> None:
        """Reset particle to a new random position."""
        self.x = random.randint(0, self.canvas_width)
        self.y = random.randint(-self.canvas_height if random_y else 0, self.canvas_height)
        self.size = random.randint(SNOW_SIZE_MIN, SNOW_SIZE_MAX)
        self.speed = random.uniform(SNOW_SPEED_MIN, SNOW_SPEED_MAX)
        self.opacity = random.uniform(0.6, 1.0)

    def update(self) -> None:
        """Update particle position for next frame."""
        self.y += self.speed
        # Reset if particle moves below canvas
        if self.y > self.canvas_height:
            self.reset(random_y=False)


class SnowEffect:
    """Snow particle effect generator."""

    def __init__(self, canvas_width: int, canvas_height: int, particle_count: int):
        """
        Initialize snow effect.

        Args:
            canvas_width: Width of the canvas
            canvas_height: Height of the canvas
            particle_count: Number of snow particles
        """
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.particles: List[SnowParticle] = [
            SnowParticle(canvas_width, canvas_height)
            for _ in range(particle_count)
        ]

    def generate_frame(self) -> np.ndarray:
        """
        Generate a single frame with snow effect.

        Returns:
            numpy array containing the frame with snow particles
        """
        frame = np.zeros((self.canvas_height, self.canvas_width, 3), dtype=np.uint8)

        for particle in self.particles:
            # Update particle position
            particle.update()

            # Draw particle as white circle
            alpha = int(255 * particle.opacity)
            color = (255, 255, 255)

            # Use thicker circles for larger particles
            thickness = -1  # Filled circle
            cv2.circle(frame, (particle.x, int(particle.y)), particle.size, color, thickness)

        return frame

    def apply_to_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply snow effect on top of an existing frame.

        Args:
            frame: Original frame as numpy array

        Returns:
            Frame with snow particles overlay
        """
        snow_frame = self.generate_frame()

        # Blend snow with original frame
        # Snow is white, so we use additive blending with opacity
        result = frame.copy()

        # Create mask for snow particles
        snow_gray = cv2.cvtColor(snow_frame, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(snow_gray, 50, 255, cv2.THRESH_BINARY)

        # Where there's snow, blend it in
        for i in range(3):
            result[:, :, i] = np.where(
                mask > 0,
                np.clip(result[:, :, i].astype(np.int32) + 50, 0, 255).astype(np.uint8),
                result[:, :, i]
            )

        return result


class TextOverlay:
    """Text overlay renderer using PIL."""

    def __init__(self, text: str = TEXT_CONTENT,
                 color: Tuple[int, int, int] = TEXT_COLOR,
                 stroke_color: Tuple[int, int, int] = TEXT_STROKE_COLOR,
                 stroke_width: int = TEXT_STROKE_WIDTH,
                 font_size: int = TEXT_FONT_SIZE):
        """
        Initialize text overlay.

        Args:
            text: Text content to display
            color: RGB tuple for text color
            stroke_color: RGB tuple for stroke color
            stroke_width: Width of text stroke
            font_size: Font size
        """
        self.text = text
        self.color = color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.font_size = font_size

        # Try to load a system font, fallback to default
        self.font = self._load_font()

    def _load_font(self):
        """Load an appropriate font for the platform."""
        import platform

        system = platform.system()
        font_paths = {
            "Darwin": [
                "/System/Library/Fonts/Helvetica.ttc",
                "/Library/Fonts/Arial.ttf",
                "/System/Library/Fonts/Arial.ttf"
            ],
            "Windows": [
                "C:\\Windows\\Fonts\\arial.ttf",
                "C:\\Windows\\Fonts\\Helvetica.ttc"
            ],
            "Linux": [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
            ]
        }

        for path in font_paths.get(system, []):
            try:
                return ImageFont.truetype(path, self.font_size)
            except (IOError, OSError):
                continue

        # Fallback to default PIL font
        return ImageFont.load_default()

    def generate_frame(self, canvas_width: int, canvas_height: int) -> np.ndarray:
        """
        Generate a frame with just the text overlay on transparent background.

        Args:
            canvas_width: Width of the canvas
            canvas_height: Height of the canvas

        Returns:
            numpy array containing text on transparent background
        """
        # Create transparent image
        img = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Calculate text position
        # Get text bounding box
        left, top, right, bottom = draw.textbbox((0, 0), self.text, font=self.font)
        text_width = right - left
        text_height = bottom - top

        # Position at top with some padding
        x = (canvas_width - text_width) // 2
        y = 50  # Top padding

        # Draw stroke first (outline)
        if self.stroke_width > 0:
            for i in range(-self.stroke_width, self.stroke_width + 1):
                for j in range(-self.stroke_width, self.stroke_width + 1):
                    draw.text((x + i, y + j), self.text, font=self.font,
                             fill=self.stroke_color)

        # Draw main text
        draw.text((x, y), self.text, font=self.font, fill=self.color)

        # Convert to numpy array (BGR format for OpenCV)
        img_array = np.array(img)
        # RGBA to BGR, removing alpha channel
        bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)

        return bgr

    def apply_to_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply text overlay on top of an existing frame.

        Args:
            frame: Original frame as numpy array

        Returns:
            Frame with text overlay
        """
        canvas_height, canvas_width = frame.shape[:2]

        # Generate text frame
        text_frame = self.generate_frame(canvas_width, canvas_height)

        # Create mask for text (non-transparent pixels)
        if text_frame.shape[2] == 3:
            # If text_frame is BGR, create mask
            text_gray = cv2.cvtColor(text_frame, cv2.COLOR_BGR2GRAY)
        else:
            text_gray = cv2.cvtColor(text_frame, cv2.COLOR_RGBA2BGR)
            text_gray = cv2.cvtColor(text_gray, cv2.COLOR_BGR2GRAY)

        _, mask = cv2.threshold(text_gray, 10, 255, cv2.THRESH_BINARY)

        # Where there's text, overlay it
        # For colored text, we need proper alpha blending
        result = frame.copy()

        # Find contours of text
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Draw text directly on frame for better quality
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA))
        draw = ImageDraw.Draw(img)

        left, top, right, bottom = draw.textbbox((0, 0), self.text, font=self.font)
        text_width = right - left
        text_height = bottom - top
        x = (canvas_width - text_width) // 2
        y = 50

        # Draw stroke
        if self.stroke_width > 0:
            for i in range(-self.stroke_width, self.stroke_width + 1):
                for j in range(-self.stroke_width, self.stroke_width + 1):
                    draw.text((x + i, y + j), self.text, font=self.font,
                             fill=self.stroke_color + (255,))

        # Draw main text
        draw.text((x, y), self.text, font=self.font, fill=self.color + (255,))

        # Convert back to BGR
        result = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGR)

        return result


def create_background(canvas_width: int, canvas_height: int,
                      color: Tuple[int, int, int],
                      mode: str = "solid") -> np.ndarray:
    """
    Create a background image.

    Args:
        canvas_width: Width of the background
        canvas_height: Height of the background
        color: RGB tuple for background color
        mode: Background mode - "solid", "gradient", or "blur"

    Returns:
        numpy array containing the background
    """
    if mode == "solid":
        return np.full((canvas_height, canvas_width, 3), color, dtype=np.uint8)

    elif mode == "gradient":
        # Create vertical gradient
        background = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)

        for y in range(canvas_height):
            # Interpolate between color and white
            ratio = y / canvas_height
            r = int(color[0] * (1 - ratio * 0.3) + 255 * ratio * 0.3)
            g = int(color[1] * (1 - ratio * 0.3) + 255 * ratio * 0.3)
            b = int(color[2] * (1 - ratio * 0.3) + 255 * ratio * 0.3)
            background[y, :] = [b, g, r]  # PIL uses RGB, OpenCV uses BGR

        return background

    elif mode == "blur":
        # Create solid background and apply blur
        background = np.full((canvas_height, canvas_width, 3), color, dtype=np.uint8)
        # Apply strong blur for background effect
        blurred = cv2.GaussianBlur(background, (51, 51), 0)
        return blurred

    else:
        # Default to solid
        return np.full((canvas_height, canvas_width, 3), color, dtype=np.uint8)


class ProgressBarOverlay:
    """Progress bar overlay with animated character (e.g., Santa on bike)."""

    def __init__(self, canvas_width: int, canvas_height: int,
                 character: str = "santa",
                 bar_height: int = 40,
                 bar_margin: int = 20):
        """
        Initialize progress bar overlay.

        Args:
            canvas_width: Width of the canvas
            canvas_height: Height of the canvas
            character: Character type - "santa" or "pikachu"
            bar_height: Height of the progress bar
            bar_margin: Margin from bottom
        """
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.character = character
        self.bar_height = bar_height
        self.bar_margin = bar_margin

        # Calculate bar position
        self.bar_y = canvas_height - bar_margin - bar_height
        self.bar_x = 50  # Left margin
        self.bar_width = canvas_width - 100  # Right margin

        # Character emoji
        if character == "santa":
            self.character_emoji = "🎅🚴"
        else:
            self.character_emoji = "⚡🐭🚴"

    def apply_to_frame(self, frame: np.ndarray, progress: float) -> np.ndarray:
        """
        Apply progress bar overlay to a frame.

        Args:
            frame: Original frame as numpy array
            progress: Progress value from 0.0 to 1.0

        Returns:
            Frame with progress bar overlay
        """
        result = frame.copy()

        # Clamp progress
        progress = max(0.0, min(1.0, progress))

        # Draw progress bar background (dark track)
        cv2.rectangle(result,
                      (self.bar_x, self.bar_y),
                      (self.bar_x + self.bar_width, self.bar_y + self.bar_height),
                      (50, 50, 50), -1)

        # Draw progress bar fill (green for Santa, yellow/orange for Pikachu)
        fill_width = int(self.bar_width * progress)
        if self.character == "santa":
            # Green gradient progress
            cv2.rectangle(result,
                          (self.bar_x, self.bar_y),
                          (self.bar_x + fill_width, self.bar_y + self.bar_height),
                          (34, 139, 34), -1)  # Forest green
        else:
            # Yellow/orange gradient progress
            cv2.rectangle(result,
                          (self.bar_x, self.bar_y),
                          (self.bar_x + fill_width, self.bar_y + self.bar_height),
                          (255, 200, 0), -1)  # Golden yellow

        # Draw bar border
        cv2.rectangle(result,
                      (self.bar_x, self.bar_y),
                      (self.bar_x + self.bar_width, self.bar_y + self.bar_height),
                      (0, 0, 0), 2)

        # Draw percentage text
        percent_text = f"{int(progress * 100)}%"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 2
        text_size = cv2.getTextSize(percent_text, font, font_scale, thickness)[0]
        text_x = self.bar_x + self.bar_width + 10
        text_y = self.bar_y + self.bar_height // 2 + text_size[1] // 2

        # Draw white text with black outline
        cv2.putText(result, percent_text, (text_x, text_y), font, font_scale, (0, 0, 0), thickness + 1)
        cv2.putText(result, percent_text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness)

        # Draw character at progress position
        char_x = self.bar_x + fill_width
        char_y = self.bar_y - 10

        # Convert frame to PIL for emoji rendering
        img = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGBA))
        draw = ImageDraw.Draw(img)

        char_font = _get_emoji_font(35)

        # Draw character emoji
        draw.text((char_x - 30, char_y - 25), self.character_emoji, font=char_font)

        # Convert back to BGR
        result = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGR)

        return result


class VideoFrameEffects:
    """Apply video frame effects like rounded corners, borders, and filters."""

    def __init__(self, canvas_width: int, canvas_height: int,
                 border_width: int = 4,
                 border_color: Tuple[int, int, int] = (255, 255, 255),
                 corner_radius: int = 20,
                 enable_warmth: bool = False,
                 warmth_value: int = 5,
                 enable_contrast: bool = False,
                 contrast_value: float = -3.0):
        """
        Initialize video frame effects.

        Args:
            canvas_width: Width of canvas
            canvas_height: Height of canvas
            border_width: Border width around video
            border_color: RGB border color
            corner_radius: Corner radius for rounded video
            enable_warmth: Enable warmth filter
            warmth_value: Warmth adjustment (-20 to 20)
            enable_contrast: Enable contrast filter
            contrast_value: Contrast adjustment (-10 to 10)
        """
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.border_width = border_width
        self.border_color = border_color
        self.corner_radius = corner_radius
        self.enable_warmth = enable_warmth
        self.warmth_value = warmth_value
        self.enable_contrast = enable_contrast
        self.contrast_value = contrast_value

    def apply_frame_effects(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply frame effects to a video frame.

        Args:
            frame: Original frame

        Returns:
            Processed frame with effects
        """
        result = frame.copy()

        # Apply filters if enabled
        if self.enable_warmth or self.enable_contrast:
            result = self._apply_filter(result)

        return result

    def _apply_filter(self, frame: np.ndarray) -> np.ndarray:
        """Apply warmth and contrast filters."""
        # Convert to LAB color space for better color manipulation
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Apply warmth (adjust B channel in LAB)
        if self.enable_warmth:
            # Warmth: increase B channel for warm, decrease for cool
            b = np.clip(b.astype(np.int32) + self.warmth_value, 0, 255).astype(np.uint8)

        # Apply contrast (adjust L channel)
        if self.enable_contrast:
            # Convert to float for contrast adjustment
            l_float = l.astype(np.float32)
            # Contrast factor: (259 * (contrast + 255)) / (255 * (259 - contrast))
            contrast_factor = (259 * (self.contrast_value + 255)) / (255 * (259 - self.contrast_value))
            l_float = np.clip(contrast_factor * (l_float - 128) + 128, 0, 255)
            l = l_float.astype(np.uint8)

        # Merge channels back
        lab = cv2.merge([l, a, b])

        # Convert back to BGR
        result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        return result


class StickerOverlay:
    """Add sticker overlays to video with random effects."""

    # Random stickers/emojis for variety
    RANDOM_STICKERS = [
        '🎅', '🤶', '🎄', '🎁', '⭐', '❄️', '☃️', '🦌', '🔔', '🕯️',
        '❤️', '💕', '💖', '💗', '💓', '💝', '💘', '💌', '💑', '💍',
        '🔥', '💥', '⭐', '✨', '🌟', '💫', '🌙', '☀️', '🌈', '💧',
        '👍', '👎', '❤️', '😂', '😮', '😢', '😡', '😱', '🤔', '😴',
        '🎉', '🎊', '🎈', '🎀', '🧧', '🏮', '🎑', '🪔', '🌸', '🌺',
        '🍎', '🍓', '🍒', '🍑', '🍊', '🍋', '🍌', '🍉', '🍇', '🍓',
        '👑', '👒', '🎩', '🧢', '👑', '💎', '👢', '👠', '👟', '👞',
        '🎬', '🎥', '📹', '🎞️', '📺', '📻', '🎵', '🎶', '🎤', '🎧',
        '💬', '💭', '🗯️', '📢', '🔊', '🔔', '🎵', '🎶', '🎷', '🎸',
        '🚀', '✈️', '🚁', '🚂', '🚗', '🚕', '🚌', '🚎', '🏎️', '🚲',
        '🐭', '🐹', '🐰', '🐻', '🐼', '🐨', '🐯', '🦁', '🐮', '🐷',
        '🐸', '🐵', '🦊', '🦝', '🦌', '🦄', '🐲', '🦋', '🐝', '🐞',
    ]

    def __init__(self, canvas_width: int, canvas_height: int):
        """
        Initialize sticker overlay.

        Args:
            canvas_width: Width of canvas
            canvas_height: Height of canvas
        """
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

    def apply_to_frame(self, frame: np.ndarray,
                       stickers: list = None,
                       frame_index: int = 0) -> np.ndarray:
        """
        Apply stickers to frame.

        Args:
            frame: Original frame
            stickers: List of stickers with position and content
            frame_index: Current frame index for animation effects

        Returns:
            Frame with stickers applied
        """
        if not stickers:
            return frame

        result = frame.copy()

        # Convert to RGBA for transparency support
        img = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGBA))
        draw = ImageDraw.Draw(img)

        font_cache: dict = {}

        def get_sticker_font(size: int) -> ImageFont.ImageFont:
            if size not in font_cache:
                font_cache[size] = _get_emoji_font(size)
            return font_cache[size]

        for i, sticker in enumerate(stickers):
            # Get sticker properties
            x = sticker.get('x', 50)
            y = sticker.get('y', 50)
            content = sticker.get('content', None)
            opacity = sticker.get('opacity', 1.0)
            size = sticker.get('size', 40)
            animation = sticker.get('animation', False)

            # If no content specified, use random sticker
            if content is None:
                import random
                content = random.choice(self.RANDOM_STICKERS)

            # For animated stickers, vary based on frame
            if animation:
                import random
                # Make position slightly wobble
                wobble_x = x + int(frame_index % 5) - 2
                wobble_y = y + int((frame_index * 3) % 5) - 2
            else:
                wobble_x = x
                wobble_y = y

            sticker_font = get_sticker_font(size)

            # Draw emoji text
            if opacity < 1.0:
                # Create temp image with transparency
                temp_width = size * 2
                temp_height = size * 2
                temp_img = Image.new('RGBA', (temp_width, temp_height), (0, 0, 0, 0))
                temp_draw = ImageDraw.Draw(temp_img)

                # Draw with transparency
                fill_color = (255, 255, 255, int(255 * opacity))
                temp_draw.text((0, 0), content, font=sticker_font, fill=fill_color)

                # Paste onto main image
                img.paste(temp_img, (wobble_x, wobble_y), temp_img)
            else:
                draw.text((wobble_x, wobble_y), content, font=sticker_font, fill=(255, 255, 255))

        # Convert back to BGR
        result = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGR)
        return result


def generate_random_stickers(canvas_width: int, canvas_height: int,
                              count: int = 10,
                              video_scale: Optional[float] = None) -> list:
    """
    Generate random stickers with varied positions around video area.

    Args:
        canvas_width: Canvas width
        canvas_height: Canvas height
        count: Number of stickers to generate
        video_scale: Scale of the main video area for layout alignment

    Returns:
        List of sticker dictionaries
    """
    import random

    stickers = []

    layout_scale = video_scale or 0.85
    video_width = int(canvas_width * layout_scale)
    video_height = int(canvas_height * layout_scale)
    margin_x = max(30, (canvas_width - video_width) // 2)
    margin_y = max(40, (canvas_height - video_height) // 2)

    left_x = max(12, margin_x - 25)
    right_x = min(canvas_width - 60, canvas_width - margin_x + 5)
    top_y = max(20, margin_y - 35)
    bottom_y = min(canvas_height - 70, canvas_height - margin_y + 10)

    # Sticker positions around the video area, closer to the video edges
    top_stickers = [
        {'x': margin_x + 20, 'y': top_y, 'content': '✨', 'size': 44, 'opacity': 1.0, 'animation': True},
        {'x': canvas_width // 2, 'y': top_y, 'content': '⭐', 'size': 40, 'opacity': 1.0, 'animation': True},
        {'x': canvas_width - margin_x - 60, 'y': top_y, 'content': '💫', 'size': 44, 'opacity': 1.0, 'animation': True},
    ]

    left_stickers = [
        {'x': left_x, 'y': canvas_height // 2 - 160, 'content': '❤️', 'size': 40, 'opacity': 0.95, 'animation': True},
        {'x': left_x, 'y': canvas_height // 2 - 20, 'content': '💕', 'size': 38, 'opacity': 0.95, 'animation': True},
        {'x': left_x, 'y': canvas_height // 2 + 120, 'content': '💖', 'size': 40, 'opacity': 0.95, 'animation': True},
    ]

    right_stickers = [
        {'x': right_x, 'y': canvas_height // 2 - 160, 'content': '💘', 'size': 40, 'opacity': 0.95, 'animation': True},
        {'x': right_x, 'y': canvas_height // 2 - 20, 'content': '🔥', 'size': 38, 'opacity': 0.95, 'animation': True},
        {'x': right_x, 'y': canvas_height // 2 + 120, 'content': '✨', 'size': 40, 'opacity': 0.95, 'animation': True},
    ]

    bottom_stickers = [
        {'x': margin_x + 30, 'y': bottom_y, 'content': '👍', 'size': 36, 'opacity': 0.9, 'animation': True},
        {'x': canvas_width // 2, 'y': bottom_y, 'content': '💯', 'size': 36, 'opacity': 0.9, 'animation': True},
        {'x': canvas_width - margin_x - 70, 'y': bottom_y, 'content': '🔔', 'size': 36, 'opacity': 0.9, 'animation': True},
    ]

    corner_stickers = [
        {'x': 16, 'y': 20, 'content': '🎀', 'size': 46, 'opacity': 0.9, 'animation': False},
        {'x': canvas_width - 70, 'y': 20, 'content': '🎁', 'size': 46, 'opacity': 0.9, 'animation': False},
    ]

    # Combine all sticker positions
    all_stickers = top_stickers + left_stickers + right_stickers + bottom_stickers + corner_stickers

    # Add random additional stickers
    for _ in range(max(0, count - len(all_stickers))):
        # Random positions in the whitespace areas
        side = random.choice(['top', 'left', 'right', 'bottom'])
        if side == 'top':
            x = random.randint(margin_x + 20, canvas_width - margin_x - 20)
            y = random.randint(max(20, margin_y - 40), max(60, margin_y))
        elif side == 'left':
            x = random.randint(12, max(20, margin_x - 10))
            y = random.randint(canvas_height // 4, canvas_height * 3 // 4)
        elif side == 'right':
            x = random.randint(min(canvas_width - 80, canvas_width - margin_x + 5), canvas_width - 20)
            y = random.randint(canvas_height // 4, canvas_height * 3 // 4)
        else:  # bottom
            x = random.randint(margin_x + 20, canvas_width - margin_x - 20)
            y = random.randint(min(canvas_height - 140, canvas_height - margin_y + 10), canvas_height - 70)

        all_stickers.append({
            'x': x,
            'y': y,
            'content': random.choice(StickerOverlay.RANDOM_STICKERS),
            'size': random.randint(32, 46),
            'opacity': random.uniform(0.8, 1.0),
            'animation': random.choice([True, False])
        })

    # Take requested number of stickers
    for i in range(min(count, len(all_stickers))):
        stickers.append(all_stickers[i])

    return stickers


class BlurBarOverlay:
    """Add blurred bar at bottom to cover subtitles/logos."""

    def __init__(self, canvas_width: int, canvas_height: int,
                 bar_height: int = 150,
                 blur_amount: int = 50):
        """
        Initialize blur bar overlay.

        Args:
            canvas_width: Width of canvas
            canvas_height: Height of canvas
            bar_height: Height of blur bar at bottom
            blur_amount: Blur kernel size (odd number)
        """
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.bar_height = bar_height
        self.blur_amount = blur_amount if blur_amount % 2 == 1 else blur_amount + 1

    def apply_to_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply blur bar to bottom of frame.

        Args:
            frame: Original frame

        Returns:
            Frame with blur bar at bottom
        """
        result = frame.copy()

        # Get the region to blur (bottom of the canvas, corresponds to top of video area)
        y_start = self.canvas_height - self.bar_height

        # Crop the region
        region = result[y_start:self.canvas_height, 0:self.canvas_width]

        # Apply blur
        blurred = cv2.GaussianBlur(region, (self.blur_amount, self.blur_amount), 0)

        # Put blurred region back
        result[y_start:self.canvas_height, 0:self.canvas_width] = blurred

        return result


def create_rounded_mask(width: int, height: int, radius: int) -> np.ndarray:
    """
    Create a rounded rectangle mask.

    Args:
        width: Mask width
        height: Mask height
        radius: Corner radius

    Returns:
        Binary mask as numpy array
    """
    mask = np.ones((height, width), dtype=np.uint8) * 255

    # Create rounded corners using ellipses
    # Top-left
    cv2.ellipse(mask, (radius, radius), (radius, radius), 0, 180, 270, 0, -1)
    # Top-right
    cv2.ellipse(mask, (width - radius, radius), (radius, radius), 0, 270, 360, 0, -1)
    # Bottom-left
    cv2.ellipse(mask, (radius, height - radius), (radius, radius), 0, 90, 180, 0, -1)
    # Bottom-right
    cv2.ellipse(mask, (width - radius, height - radius), (radius, radius), 0, 0, 90, 0, -1)

    # Fill the rectangle
    mask[radius:height - radius, 0:width] = 255
    mask[0:height, radius:width - radius] = 255

    return mask


class SideTextOverlay:
    """Add horizontal side text decorations (left and right of video)."""

    # Default side text phrases
    SIDE_TEXTS = [
        "❤️ 推荐", "🔥 热门", "⭐ 关注", "💕 点赞", "📌 收藏",
        "👍 支持", "🎬 精彩", "✨ 发现", "💡 技巧", "🚀 推荐",
        "🎯 必看", "💯 满分", "🔔 订阅", "📺 更新", "🎥 影视"
    ]

    def __init__(self, canvas_width: int, canvas_height: int,
                 left_texts: list = None,
                 right_texts: list = None,
                 font_size: int = 28,
                 text_color: Tuple[int, int, int] = (255, 255, 255),
                 stroke_color: Tuple[int, int, int] = (0, 0, 0),
                 stroke_width: int = 3,
                 text_margin: int = 0,
                 video_scale: Optional[float] = None):
        """
        Initialize side text overlay.

        Args:
            canvas_width: Width of canvas
            canvas_height: Height of canvas
            left_texts: List of texts for left side (horizontal)
            right_texts: List of texts for right side (horizontal)
            font_size: Font size (larger for better readability)
            text_color: RGB text color
            stroke_color: RGB stroke color
            stroke_width: Stroke width
            text_margin: Margin from edge
            video_scale: Scale of the main video area for layout alignment
        """
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.left_texts = left_texts or ["❤️ 推荐", "🔥 热门", "⭐ 关注"]
        self.right_texts = right_texts or ["👍 支持", "🎬 精彩", "✨ 发现"]
        self.font_size = font_size
        self.text_color = text_color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.text_margin = text_margin
        self.video_scale = video_scale

    def apply_to_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply side text overlay to frame.

        Args:
            frame: Original frame

        Returns:
            Frame with side text applied
        """
        result = frame.copy()

        # Convert to RGBA for better text rendering
        img = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGBA))
        draw = ImageDraw.Draw(img)

        text_font = _get_text_font(self.font_size)
        emoji_font = _get_emoji_font(self.font_size)

        layout_scale = self.video_scale or 0.85
        video_width = int(self.canvas_width * layout_scale)
        margin_x = max(30, (self.canvas_width - video_width) // 2)

        # Left side position - vertically centered on the left side
        left_x = max(8, int(margin_x - self.font_size * 0.5) - self.text_margin)

        # Right side position - vertically centered on the right side
        right_x = min(
            self.canvas_width - self.font_size * 2 - 8,
            int(self.canvas_width - margin_x + self.font_size * 0.5) + self.text_margin
        )

        # Draw left texts horizontally (each text on its own line, but horizontal)
        line_height = self.font_size + 8
        left_start_y = max(20, (self.canvas_height - len(self.left_texts) * line_height) // 2)

        for i, text in enumerate(self.left_texts):
            y = left_start_y + i * line_height
            self._draw_horizontal_text(draw, text, left_x, y, text_font, emoji_font)

        # Draw right texts horizontally
        right_start_y = max(20, (self.canvas_height - len(self.right_texts) * line_height) // 2)

        for i, text in enumerate(self.right_texts):
            y = right_start_y + i * line_height
            self._draw_horizontal_text(draw, text, right_x, y, text_font, emoji_font)

        # Convert back to BGR
        result = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGR)
        return result

    def _draw_horizontal_text(self, draw: ImageDraw, text: str, x: int, y: int,
                              text_font: ImageFont.ImageFont,
                              emoji_font: ImageFont.ImageFont) -> None:
        """
        Draw horizontal text from left to right.

        Args:
            draw: PIL Draw object
            text: Text to draw (horizontal)
            x: X position (starting point)
            y: Y position
            text_font: Font for non-emoji characters
            emoji_font: Font for emoji characters
        """
        current_x = x

        for char in _split_graphemes(text):
            font = emoji_font if _is_emoji(char) else text_font

            # Get character dimensions
            left, top, right, bottom = draw.textbbox((0, 0), char, font=font)
            char_width = right - left
            char_height = bottom - top

            # Draw stroke first
            if self.stroke_width > 0:
                for dx in range(-self.stroke_width, self.stroke_width + 1):
                    for dy in range(-self.stroke_width, self.stroke_width + 1):
                        draw.text((current_x + dx, y + dy), char, font=font,
                                 fill=self.stroke_color + (255,))

            # Draw main text
            draw.text((current_x, y), char, font=font, fill=self.text_color + (255,))

            # Move to next character position
            current_x += char_width + 2  # Small gap between characters


def generate_random_side_texts() -> Tuple[list, list]:
    """
    Generate random side texts for left and right sides.

    Returns:
        Tuple of (left_texts, right_texts)
    """
    import random

    left_texts = random.sample(SideTextOverlay.SIDE_TEXTS, k=min(5, len(SideTextOverlay.SIDE_TEXTS)))
    remaining = [t for t in SideTextOverlay.SIDE_TEXTS if t not in left_texts]
    right_texts = random.sample(remaining, k=min(5, len(remaining)))

    return left_texts, right_texts


class GIFStickerOverlay:
    """Add GIF sticker overlays to video frames."""

    def __init__(self, canvas_width: int, canvas_height: int,
                 gif_stickers: list = None):
        """
        Initialize GIF sticker overlay.

        Args:
            canvas_width: Width of canvas
            canvas_height: Height of canvas
            gif_stickers: List of GIF sticker dictionaries with path, x, y, scale
        """
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.gif_stickers = gif_stickers or []

        # Pre-load GIF frames for each sticker
        self._gif_frames = {}
        self._gif_durations = {}

        for sticker in self.gif_stickers:
            gif_path = sticker.get('path')
            if gif_path and os.path.exists(gif_path):
                try:
                    gif = Image.open(gif_path)
                    frames = []
                    durations = []

                    # Extract all frames from the GIF
                    try:
                        while True:
                            # Convert frame to RGBA for consistent handling
                            frame = gif.copy()
                            if frame.mode != 'RGBA':
                                frame = frame.convert('RGBA')

                            # Convert to numpy array
                            frame_array = np.array(frame)
                            frames.append(frame_array)
                            durations.append(gif.info.get('duration', 100))

                            gif.seek(gif.tell() + 1)
                    except EOFError:
                        pass  # End of frames

                    # Reset to first frame
                    gif.seek(0)

                    if frames:
                        self._gif_frames[gif_path] = frames
                        self._gif_durations[gif_path] = durations
                        logger.info(f"Loaded GIF: {gif_path} ({len(frames)} frames)")

                except Exception as e:
                    logger.warning(f"Failed to load GIF {gif_path}: {e}")

    def _get_frame_for_time(self, gif_path: str, elapsed_ms: int) -> Optional[np.ndarray]:
        """
        Get the appropriate frame for a given elapsed time.

        Args:
            gif_path: Path to the GIF file
            elapsed_ms: Elapsed time in milliseconds

        Returns:
            Frame as numpy array or None
        """
        if gif_path not in self._gif_frames:
            return None

        frames = self._gif_frames[gif_path]
        durations = self._gif_durations[gif_path]

        if not frames:
            return None

        total_duration = sum(durations)
        if total_duration == 0:
            return frames[0]

        # Calculate which frame to show
        time_in_cycle = elapsed_ms % total_duration
        cumulative = 0

        for i, duration in enumerate(durations):
            cumulative += duration
            if cumulative >= time_in_cycle:
                return frames[i]

        return frames[-1]

    def apply_to_frame(self, frame: np.ndarray, frame_index: int = 0,
                       fps: float = 30.0) -> np.ndarray:
        """
        Apply GIF stickers to frame.

        Args:
            frame: Original frame
            frame_index: Current frame index
            fps: Frames per second for timing GIF animation

        Returns:
            Frame with GIF stickers applied
        """
        if not self.gif_stickers:
            return frame

        result = frame.copy()

        # Convert to RGBA for transparency support
        img = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGBA))
        draw = ImageDraw.Draw(img)

        # Calculate elapsed time for GIF animation
        elapsed_ms = int((frame_index / fps) * 1000) if fps > 0 else 0

        for sticker in self.gif_stickers:
            gif_path = sticker.get('path')
            x = sticker.get('x', 20)
            y = sticker.get('y', 20)
            scale = sticker.get('scale', 0.25)

            gif_frame = self._get_frame_for_time(gif_path, elapsed_ms)

            if gif_frame is None:
                continue

            # Resize GIF frame based on scale
            orig_height, orig_width = gif_frame.shape[:2]
            new_width = int(orig_width * scale)
            new_height = int(orig_height * scale)

            if new_width <= 0 or new_height <= 0:
                continue

            try:
                # Resize the frame
                resized = cv2.resize(gif_frame, (new_width, new_height),
                                   interpolation=cv2.INTER_LINEAR)

                # Convert to PIL Image
                gif_pil = Image.fromarray(resized)

                # Paste onto main image with alpha blending
                img.paste(gif_pil, (x, y), gif_pil)

            except Exception as e:
                logger.warning(f"Failed to paste GIF frame: {e}")
                continue

        # Convert back to BGR
        result = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGR)
        return result


class GlassmorphismSubtitleOverlay:
    """
    Overlay subtitles on a glassmorphism bar at the bottom of the video.
    Used to cover original subtitles and display rewritten ones.
    The bar is positioned INSIDE the video frame area, at the bottom.
    """

    def __init__(self, canvas_width: int, canvas_height: int,
                 subtitles: List[Dict] = None,
                 bar_height: int = GLASS_BAR_HEIGHT,
                 bar_color: Tuple[int, int, int] = GLASS_BAR_COLOR,
                 bar_opacity: int = GLASS_BAR_OPACITY,
                 blur_amount: int = GLASS_BLUR_AMOUNT,
                 corner_radius: int = GLASS_CORNER_RADIUS,
                 text_color: Tuple[int, int, int] = GLASS_TEXT_COLOR,
                 text_size: int = GLASS_TEXT_SIZE,
                 text_stroke: int = GLASS_TEXT_STROKE,
                 text_stroke_color: Tuple[int, int, int] = GLASS_TEXT_STROKE_COLOR,
                 video_scale: float = 0.85):  # Add video scale for positioning
        """
        Initialize glassmorphism subtitle overlay.

        Args:
            canvas_width: Width of canvas
            canvas_height: Height of canvas
            subtitles: List of subtitle dictionaries with 'start_time', 'end_time', 'text'
            bar_height: Height of the glass bar
            bar_color: RGB base color of the bar
            bar_opacity: Opacity (0-255)
            blur_amount: Gaussian blur amount
            corner_radius: Corner radius for rounded corners
            text_color: RGB text color
            text_size: Font size for text
            text_stroke: Stroke width for text
            text_stroke_color: RGB stroke color
            video_scale: Scale of the video area (0.75-0.90) for positioning
        """
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.subtitles = subtitles or []
        self.bar_height = bar_height
        self.bar_color = bar_color
        self.bar_opacity = bar_opacity
        self.blur_amount = blur_amount if blur_amount % 2 == 1 else blur_amount + 1
        self.corner_radius = corner_radius
        self.text_color = text_color
        self.text_size = text_size
        self.text_stroke = text_stroke
        self.text_stroke_color = text_stroke_color
        self.video_scale = video_scale

        # Calculate video frame position (video is centered on canvas)
        # This is the same calculation as in video_processor._create_pip_frame
        fit_scale = min(canvas_width / 1920, canvas_height / 1080)  # Assume 1080p reference
        actual_scale = fit_scale * video_scale
        video_width = int(1920 * actual_scale)
        video_height = int(1080 * actual_scale)

        self.video_x = (canvas_width - video_width) // 2
        self.video_y = (canvas_height - video_height) // 2

        # Bar position: INSIDE video frame, at the bottom
        # Position it slightly above the bottom of the video to cover subtitles
        self.bar_x = self.video_x
        self.bar_y = self.video_y + video_height - bar_height

        # Load fonts
        self.text_font = _get_text_font(self.text_size)
        self.emoji_font = _get_emoji_font(self.text_size)

    def get_subtitle_at_time(self, current_time: float) -> Optional[str]:
        """
        Get the subtitle text that should be displayed at the given time.

        Args:
            current_time: Current time in seconds

        Returns:
            Subtitle text or None if no subtitle should be shown
        """
        from config import time_to_seconds

        for subtitle in self.subtitles:
            start = time_to_seconds(subtitle['start_time'])
            end = time_to_seconds(subtitle['end_time'])

            if start <= current_time <= end:
                return subtitle['text']

        return None

    def apply_to_frame(self, frame: np.ndarray, current_time: float) -> np.ndarray:
        """
        Apply glassmorphism subtitle bar to frame.

        Args:
            frame: Original frame
            current_time: Current video time in seconds

        Returns:
            Frame with glassmorphism subtitle overlay
        """
        result = frame.copy()

        # Get current subtitle
        subtitle_text = self.get_subtitle_at_time(current_time)

        if not subtitle_text:
            # Still apply the glass bar even without subtitle
            result = self._apply_glass_bar(result)
            return result

        # Apply glass bar first
        result = self._apply_glass_bar(result)

        # Apply subtitle text
        result = self._apply_subtitle_text(result, subtitle_text)

        return result

    def _apply_glass_bar(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply the glassmorphism bar to the frame.
        The bar is positioned INSIDE the video frame area.

        Args:
            frame: Original frame

        Returns:
            Frame with glass bar applied
        """
        result = frame.copy()

        # Get the region for the bar (INSIDE video frame)
        x_start = self.bar_x
        y_start = self.bar_y
        bar_width = self.canvas_width - 2 * self.video_x  # Width of video area

        # Ensure we don't go out of bounds
        if y_start < 0:
            y_start = 0
        if y_start + self.bar_height > self.canvas_height:
            self.bar_height = self.canvas_height - y_start

        bar_region = result[y_start:y_start + self.bar_height, x_start:x_start + bar_width].copy()

        # Apply strong blur to create the frosted glass effect
        blurred = cv2.GaussianBlur(bar_region, (self.blur_amount, self.blur_amount), 0)

        # Create a semi-transparent overlay
        overlay = np.full(bar_region.shape, self.bar_color, dtype=np.uint8)

        # Blend the blurred background with the overlay color
        alpha = self.bar_opacity / 255.0
        blended = cv2.addWeighted(blurred, 1 - alpha, overlay, alpha, 0)

        # Apply rounded corners to the bar region
        if self.corner_radius > 0:
            mask = self._create_rounded_mask(bar_width, self.bar_height, self.corner_radius)
            # Resize mask to match the region
            mask_resized = cv2.resize(mask, (bar_width, self.bar_height))

            # Apply mask to keep only the rounded area
            for c in range(3):
                blended[:, :, c] = np.where(
                    mask_resized == 0,
                    bar_region[:, :, c],
                    blended[:, :, c]
                )

        # Put the blended bar back
        result[y_start:y_start + self.bar_height, x_start:x_start + bar_width] = blended

        # Add a subtle border/shadow for depth (only on left and right edges inside video)
        border_color = (255, 255, 255)  # Light border for glass effect
        border_width = 2
        cv2.rectangle(
            result,
            (x_start, y_start),
            (x_start + bar_width - 1, y_start + self.bar_height - 1),
            border_color,
            border_width
        )

        return result

    def _apply_subtitle_text(self, frame: np.ndarray, text: str) -> np.ndarray:
        """
        Apply subtitle text on top of the glass bar.

        Args:
            frame: Frame with glass bar
            text: Subtitle text to display

        Returns:
            Frame with text applied
        """
        result = frame.copy()

        # Convert to RGBA for better text handling
        img = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGBA))
        draw = ImageDraw.Draw(img)

        # Calculate text position (centered horizontally within video, vertically in bar)
        bbox = draw.textbbox((0, 0), text, font=self.text_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Center text within the video area
        x = self.video_x + (self.canvas_width - 2 * self.video_x - text_width) // 2
        y = self.bar_y + (self.bar_height - text_height) // 2

        # Draw stroke/outline for better readability
        if self.text_stroke > 0:
            stroke_fill = self.text_stroke_color + (255,)
            for dx in range(-self.text_stroke, self.text_stroke + 1):
                for dy in range(-self.text_stroke, self.text_stroke + 1):
                    draw.text((x + dx, y + dy), text, font=self.text_font, fill=stroke_fill)

        # Draw main text
        text_fill = self.text_color + (255,)
        draw.text((x, y), text, font=self.text_font, fill=text_fill)

        # Convert back to BGR
        result = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGR)

        return result

    def _create_rounded_mask(self, width: int, height: int, radius: int) -> np.ndarray:
        """
        Create a rounded rectangle mask.

        Args:
            width: Mask width
            height: Mask height
            radius: Corner radius

        Returns:
            Binary mask (255 = keep, 0 = transparent)
        """
        mask = np.zeros((height, width), dtype=np.uint8)

        # Fill with white
        mask[:] = 255

        # Create rounded corners using ellipses
        # Top-left
        cv2.ellipse(mask, (radius, radius), (radius, radius), 0, 180, 270, 0, -1)
        # Top-right
        cv2.ellipse(mask, (width - radius, radius), (radius, radius), 0, 270, 360, 0, -1)
        # Bottom-left
        cv2.ellipse(mask, (radius, height - radius), (radius, radius), 0, 90, 180, 0, -1)
        # Bottom-right
        cv2.ellipse(mask, (width - radius, height - radius), (radius, radius), 0, 0, 90, 0, -1)

        # Fill the rectangle (keep corners as white, fill the cut corners with 0)
        mask[radius:height - radius, 0:width] = 255
        mask[0:height, radius:width - radius] = 255


class FilmGrain:
    """Apply film grain (noise) effect to video frames."""

    def __init__(self, canvas_width: int, canvas_height: int,
                 grain_intensity: float = 0.05,
                 grain_color: str = "gray"):
        """
        Initialize film grain effect.

        Args:
            canvas_width: Width of canvas
            canvas_height: Height of canvas
            grain_intensity: Intensity of grain (0.01-0.1, recommended 0.03-0.05)
            grain_color: Color of grain - "gray", "white", or "colored"
        """
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.grain_intensity = grain_intensity
        self.grain_color = grain_color

    def apply_to_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply film grain to a video frame.

        Args:
            frame: Original frame

        Returns:
            Frame with film grain applied
        """
        result = frame.copy()

        # Generate random noise
        noise = np.random.normal(0, self.grain_intensity * 255, frame.shape).astype(np.float32)

        # Apply noise based on color mode
        if self.grain_color == "gray":
            # Grayscale noise - same for all channels
            noise_gray = np.random.normal(0, self.grain_intensity * 255, (frame.shape[0], frame.shape[1]))
            noise = np.stack([noise_gray] * 3, axis=-1)
        elif self.grain_color == "white":
            # White noise - bright specks
            noise = np.random.uniform(-self.grain_intensity * 255, self.grain_intensity * 255, frame.shape)
        # "colored" mode uses the full RGB noise generated above

        # Convert frame to float for noise addition
        result = result.astype(np.float32)

        # Add noise
        result = result + noise

        # Clip to valid range
        result = np.clip(result, 0, 255)

        # Convert back to uint8
        return result.astype(np.uint8)


# ============== Advanced Visual Effects ==============

class GeometricTransform:
    """Apply geometric transformations: crop, perspective, displacement."""

    def __init__(self, crop_params: dict = None,
                 perspective_params: list = None,
                 displacement_params: dict = None):
        """
        Initialize geometric transformation.

        Args:
            crop_params: Crop parameters dict
            perspective_params: Perspective transform points
            displacement_params: Displacement parameters dict
        """
        self.crop_params = crop_params or {}
        self.perspective_params = perspective_params or []
        self.displacement_params = displacement_params or {}

    def apply_crop(self, frame: np.ndarray) -> np.ndarray:
        """Apply crop to frame."""
        if not self.crop_params:
            return frame

        h, w = frame.shape[:2]
        crop_type = self.crop_params.get("type", "none")

        if crop_type == "edge":
            top = self.crop_params.get("top", 0)
            bottom = self.crop_params.get("bottom", 0)
            left = self.crop_params.get("left", 0)
            right = self.crop_params.get("right", 0)
            return frame[top:h-bottom, left:w-right]

        elif crop_type == "center":
            ratio = self.crop_params.get("ratio", 0.9)
            new_h = int(h * ratio)
            new_w = int(w * ratio)
            y = (h - new_h) // 2
            x = (w - new_w) // 2
            return frame[y:y+new_h, x:x+new_w]

        elif crop_type == "random":
            top = self.crop_params.get("top", 0)
            bottom = self.crop_params.get("bottom", 0)
            left = self.crop_params.get("left", 0)
            right = self.crop_params.get("right", 0)
            return frame[top:h-bottom, left:w-right]

        return frame

    def apply_perspective(self, frame: np.ndarray) -> np.ndarray:
        """Apply perspective transform to frame."""
        if not self.perspective_params:
            return frame

        h, w = frame.shape[:2]

        # Extract source and destination points
        src_points = np.float32([p[0] for p in self.perspective_params])
        dst_points = np.float32([p[1] for p in self.perspective_params])

        # Get perspective transform matrix
        matrix = cv2.getPerspectiveTransform(src_points, dst_points)

        # Apply perspective transform
        result = cv2.warpPerspective(frame, matrix, (w, h))

        return result

    def apply_displacement(self, frame: np.ndarray, frame_index: int = 0) -> np.ndarray:
        """Apply displacement (shake/slide) to frame."""
        if not self.displacement_params:
            return frame

        h, w = frame.shape[:2]
        disp_type = self.displacement_params.get("type", "none")

        if disp_type == "fixed":
            dx = self.displacement_params.get("x", 0)
            dy = self.displacement_params.get("y", 0)
            # Use translation matrix
            matrix = np.float32([[1, 0, dx], [0, 1, dy]])
            result = cv2.warpAffine(frame, matrix, (w, h))
            return result

        elif disp_type == "shake":
            intensity = self.displacement_params.get("intensity", 3)
            frequency = self.displacement_params.get("frequency", 10)
            # Calculate shake offset based on frame index
            offset_x = int(intensity * np.sin(2 * np.pi * frequency * frame_index / 30))
            offset_y = int(intensity * np.cos(2 * np.pi * frequency * frame_index / 30))
            matrix = np.float32([[1, 0, offset_x], [0, 1, offset_y]])
            result = cv2.warpAffine(frame, matrix, (w, h))
            return result

        elif disp_type == "slide":
            direction = self.displacement_params.get("direction", "right")
            distance = self.displacement_params.get("distance", 10)
            # Calculate slide offset based on time
            slide_factor = (frame_index % 60) / 60.0  # 0 to 1

            if direction == "left":
                dx = -int(distance * slide_factor)
                dy = 0
            elif direction == "right":
                dx = int(distance * slide_factor)
                dy = 0
            elif direction == "up":
                dx = 0
                dy = -int(distance * slide_factor)
            else:  # down
                dx = 0
                dy = int(distance * slide_factor)

            matrix = np.float32([[1, 0, dx], [0, 1, dy]])
            result = cv2.warpAffine(frame, matrix, (w, h))
            return result

        return frame

    def apply_to_frame(self, frame: np.ndarray, frame_index: int = 0) -> np.ndarray:
        """Apply all geometric transforms to frame."""
        result = frame.copy()

        result = self.apply_crop(result)
        result = self.apply_perspective(result)
        result = self.apply_displacement(result, frame_index)

        return result


class ColorAdjustments:
    """Apply advanced color adjustments."""

    def __init__(self, brightness: float = 0.0,
                 contrast: float = 1.0,
                 saturation: float = 1.0,
                 hue_shift: float = 0.0,
                 gamma: float = 1.0,
                 lut_filter: str = None):
        """
        Initialize color adjustments.

        Args:
            brightness: Brightness adjustment (-0.1 to 0.1)
            contrast: Contrast multiplier (0.95 to 1.1)
            saturation: Saturation multiplier (0.9 to 1.15)
            hue_shift: Hue shift in degrees (-10 to 10)
            gamma: Gamma correction (0.9 to 1.1)
            lut_filter: LUT filter name
        """
        self.brightness = brightness
        self.contrast = contrast
        self.saturation = saturation
        self.hue_shift = hue_shift
        self.gamma = gamma
        self.lut_filter = lut_filter

    def apply_brightness_contrast(self, frame: np.ndarray) -> np.ndarray:
        """Apply brightness and contrast adjustments."""
        result = frame.copy().astype(np.float32)

        # Apply brightness
        result = result + (self.brightness * 255)

        # Apply contrast
        if self.contrast != 1.0:
            result = (result - 128) * self.contrast + 128

        result = np.clip(result, 0, 255)
        return result.astype(np.uint8)

    def apply_saturation(self, frame: np.ndarray) -> np.ndarray:
        """Apply saturation adjustment."""
        if self.saturation == 1.0:
            return frame

        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        # Adjust saturation
        s = np.clip(s.astype(np.float32) * self.saturation, 0, 255).astype(np.uint8)

        # Merge and convert back
        hsv = cv2.merge([h, s, v])
        result = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        return result

    def apply_hue_shift(self, frame: np.ndarray) -> np.ndarray:
        """Apply hue shift."""
        if self.hue_shift == 0.0:
            return frame

        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        # Shift hue (OpenCV uses 0-179 range)
        h = (h.astype(np.int32) + int(self.hue_shift / 2)) % 180
        h = h.astype(np.uint8)

        # Merge and convert back
        hsv = cv2.merge([h, s, v])
        result = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        return result

    def apply_gamma(self, frame: np.ndarray) -> np.ndarray:
        """Apply gamma correction."""
        if self.gamma == 1.0:
            return frame

        # Build lookup table
        inv_gamma = 1.0 / self.gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(np.uint8)

        # Apply gamma correction using LUT
        result = cv2.LUT(frame, table)
        return result

    def apply_lut_filter(self, frame: np.ndarray) -> np.ndarray:
        """Apply LUT filter effect."""
        if not self.lut_filter:
            return frame

        result = frame.copy()

        if self.lut_filter == "bw" or self.lut_filter == "grayscale":
            # Convert to grayscale
            gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
            result = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        elif self.lut_filter == "sepia":
            # Apply sepia tone
            kernel = np.array([[0.272, 0.534, 0.131],
                             [0.349, 0.686, 0.168],
                             [0.393, 0.769, 0.189]])
            result = cv2.transform(result, kernel)

        elif self.lut_filter == "negate":
            # Invert colors
            result = cv2.bitwise_not(result)

        elif self.lut_filter == "vintage":
            # Vintage effect: slight sepia + reduced contrast
            kernel = np.array([[0.393, 0.769, 0.189],
                             [0.349, 0.686, 0.168],
                             [0.272, 0.534, 0.131]])
            sepia = cv2.transform(result, kernel)
            result = cv2.addWeighted(result, 0.6, sepia, 0.4, 0)

        elif self.lut_filter == "cool":
            # Cool effect: shift towards blue
            result = result.copy().astype(np.float32)
            result[:, :, 0] = result[:, :, 0] * 0.9  # Reduce red
            result[:, :, 1] = result[:, :, 1] * 0.95  # Slightly reduce green
            result[:, :, 2] = np.clip(result[:, :, 2] * 1.1, 0, 255)  # Boost blue
            result = np.clip(result, 0, 255).astype(np.uint8)

        elif self.lut_filter == "warm":
            # Warm effect: shift towards red/yellow
            result = result.copy().astype(np.float32)
            result[:, :, 0] = np.clip(result[:, :, 0] * 1.1, 0, 255)  # Boost red
            result[:, :, 1] = np.clip(result[:, :, 1] * 1.05, 0, 255)  # Boost green
            result[:, :, 2] = result[:, :, 2] * 0.9  # Reduce blue
            result = np.clip(result, 0, 255).astype(np.uint8)

        return result

    def apply_to_frame(self, frame: np.ndarray) -> np.ndarray:
        """Apply all color adjustments to frame."""
        result = frame.copy()

        result = self.apply_brightness_contrast(result)
        result = self.apply_saturation(result)
        result = self.apply_hue_shift(result)
        result = self.apply_gamma(result)
        result = self.apply_lut_filter(result)

        return result


class SharpnessEffects:
    """Apply sharpness, blur, and denoise effects."""

    def __init__(self, gaussian_blur: float = 0.0,
                 sharpen_strength: float = 1.5,
                 denoise_strength: int = 5):
        """
        Initialize sharpness effects.

        Args:
            gaussian_blur: Gaussian blur kernel size (0 = disabled)
            sharpen_strength: Sharpening strength (1.0-3.0)
            denoise_strength: Denoising strength (1-10)
        """
        self.gaussian_blur = gaussian_blur
        self.sharpen_strength = sharpen_strength
        self.denoise_strength = denoise_strength

    def apply_blur(self, frame: np.ndarray) -> np.ndarray:
        """Apply Gaussian blur."""
        if self.gaussian_blur <= 0:
            return frame

        # Calculate kernel size (must be odd)
        kernel_size = int(self.gaussian_blur * 10)
        if kernel_size % 2 == 0:
            kernel_size += 1
        kernel_size = max(3, kernel_size)

        result = cv2.GaussianBlur(frame, (kernel_size, kernel_size), 0)
        return result

    def apply_sharpen(self, frame: np.ndarray) -> np.ndarray:
        """Apply unsharp mask sharpening."""
        if self.sharpen_strength == 0:
            return frame

        # Create Gaussian blur for unsharp mask
        blurred = cv2.GaussianBlur(frame, (0, 0), 3)
        sharpened = cv2.addWeighted(frame, 1.0 + self.sharpen_strength * 0.5,
                                   blurred, -self.sharpen_strength * 0.5, 0)
        return sharpened

    def apply_denoise(self, frame: np.ndarray) -> np.ndarray:
        """Apply fast denoising."""
        if self.denoise_strength <= 0:
            return frame

        # Use fastNlMeansDenoisingColored
        template_window_size = max(3, self.denoise_strength)
        search_window_size = 21

        result = cv2.fastNlMeansDenoisingColored(
            frame, None, template_window_size, template_window_size,
            search_window_size, search_window_size
        )
        return result

    def apply_to_frame(self, frame: np.ndarray) -> np.ndarray:
        """Apply all sharpness effects to frame."""
        result = frame.copy()

        result = self.apply_denoise(result)
        result = self.apply_blur(result)
        result = self.apply_sharpen(result)

        return result


class TextureOverlay:
    """Add texture overlays: scratches, dust, light leaks."""

    def __init__(self, scratch_density: float = 0.02,
                 dust_density: float = 0.05,
                 leak_intensity: float = 0.1):
        """
        Initialize texture overlay.

        Args:
            scratch_density: Density of scratches (0.0-1.0)
            dust_density: Density of dust spots (0.0-1.0)
            leak_intensity: Intensity of light leaks (0.0-1.0)
        """
        self.scratch_density = scratch_density
        self.dust_density = dust_density
        self.leak_intensity = leak_intensity

        # Pre-generate scratch and dust patterns for consistency
        self.scratches = []
        self.dust_spots = []

    def apply_scratches(self, frame: np.ndarray) -> np.ndarray:
        """Apply scratch lines."""
        if self.scratch_density <= 0:
            return frame

        result = frame.copy()
        h, w = frame.shape[:2]

        # Randomly add scratch lines
        num_scratches = int(self.scratch_density * 20)

        for _ in range(num_scratches):
            if random.random() > 0.3:  # 70% chance to show scratch
                x = random.randint(0, w - 1)
                y_start = random.randint(0, h // 3)
                length = random.randint(h // 3, h)

                # Draw vertical scratch line
                color = random.randint(180, 255)
                thickness = random.randint(1, 2)
                cv2.line(result, (x, y_start), (x, y_start + length),
                        (color, color, color), thickness)

        return result

    def apply_dust(self, frame: np.ndarray) -> np.ndarray:
        """Apply dust spots."""
        if self.dust_density <= 0:
            return frame

        result = frame.copy()
        h, w = frame.shape[:2]

        # Randomly add dust spots
        num_dust = int(self.dust_density * 50)

        for _ in range(num_dust):
            if random.random() > 0.5:  # 50% chance to show dust
                x = random.randint(0, w - 1)
                y = random.randint(0, h - 1)
                radius = random.randint(1, 3)

                # Draw dark dust spot
                color = random.randint(0, 50)
                cv2.circle(result, (x, y), radius, (color, color, color), -1)

        return result

    def apply_light_leak(self, frame: np.ndarray) -> np.ndarray:
        """Apply light leak effect."""
        if self.leak_intensity <= 0:
            return frame

        result = frame.copy().astype(np.float32)
        h, w = frame.shape[:2]

        # Create gradient overlay
        leak_pos = random.choice(["top_left", "top_right", "bottom_left", "bottom_right"])

        if leak_pos == "top_left":
            gradient = np.zeros((h, w, 3), dtype=np.float32)
            for i in range(min(h, w)):
                alpha = self.leak_intensity * (1 - i / min(h, w))
                gradient[i, :i] = [255 * alpha * 1.2, 200 * alpha, 150 * alpha]

        elif leak_pos == "top_right":
            gradient = np.zeros((h, w, 3), dtype=np.float32)
            for i in range(min(h, w)):
                alpha = self.leak_intensity * (1 - i / min(h, w))
                gradient[i, w-i:] = [255 * alpha * 1.2, 200 * alpha, 150 * alpha]

        elif leak_pos == "bottom_left":
            gradient = np.zeros((h, w, 3), dtype=np.float32)
            for i in range(min(h, w)):
                alpha = self.leak_intensity * (1 - i / min(h, w))
                gradient[h-i:, :i] = [255 * alpha * 1.2, 200 * alpha, 150 * alpha]

        else:  # bottom_right
            gradient = np.zeros((h, w, 3), dtype=np.float32)
            for i in range(min(h, w)):
                alpha = self.leak_intensity * (1 - i / min(h, w))
                gradient[h-i:, w-i:] = [255 * alpha * 1.2, 200 * alpha, 150 * alpha]

        # Blend gradient with frame
        result = np.clip(result + gradient, 0, 255)
        return result.astype(np.uint8)

    def apply_to_frame(self, frame: np.ndarray) -> np.ndarray:
        """Apply all texture effects to frame."""
        result = frame.copy()

        result = self.apply_light_leak(result)
        result = self.apply_scratches(result)
        result = self.apply_dust(result)

        return result


class EdgeEffects:
    """Apply edge detection and cartoon effects."""

    def __init__(self, edge_threshold: int = 50,
                 cartoon_level: int = 5,
                 enable_edges: bool = False,
                 enable_cartoon: bool = False):
        """
        Initialize edge effects.

        Args:
            edge_threshold: Edge detection threshold (0-255)
            cartoon_level: Cartoon effect level (1-10)
            enable_edges: Enable edge detection overlay
            enable_cartoon: Enable cartoon effect
        """
        self.edge_threshold = edge_threshold
        self.cartoon_level = cartoon_level
        self.enable_edges = enable_edges
        self.enable_cartoon = enable_cartoon

    def apply_edge_detection(self, frame: np.ndarray) -> np.ndarray:
        """Apply Canny edge detection."""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply Canny edge detection
        edges = cv2.Canny(gray, self.edge_threshold, self.edge_threshold * 2)

        # Convert back to BGR
        edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

        return edges_bgr

    def apply_cartoon(self, frame: np.ndarray) -> np.ndarray:
        """Apply cartoon effect."""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply bilateral filter for cartoon effect
        filtered = cv2.bilateralFilter(frame, 9, 75, 75)

        # Detect edges
        edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                     cv2.THRESH_BINARY, 9, 2)

        # Convert edges to 3-channel
        edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

        # Combine edges with filtered image
        cartoon = cv2.bitwise_and(filtered, edges_bgr)

        return cartoon

    def apply_to_frame(self, frame: np.ndarray) -> np.ndarray:
        """Apply edge effects to frame."""
        result = frame.copy()

        if self.enable_cartoon:
            result = self.apply_cartoon(result)
        elif self.enable_edges:
            edges = self.apply_edge_detection(result)
            # Blend edges with original
            result = cv2.addWeighted(result, 0.7, edges, 0.3, 0)

        return result
