"""Image processing utilities for JARVIS."""

import io
import logging
from typing import List, Optional, Tuple, Union
from pathlib import Path
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ExifTags

logger = logging.getLogger(__name__)


@dataclass
class ImageMetadata:
    """Image metadata information."""
    width: int
    height: int
    format: str
    mode: str
    file_size: int
    dpi: Optional[Tuple[int, int]] = None
    exif: Optional[dict] = None


class ImageProcessor:
    """Image processing utilities for manipulation and enhancement."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self._max_size = self.config.get("max_image_size", 4096)

    def resize(
        self,
        image: np.ndarray,
        dimensions: Tuple[int, int],
        maintain_aspect: bool = True
    ) -> np.ndarray:
        """Resize image to specified dimensions."""
        try:
            if maintain_aspect:
                h, w = image.shape[:2]
                target_w, target_h = dimensions

                scale = min(target_w / w, target_h / h)
                new_w = int(w * scale)
                new_h = int(h * scale)

                resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

                canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)
                x_offset = (target_w - new_w) // 2
                y_offset = (target_h - new_h) // 2
                canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

                return canvas
            else:
                return cv2.resize(image, dimensions, interpolation=cv2.INTER_AREA)

        except Exception as e:
            logger.error(f"Resize failed: {e}")
            return image

    def crop(
        self,
        image: np.ndarray,
        region: Tuple[int, int, int, int]
    ) -> np.ndarray:
        """Crop image to specified region (x, y, width, height)."""
        try:
            x, y, w, h = region
            height, width = image.shape[:2]

            x = max(0, min(x, width))
            y = max(0, min(y, height))
            w = max(1, min(w, width - x))
            h = max(1, min(h, height - y))

            return image[y:y + h, x:x + w].copy()

        except Exception as e:
            logger.error(f"Crop failed: {e}")
            return image

    def enhance(self, image: np.ndarray) -> np.ndarray:
        """Enhance image quality automatically."""
        try:
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

            pil_image = ImageEnhance.Contrast(pil_image).enhance(1.2)
            pil_image = ImageEnhance.Brightness(pil_image).enhance(1.1)
            pil_image = ImageEnhance.Color(pil_image).enhance(1.15)
            pil_image = ImageEnhance.Sharpness(pil_image).enhance(1.3)

            enhanced = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

            lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)

            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)

            enhanced = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

            return enhanced

        except Exception as e:
            logger.error(f"Enhancement failed: {e}")
            return image

    def convert_format(
        self,
        image: np.ndarray,
        target_format: str
    ) -> bytes:
        """Convert image to specified format."""
        try:
            format_map = {
                "jpg": ".jpg",
                "jpeg": ".jpg",
                "png": ".png",
                "bmp": ".bmp",
                "tiff": ".tiff",
                "webp": ".webp"
            }

            ext = format_map.get(target_format.lower(), ".png")

            encode_params = []
            if ext in [".jpg", ".jpeg"]:
                quality = self.config.get("jpeg_quality", 95)
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
            elif ext == ".png":
                compression = self.config.get("png_compression", 6)
                encode_params = [cv2.IMWRITE_PNG_COMPRESSION, compression]
            elif ext == ".webp":
                quality = self.config.get("webp_quality", 90)
                encode_params = [cv2.IMWRITE_WEBP_QUALITY, quality]

            success, buffer = cv2.imencode(ext, image, encode_params)
            if not success:
                raise RuntimeError(f"Failed to encode image to {target_format}")

            return buffer.tobytes()

        except Exception as e:
            logger.error(f"Format conversion failed: {e}")
            return image.tobytes()

    def extract_metadata(self, image_path: str) -> ImageMetadata:
        """Extract metadata from image file."""
        try:
            path = Path(image_path)
            file_size = path.stat().st_size

            with Image.open(image_path) as pil_image:
                width, height = pil_image.size
                fmt = pil_image.format or "Unknown"
                mode = pil_image.mode

                dpi = pil_image.info.get("dpi")

                exif_data = {}
                if hasattr(pil_image, "_getexif") and pil_image._getexif():
                    for tag_id, value in pil_image._getexif().items():
                        tag = ExifTags.TAGS.get(tag_id, tag_id)
                        exif_data[tag] = str(value)

                return ImageMetadata(
                    width=width,
                    height=height,
                    format=fmt,
                    mode=mode,
                    file_size=file_size,
                    dpi=dpi,
                    exif=exif_data if exif_data else None
                )

        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            h, w = image_path.shape[:2] if isinstance(image_path, np.ndarray) else (0, 0)
            return ImageMetadata(
                width=w,
                height=h,
                format="Unknown",
                mode="Unknown",
                file_size=0
            )

    def create_thumbnail(
        self,
        image: np.ndarray,
        size: Tuple[int, int] = (128, 128)
    ) -> np.ndarray:
        """Create thumbnail of image."""
        try:
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            pil_image.thumbnail(size, Image.Resampling.LANCZOS)
            return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        except Exception as e:
            logger.error(f"Thumbnail creation failed: {e}")
            return cv2.resize(image, size)

    def batch_process(
        self,
        images: List[np.ndarray],
        operations: List[str]
    ) -> List[np.ndarray]:
        """Process multiple images with specified operations."""
        results = []

        operation_map = {
            "resize": lambda img: self.resize(img, (800, 600)),
            "enhance": lambda img: self.enhance(img),
            "thumbnail": lambda img: self.create_thumbnail(img),
            "grayscale": lambda img: cv2.cvtColor(
                cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR
            ),
            "blur": lambda img: cv2.GaussianBlur(img, (15, 15), 0),
            "sharpen": lambda img: cv2.filter2D(
                img, -1, np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            ),
            "normalize": lambda img: cv2.normalize(
                img, None, 0, 255, cv2.NORM_MINMAX
            )
        }

        for image in images:
            processed = image.copy()
            for op in operations:
                if op in operation_map:
                    processed = operation_map[op](processed)
                else:
                    logger.warning(f"Unknown operation: {op}")
            results.append(processed)

        return results

    def apply_filter(
        self,
        image: np.ndarray,
        filter_type: str
    ) -> np.ndarray:
        """Apply artistic filter to image."""
        filters = {
            "sepia": self._sepia_filter,
            "vintage": self._vintage_filter,
            "sketch": self._sketch_filter,
            "cartoon": self._cartoon_filter,
            "oil_painting": self._oil_painting_filter
        }

        filter_func = filters.get(filter_type)
        if filter_func:
            return filter_func(image)
        return image

    def _sepia_filter(self, image: np.ndarray) -> np.ndarray:
        """Apply sepia tone filter."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        sepia = np.zeros_like(image)
        sepia[:, :, 0] = np.clip(gray * 1.032, 0, 255)
        sepia[:, :, 1] = np.clip(gray * 0.869, 0, 255)
        sepia[:, :, 2] = np.clip(gray * 0.691, 0, 255)
        return sepia.astype(np.uint8)

    def _vintage_filter(self, image: np.ndarray) -> np.ndarray:
        """Apply vintage filter."""
        rows, cols = image.shape[:2]
        kernel = np.array([[0.272, 0.534, 0.131],
                           [0.349, 0.686, 0.168],
                           [0.393, 0.769, 0.189]])
        vintage = cv2.transform(image, kernel)

        vignette = np.zeros((rows, cols), dtype="float32")
        center_x, center_y = cols // 2, rows // 2
        Y, X = np.ogrid[:rows, :cols]
        dist = np.sqrt((X - center_x) ** 2 + (Y - center_y) ** 2)
        max_dist = np.sqrt(center_x ** 2 + center_y ** 2)
        vignette = 1 - (dist / max_dist)
        vignette = np.power(vignette, 1.5)

        for i in range(3):
            vintage[:, :, i] = (vintage[:, :, i] * vignette).astype(np.uint8)

        return np.clip(vintage, 0, 255).astype(np.uint8)

    def _sketch_filter(self, image: np.ndarray) -> np.ndarray:
        """Apply pencil sketch filter."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        inverted = 255 - gray
        blurred = cv2.GaussianBlur(inverted, (21, 21), 0)
        sketch = cv2.divide(gray, 255 - blurred, scale=256)
        return cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)

    def _cartoon_filter(self, image: np.ndarray) -> np.ndarray:
        """Apply cartoon filter."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 7)
        edges = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 9
        )

        color = cv2.bilateralFilter(image, 9, 300, 300)
        edges_3channel = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        cartoon = cv2.bitwise_and(color, edges_3channel)

        return cartoon

    def _oil_painting_filter(self, image: np.ndarray) -> np.ndarray:
        """Apply oil painting effect."""
        return cv2.stylization(image, sigma_s=60, sigma_r=0.07)

    def adjust_color_balance(
        self,
        image: np.ndarray,
        red: float = 1.0,
        green: float = 1.0,
        blue: float = 1.0
    ) -> np.ndarray:
        """Adjust color balance of image."""
        result = image.copy().astype(np.float32)
        result[:, :, 2] *= red
        result[:, :, 1] *= green
        result[:, :, 0] *= blue
        return np.clip(result, 0, 255).astype(np.uint8)

    def remove_background(self, image: np.ndarray) -> np.ndarray:
        """Remove simple solid-color background."""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            result = np.zeros_like(image)
            result[mask > 0] = image[mask > 0]

            return result

        except Exception as e:
            logger.error(f"Background removal failed: {e}")
            return image

    def create_collage(
        self,
        images: List[np.ndarray],
        layout: str = "grid",
        spacing: int = 10
    ) -> np.ndarray:
        """Create collage from multiple images."""
        if not images:
            raise ValueError("No images provided")

        n = len(images)
        target_size = (400, 300)
        resized = [
            cv2.resize(img, target_size, interpolation=cv2.INTER_AREA)
            for img in images
        ]

        if layout == "grid":
            cols = int(np.ceil(np.sqrt(n)))
            rows = int(np.ceil(n / cols))

            canvas_w = cols * (target_size[0] + spacing) + spacing
            canvas_h = rows * (target_size[1] + spacing) + spacing
            canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)

            for idx, img in enumerate(resized):
                row = idx // cols
                col = idx % cols
                x = spacing + col * (target_size[0] + spacing)
                y = spacing + row * (target_size[1] + spacing)
                canvas[y:y + target_size[1], x:x + target_size[0]] = img

            return canvas

        elif layout == "horizontal":
            total_w = n * (target_size[0] + spacing) + spacing
            canvas = np.zeros((target_size[1] + 2 * spacing, total_w, 3), dtype=np.uint8)
            for idx, img in enumerate(resized):
                x = spacing + idx * (target_size[0] + spacing)
                canvas[spacing:spacing + target_size[1], x:x + target_size[0]] = img
            return canvas

        elif layout == "vertical":
            total_h = n * (target_size[1] + spacing) + spacing
            canvas = np.zeros((total_h, target_size[0] + 2 * spacing, 3), dtype=np.uint8)
            for idx, img in enumerate(resized):
                y = spacing + idx * (target_size[1] + spacing)
                canvas[y:y + target_size[1], spacing:spacing + target_size[0]] = img
            return canvas

        return resized[0]
