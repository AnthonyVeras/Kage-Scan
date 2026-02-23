"""
Kage Scan — Text Detection Service
Wraps comic-text-detector with lazy-loaded singleton + asyncio.to_thread.
"""

import asyncio
from pathlib import Path

import cv2
import numpy as np
from loguru import logger


class TextDetector:
    """
    Detects text regions (speech bubbles, SFX, etc.) in manga/comic pages.
    Uses comic-text-detector under the hood.
    Model is loaded lazily on first call and reused across requests.
    """

    _instance: "TextDetector | None" = None
    _model = None

    def __new__(cls) -> "TextDetector":
        """Singleton — only one detector instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self) -> None:
        """Lazy-load the comic-text-detector model on first use."""
        if self._model is not None:
            return

        logger.info("⏳ Loading comic-text-detector model (first run)...")
        try:
            from comic_text_detector import TextDetector as CTDModel

            self._model = CTDModel(
                model_path="",  # Uses default bundled model
                device="cpu",   # Switch to "cuda" if GPU available
            )
            logger.info("✅ comic-text-detector model loaded")
        except ImportError:
            logger.warning(
                "comic-text-detector not installed. "
                "Using fallback contour-based detection."
            )
            self._model = "fallback"

    def _detect_sync(self, image_path: str) -> list[dict]:
        """
        Run text detection synchronously.
        Returns list of bounding boxes: [{"x", "y", "w", "h"}, ...]
        """
        self._load_model()

        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Could not read image: {image_path}")
            return []

        if self._model == "fallback":
            return self._detect_fallback(img)

        # ── comic-text-detector inference ──────────────────────────
        try:
            result = self._model.detect(img)

            bboxes = []
            # result.bboxes is typically a numpy array of shape (N, 4, 2)
            # representing polygon corners, or (N, 4) for xyxy format
            if hasattr(result, "bboxes") and result.bboxes is not None:
                for bbox in result.bboxes:
                    bbox = np.array(bbox)

                    if bbox.ndim == 2:
                        # Polygon format (4 corners): convert to xyxy
                        x_min = int(bbox[:, 0].min())
                        y_min = int(bbox[:, 1].min())
                        x_max = int(bbox[:, 0].max())
                        y_max = int(bbox[:, 1].max())
                    elif bbox.ndim == 1 and len(bbox) == 4:
                        # xyxy format
                        x_min, y_min, x_max, y_max = map(int, bbox)
                    else:
                        continue

                    w = x_max - x_min
                    h = y_max - y_min

                    # Filter out tiny noise boxes
                    if w > 10 and h > 10:
                        bboxes.append({"x": x_min, "y": y_min, "w": w, "h": h})

            logger.info(f"Detected {len(bboxes)} text regions in {Path(image_path).name}")
            return bboxes

        except Exception as e:
            logger.error(f"Detection failed, falling back to contours: {e}")
            return self._detect_fallback(img)

    def _detect_fallback(self, img: np.ndarray) -> list[dict]:
        """
        Fallback contour-based detection when comic-text-detector
        is unavailable. Good enough for testing the pipeline.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Adaptive threshold to isolate text-like regions
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 25, 10,
        )

        # Dilate to merge nearby characters into blocks
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 20))
        dilated = cv2.dilate(binary, kernel, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        img_h, img_w = img.shape[:2]
        min_area = (img_h * img_w) * 0.001  # At least 0.1% of image area
        max_area = (img_h * img_w) * 0.5    # No more than 50% of image area

        bboxes = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            if min_area < area < max_area and w > 15 and h > 15:
                bboxes.append({"x": x, "y": y, "w": w, "h": h})

        # Sort top-to-bottom, right-to-left (manga reading order)
        bboxes.sort(key=lambda b: (b["x"] // 100, b["y"]))

        logger.info(f"Fallback detection found {len(bboxes)} regions")
        return bboxes

    async def detect(self, image_path: str) -> list[dict]:
        """
        Async wrapper — runs heavy detection in a thread pool.

        Args:
            image_path: Absolute path to the image file.

        Returns:
            List of bounding boxes [{"x", "y", "w", "h"}, ...]
        """
        return await asyncio.to_thread(self._detect_sync, image_path)
