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
        Fallback detection using Canny edges + morphological closing.
        Targets speech bubble outlines (closed curves on white background).
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img_h, img_w = img.shape[:2]

        # ── Step 1: Edge detection to find bubble borders ──────
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 30, 100)

        # Close gaps in bubble outlines so they form closed shapes
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

        # ── Step 2: Find contours from closed edges ────────────
        contours, hierarchy = cv2.findContours(
            closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE,
        )

        min_area = (img_h * img_w) * 0.01    # At least 1% of image
        max_area = (img_h * img_w) * 0.25    # No more than 25% of image

        bboxes = []
        for i, cnt in enumerate(contours):
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h

            # Size filter
            if area < min_area or area > max_area:
                continue
            if w < 50 or h < 50:
                continue

            # Aspect ratio filter (real bubbles are roundish)
            aspect = max(w, h) / min(w, h)
            if aspect > 3.5:
                continue

            # ── Step 3: White-interior check ──────────────────
            # Speech bubbles have mostly white/light interiors
            roi = gray[y:y+h, x:x+w]
            if roi.size == 0:
                continue

            mean_brightness = roi.mean()
            # Bubbles are bright inside (white paper), reject dark regions
            if mean_brightness < 200:
                continue

            # Check what percentage of the interior is white (>200)
            white_ratio = (roi > 200).sum() / roi.size
            if white_ratio < 0.65:
                continue

            bboxes.append({"x": x, "y": y, "w": w, "h": h})

        # Remove duplicate/overlapping bboxes
        bboxes = self._remove_overlapping(bboxes)

        # Sort top-to-bottom, right-to-left (manga reading order)
        bboxes.sort(key=lambda b: (-b["x"], b["y"]))

        logger.info(f"Fallback detection found {len(bboxes)} bubble regions")
        return bboxes

    @staticmethod
    def _remove_overlapping(bboxes: list[dict], iou_threshold: float = 0.5) -> list[dict]:
        """Remove overlapping bboxes, keeping the larger one."""
        if not bboxes:
            return []

        # Sort by area (largest first)
        sorted_boxes = sorted(bboxes, key=lambda b: b["w"] * b["h"], reverse=True)
        keep = []

        for box in sorted_boxes:
            overlapping = False
            for kept in keep:
                # Calculate IoU
                x1 = max(box["x"], kept["x"])
                y1 = max(box["y"], kept["y"])
                x2 = min(box["x"] + box["w"], kept["x"] + kept["w"])
                y2 = min(box["y"] + box["h"], kept["y"] + kept["h"])

                if x1 < x2 and y1 < y2:
                    intersection = (x2 - x1) * (y2 - y1)
                    box_area = box["w"] * box["h"]
                    kept_area = kept["w"] * kept["h"]
                    union = box_area + kept_area - intersection
                    iou = intersection / union if union > 0 else 0

                    if iou > iou_threshold:
                        overlapping = True
                        break

            if not overlapping:
                keep.append(box)

        return keep

    async def detect(self, image_path: str) -> list[dict]:
        """
        Async wrapper — runs heavy detection in a thread pool.

        Args:
            image_path: Absolute path to the image file.

        Returns:
            List of bounding boxes [{"x", "y", "w", "h"}, ...]
        """
        return await asyncio.to_thread(self._detect_sync, image_path)
