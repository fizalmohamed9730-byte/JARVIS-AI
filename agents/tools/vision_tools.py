"""Vision tools for JARVIS AI agent system."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_DESKTOP = Path.home() / "Desktop"


def _validate_image_path(image_path: str) -> Optional[str]:
    """Validate and normalize an image path."""
    path = os.path.expanduser(image_path.strip())
    if not os.path.isfile(path):
        return None
    valid_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}
    ext = os.path.splitext(path)[1].lower()
    if ext not in valid_extensions:
        return None
    return path


@tool
def analyze_image(image_path: str) -> str:
    """Analyze and describe the content of an image.

    Args:
        image_path: Full path to the image file.

    Returns:
        A description of the image content.
    """
    if not image_path or not image_path.strip():
        return "Error: Image path is required."

    validated = _validate_image_path(image_path)
    if not validated:
        return f"Error: Invalid or missing image file: {image_path}"

    try:
        from PIL import Image

        img = Image.open(validated)
        width, height = img.size
        mode = img.mode
        fmt = img.format or "Unknown"

        info_parts = [
            f"Image: {os.path.basename(validated)}",
            f"Format: {fmt}",
            f"Dimensions: {width}x{height} pixels",
            f"Color mode: {mode}",
            f"File size: {os.path.getsize(validated) / 1024:.1f} KB",
        ]

        if hasattr(img, "info") and img.info:
            for key in ("dpi", "exif"):
                if key in img.info:
                    info_parts.append(f"{key}: {img.info[key]}")

        try:
            exif_data = img._getexif()
            if exif_data:
                from PIL.ExifTags import TAGS
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)
                    if tag_name in ("Make", "Model", "DateTime", "Software"):
                        info_parts.append(f"EXIF {tag_name}: {value}")
        except (AttributeError, Exception):
            pass

        return "\n".join(info_parts)

    except ImportError:
        return "Image analysis requires Pillow. Install: pip install Pillow"
    except Exception as e:
        return f"Error analyzing image: {e}"


@tool
def ocr_image(image_path: str) -> str:
    """Extract text from an image using OCR.

    Args:
        image_path: Full path to the image file.

    Returns:
        The extracted text content, or an error message.
    """
    if not image_path or not image_path.strip():
        return "Error: Image path is required."

    validated = _validate_image_path(image_path)
    if not validated:
        return f"Error: Invalid or missing image file: {image_path}"

    try:
        try:
            import pytesseract
            from PIL import Image

            img = Image.open(validated)
            text = pytesseract.image_to_string(img)

            if not text or not text.strip():
                return "No text found in the image."

            return f"Extracted text:\n\n{text.strip()}"

        except ImportError:
            pass

        try:
            import easyocr

            reader = easyocr.Reader(["en"], gpu=False)
            results = reader.readtext(validated)

            if not results:
                return "No text found in the image."

            extracted = "\n".join([r[1] for r in results])
            return f"Extracted text:\n\n{extracted}"

        except ImportError:
            pass

        return (
            "OCR requires a text recognition library. Install one of:\n"
            "  - pip install pytesseract (also requires Tesseract-OCR installed on system)\n"
            "  - pip install easyocr"
        )

    except Exception as e:
        return f"Error during OCR: {e}"


@tool
def capture_webcam() -> str:
    """Capture a frame from the default webcam.

    Returns:
        The path to the saved webcam image or an error message.
    """
    try:
        import cv2

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return "Error: Could not open webcam. Make sure a camera is connected."

        ret, frame = cap.read()
        cap.release()

        if not ret:
            return "Error: Could not capture frame from webcam."

        timestamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = _DESKTOP / f"webcam_{timestamp}.png"

        cv2.imwrite(str(filepath), frame)

        return f"Webcam image captured: {filepath}"

    except ImportError:
        return "Webcam capture requires OpenCV. Install: pip install opencv-python"
    except Exception as e:
        return f"Error capturing webcam: {e}"


@tool
def analyze_screenshot() -> str:
    """Take a screenshot and analyze its content.

    Returns:
        A description of what's on screen.
    """
    try:
        import platform

        system = platform.system()
        timestamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = _DESKTOP / f"screenshot_analysis_{timestamp}.png"

        if system == "Windows":
            try:
                from PIL import ImageGrab

                img = ImageGrab.grab()
                img.save(str(filepath))
            except ImportError:
                return "Screenshot requires Pillow. Install: pip install Pillow"
        elif system == "Darwin":
            import subprocess
            subprocess.run(["screencapture", str(filepath)])
        else:
            import subprocess
            subprocess.run(["gnome-screenshot", "-f", str(filepath)])

        if not filepath.exists():
            return "Error: Could not take screenshot."

        result = analyze_image(str(filepath))

        return f"Screenshot captured and analyzed:\nPath: {filepath}\n\n{result}"

    except Exception as e:
        return f"Error analyzing screenshot: {e}"


vision_tools = [analyze_image, ocr_image, capture_webcam, analyze_screenshot]
