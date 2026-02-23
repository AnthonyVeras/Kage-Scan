"""
Kage Scan — Inpainting Service
Generates masks from bounding boxes and uses LaMa (via IOPaint) to erase original text.
"""

import asyncio
from pathlib import Path

import cv2
import numpy as np
from loguru import logger


class Inpainter:
    """
    Erases original text from manga pages using LaMa inpainting.
    - Generates binary masks from bounding box coordinates.
    - Uses IOPaint's LaMa model for high-quality removal.
    - Falls back to OpenCV's built-in inpainting if IOPaint is unavailable.
    """

    _instance: "Inpainter | None" = None
    _model = None

    def __new__(cls) -> "Inpainter":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self) -> None:
        """Lazy-load the IOPaint LaMa model."""
        if self._model is not None:
            return

        logger.info("⏳ Loading IOPaint LaMa model (first run)...")
        try:
            from iopaint.model_manager import ModelManager

            self._model = ModelManager(name="lama", device="cpu")
            logger.info("✅ IOPaint LaMa model loaded")
        except ImportError:
            logger.warning(
                "IOPaint not installed or model unavailable. "
                "Using OpenCV Telea inpainting as fallback."
            )
            self._model = "fallback"
        except Exception as e:
            logger.warning(f"IOPaint init failed ({e}). Using OpenCV fallback.")
            self._model = "fallback"

    @staticmethod
    def _create_mask(
        img_shape: tuple[int, int],
        bboxes: list[dict],
        padding: int = 5,
    ) -> np.ndarray:
        """
        Generate a binary mask image from bounding boxes.
        White (255) = areas to inpaint, Black (0) = keep.

        Args:
            img_shape: (height, width) of the original image.
            bboxes: List of {"x", "y", "w", "h"} dicts.
            padding: Extra pixels around each bbox for cleaner removal.
        """
        h, w = img_shape
        mask = np.zeros((h, w), dtype=np.uint8)

        for bbox in bboxes:
            x1 = max(0, int(bbox["x"]) - padding)
            y1 = max(0, int(bbox["y"]) - padding)
            x2 = min(w, int(bbox["x"] + bbox["w"]) + padding)
            y2 = min(h, int(bbox["y"] + bbox["h"]) + padding)
            cv2.rectangle(mask, (x1, y1), (x2, y2), 255, thickness=-1)

        return mask

    def _inpaint_sync(self, image_path: str, bboxes: list[dict]) -> str:
        """
        Synchronous inpainting — runs in thread pool.
        Returns the path to the cleaned image.
        """
        self._load_model()

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")

        h, w = img.shape[:2]
        mask = self._create_mask((h, w), bboxes)

        # Build output path: original_cleaned.png
        src = Path(image_path)
        output_path = src.parent / f"{src.stem}_cleaned{src.suffix}"

        if self._model == "fallback":
            # ── OpenCV fallback inpainting ─────────────────────────
            result = cv2.inpaint(img, mask, inpaintRadius=7, flags=cv2.INPAINT_TELEA)
            logger.debug("Used OpenCV Telea inpainting (fallback)")
        else:
            # ── IOPaint LaMa ───────────────────────────────────────
            try:
                # IOPaint expects RGB image and mask
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                result_rgb = self._model(img_rgb, mask)
                result = cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)
                logger.debug("Used IOPaint LaMa inpainting")
            except Exception as e:
                logger.warning(f"IOPaint failed ({e}), falling back to OpenCV")
                result = cv2.inpaint(img, mask, inpaintRadius=7, flags=cv2.INPAINT_TELEA)

        cv2.imwrite(str(output_path), result)
        logger.info(f"Cleaned image saved: {output_path.name}")

        return str(output_path)

    async def clean_image(self, image_path: str, bboxes: list[dict]) -> str:
        """
        Async wrapper — erases text regions from an image.

        Args:
            image_path: Absolute path to the original image.
            bboxes: List of bounding boxes [{"x", "y", "w", "h"}, ...]

        Returns:
            Path to the cleaned (inpainted) image.

        Raises:
            ValueError: If the image cannot be read.
        """
        if not bboxes:
            logger.debug(f"No bboxes to inpaint for {Path(image_path).name}")
            return image_path  # Return original if nothing to clean

        return await asyncio.to_thread(self._inpaint_sync, image_path, bboxes)
