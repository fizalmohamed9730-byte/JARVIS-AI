"""Vision engine for image capture and analysis."""

import io
import logging
from typing import List, Optional, Tuple
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
import pytesseract
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Face:
    """Represents a detected face."""
    x: int
    y: int
    width: int
    height: int
    confidence: float
    landmarks: Optional[dict] = None


@dataclass
class DetectedObject:
    """Represents a detected object."""
    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]
    class_id: int


@dataclass
class ImageMetadata:
    """Image metadata information."""
    width: int
    height: int
    format: str
    mode: str
    file_size: int
    dpi: Optional[Tuple[int, int]] = None


class VisionEngine:
    """Main vision engine for image capture and analysis."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self._webcam: Optional[cv2.VideoCapture] = None
        self._face_cascade: Optional[cv2.CascadeClassifier] = None
        self._initialized = False
        self._model = None
        self._class_names: List[str] = []

    async def initialize(self) -> None:
        """Initialize vision engine resources."""
        if self._initialized:
            return

        logger.info("Initializing vision engine...")

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._face_cascade = cv2.CascadeClassifier(cascade_path)

        self._load_object_detection_model()

        self._initialized = True
        logger.info("Vision engine initialized successfully")

    def _load_object_detection_model(self) -> None:
        """Load YOLO model for object detection."""
        try:
            config_dir = Path(self.config.get("models_dir", "models"))
            weights_path = config_dir / "yolov4-tiny.weights"
            config_path = config_dir / "yolov4-tiny.cfg"
            coco_path = config_dir / "coco.names"

            if weights_path.exists() and config_path.exists():
                self._model = cv2.dnn.readNetFromDarknet(
                    str(config_path), str(weights_path)
                )
                if self.config.get("use_gpu", False):
                    self._model.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
                    self._model.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
                else:
                    self._model.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                    self._model.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

                if coco_path.exists():
                    with open(coco_path, "r") as f:
                        self._class_names = [line.strip() for line in f.readlines()]

                logger.info("Object detection model loaded")
            else:
                logger.warning("YOLO weights not found, object detection disabled")
        except Exception as e:
            logger.error(f"Failed to load object detection model: {e}")

    async def capture_webcam(self) -> np.ndarray:
        """Capture frame from webcam."""
        if self._webcam is None or not self._webcam.isOpened():
            self._webcam = cv2.VideoCapture(0)
            if not self._webcam.isOpened():
                raise RuntimeError("Cannot access webcam")

            self._webcam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self._webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        ret, frame = self._webcam.read()
        if not ret:
            raise RuntimeError("Failed to capture frame from webcam")

        return frame

    async def capture_screenshot(self) -> np.ndarray:
        """Capture screenshot of primary display."""
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            return frame
        except ImportError:
            logger.warning("pyautogui not installed, using alternative method")
            import subprocess
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name

            if self._platform == "win32":
                subprocess.run(["screenshot", tmp_path], check=True)
            else:
                subprocess.run(["scrot", tmp_path], check=True)

            frame = cv2.imread(tmp_path)
            Path(tmp_path).unlink(missing_ok=True)
            return frame

    @property
    def _platform(self) -> str:
        import sys
        return sys.platform

    async def analyze_image(self, image: np.ndarray) -> str:
        """Analyze image and return description."""
        try:
            import base64

            _, buffer = cv2.imencode(".jpg", image)
            image_bytes = buffer.tobytes()
            base64_image = base64.b64encode(image_bytes).decode("utf-8")

            api_key = self.config.get("openai_api_key")
            if api_key:
                description = await self._analyze_with_gpt4v(base64_image, api_key)
                return description

            objects = await self.detect_objects(image)
            faces = await self.face_detect(image)

            description = self._generate_local_description(image, objects, faces)
            return description

        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return f"Analysis failed: {str(e)}"

    async def _analyze_with_gpt4v(self, base64_image: str, api_key: str) -> str:
        """Analyze image using GPT-4V API."""
        import aiohttp

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Describe this image in detail. Include any text, objects, people, and the overall scene."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1000
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error = await response.text()
                    raise RuntimeError(f"GPT-4V API error: {error}")

    def _generate_local_description(
        self,
        image: np.ndarray,
        objects: List[DetectedObject],
        faces: List[Face]
    ) -> str:
        """Generate description from local analysis."""
        height, width = image.shape[:2]
        parts = [f"Image size: {width}x{height}"]

        if objects:
            obj_labels = [f"{obj.label} ({obj.confidence:.1%})" for obj in objects]
            parts.append(f"Objects detected: {', '.join(obj_labels)}")
        else:
            parts.append("No objects detected")

        if faces:
            parts.append(f"Faces detected: {len(faces)}")
        else:
            parts.append("No faces detected")

        brightness = np.mean(image)
        if brightness < 50:
            parts.append("Scene is dark")
        elif brightness > 200:
            parts.append("Scene is bright")
        else:
            parts.append("Scene has normal lighting")

        return ". ".join(parts)

    async def ocr(self, image: np.ndarray) -> str:
        """Extract text from image using OCR."""
        try:
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            text = pytesseract.image_to_string(pil_image)
            return text.strip()
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""

    async def detect_objects(self, image: np.ndarray) -> List[DetectedObject]:
        """Detect objects in image using YOLO."""
        if self._model is None:
            logger.warning("Object detection model not loaded")
            return []

        try:
            height, width = image.shape[:2]

            blob = cv2.dnn.blobFromImage(
                image, 1 / 255.0, (416, 416), swapRB=True, crop=False
            )
            self._model.setInput(blob)

            output_layers = self._model.getUnconnectedOutLayersNames()
            outputs = self._model.forward(output_layers)

            boxes = []
            confidences = []
            class_ids = []

            for output in outputs:
                for detection in output:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]

                    if confidence > self.config.get("detection_threshold", 0.5):
                        center_x = int(detection[0] * width)
                        center_y = int(detection[1] * height)
                        w = int(detection[2] * width)
                        h = int(detection[3] * height)

                        x = int(center_x - w / 2)
                        y = int(center_y - h / 2)

                        boxes.append([x, y, w, h])
                        confidences.append(float(confidence))
                        class_ids.append(class_id)

            indices = cv2.dnn.NMSBoxes(
                boxes, confidences,
                self.config.get("detection_threshold", 0.5),
                self.config.get("nms_threshold", 0.4)
            )

            results = []
            if len(indices) > 0:
                for i in indices.flatten():
                    label = (
                        self._class_names[class_ids[i]]
                        if class_ids[i] < len(self._class_names)
                        else f"class_{class_ids[i]}"
                    )
                    results.append(DetectedObject(
                        label=label,
                        confidence=confidences[i],
                        bbox=(boxes[i][0], boxes[i][1], boxes[i][2], boxes[i][3]),
                        class_id=class_ids[i]
                    ))

            return results

        except Exception as e:
            logger.error(f"Object detection failed: {e}")
            return []

    async def face_detect(self, image: np.ndarray) -> List[Face]:
        """Detect faces in image."""
        if self._face_cascade is None:
            logger.warning("Face cascade not loaded")
            return []

        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            faces_raw = self._face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )

            faces = []
            for x, y, w, h in faces_raw:
                faces.append(Face(
                    x=int(x),
                    y=int(y),
                    width=int(w),
                    height=int(h),
                    confidence=0.95
                ))

            return faces

        except Exception as e:
            logger.error(f"Face detection failed: {e}")
            return []

    async def compare_faces(
        self, image1: np.ndarray, image2: np.ndarray
    ) -> float:
        """Compare faces in two images and return similarity score."""
        try:
            faces1 = await self.face_detect(image1)
            faces2 = await self.face_detect(image2)

            if not faces1 or not faces2:
                return 0.0

            face1 = faces1[0]
            face2 = faces2[0]

            roi1 = image1[
                face1.y:face1.y + face1.height,
                face1.x:face1.x + face1.width
            ]
            roi2 = image2[
                face2.y:face2.y + face2.height,
                face2.x:face2.x + face2.width
            ]

            roi1_gray = cv2.cvtColor(roi1, cv2.COLOR_BGR2GRAY)
            roi2_gray = cv2.cvtColor(roi2, cv2.COLOR_BGR2GRAY)

            roi1_resized = cv2.resize(roi1_gray, (100, 100))
            roi2_resized = cv2.resize(roi2_gray, (100, 100))

            diff = cv2.absdiff(roi1_resized, roi2_resized)
            similarity = 1.0 - (np.mean(diff) / 255.0)

            return float(similarity)

        except Exception as e:
            logger.error(f"Face comparison failed: {e}")
            return 0.0

    async def shutdown(self) -> None:
        """Cleanup resources."""
        if self._webcam and self._webcam.isOpened():
            self._webcam.release()
            self._webcam = None

        self._model = None
        self._face_cascade = None
        self._initialized = False
        logger.info("Vision engine shut down")
