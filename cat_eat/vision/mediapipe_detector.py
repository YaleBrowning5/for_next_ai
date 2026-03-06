"""MediaPipe-based cat / animal detector.

Uses MediaPipe's Object Detector (COCO SSD lite) which can detect *cats*
(COCO class 15) and falls back to a bounding-box around any detected animal.

The detector is designed to be instantiated once and called from the
*detection thread* in the pipeline — it is **not** thread-safe by itself.

Detection result schema
-----------------------
Each result is a dict::

    {
        "bbox": (x, y, w, h),   # pixel coordinates in the source frame
        "confidence": float,     # detection confidence [0, 1]
        "label": str,            # e.g. "cat"
        "frame": np.ndarray,     # cropped ROI (used for embedding)
    }
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# COCO class IDs that we treat as "cat" detections.
# MediaPipe Object Detector uses COCO labels.
_CAT_LABELS = {"cat", "Cat"}


class DetectionResult:
    """Immutable detection result."""

    __slots__ = ("bbox", "confidence", "label", "roi")

    def __init__(
        self,
        bbox: Tuple[int, int, int, int],
        confidence: float,
        label: str,
        roi: np.ndarray,
    ) -> None:
        self.bbox = bbox            # (x, y, w, h)
        self.confidence = confidence
        self.label = label
        self.roi = roi              # cropped region of the source frame

    def to_dict(self) -> dict:
        return {
            "bbox": self.bbox,
            "confidence": self.confidence,
            "label": self.label,
        }

    def __repr__(self) -> str:
        return (
            f"DetectionResult(label={self.label!r}, "
            f"confidence={self.confidence:.2f}, bbox={self.bbox})"
        )


class MediaPipeDetector:
    """Wraps MediaPipe Object Detector to identify cats in frames.

    Parameters
    ----------
    min_confidence:
        Minimum detection score; detections below this are ignored.
    model_asset_path:
        Path to a TFLite model file.  When *None* the detector tries to use
        the default EfficientDet-Lite0 model bundled with mediapipe.  Falls
        back to a ``NullDetector`` if mediapipe is unavailable (e.g. on CI).
    """

    def __init__(
        self,
        min_confidence: float = 0.5,
        model_asset_path: Optional[str] = None,
    ) -> None:
        self.min_confidence = min_confidence
        self._detector = None
        self._available = False
        self._init_detector(model_asset_path)

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_detector(self, model_asset_path: Optional[str]) -> None:
        try:
            import mediapipe as mp  # type: ignore

            BaseOptions = mp.tasks.BaseOptions
            ObjectDetector = mp.tasks.vision.ObjectDetector
            ObjectDetectorOptions = mp.tasks.vision.ObjectDetectorOptions
            VisionRunningMode = mp.tasks.vision.RunningMode

            options = ObjectDetectorOptions(
                base_options=BaseOptions(model_asset_path=model_asset_path or ""),
                running_mode=VisionRunningMode.IMAGE,
                score_threshold=self.min_confidence,
                max_results=5,
            )
            self._detector = ObjectDetector.create_from_options(options)
            self._available = True
            logger.info("MediaPipe ObjectDetector initialised (model=%s)", model_asset_path)
        except Exception as exc:
            logger.warning(
                "MediaPipe not available (%s) – using NullDetector fallback.", exc
            )
            self._available = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        return self._available

    def detect(self, frame: np.ndarray) -> List[DetectionResult]:
        """Run detection on *frame* (H×W×3, BGR or RGB uint8).

        Returns
        -------
        list[DetectionResult]
            All detections whose label is in ``_CAT_LABELS``.  Empty list
            when nothing is detected or the detector is unavailable.
        """
        if not self._available or frame is None or frame.size == 0:
            return []

        try:
            import mediapipe as mp  # type: ignore

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=frame if frame.shape[2] == 3 else frame[:, :, :3],
            )
            raw = self._detector.detect(mp_image)
            return self._parse_results(frame, raw)
        except Exception as exc:
            logger.error("Detection error: %s", exc)
            return []

    def close(self) -> None:
        if self._detector is not None:
            try:
                self._detector.close()
            except Exception:
                pass
            self._detector = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_results(self, frame: np.ndarray, raw_result) -> List[DetectionResult]:
        h, w = frame.shape[:2]
        results: List[DetectionResult] = []

        for detection in raw_result.detections:
            # mediapipe >= 0.10 uses detection.categories
            categories = getattr(detection, "categories", [])
            if not categories:
                continue
            top_cat = categories[0]
            label = top_cat.category_name or ""
            score = float(top_cat.score)
            if label not in _CAT_LABELS:
                continue

            bb = detection.bounding_box
            x = max(0, int(bb.origin_x))
            y = max(0, int(bb.origin_y))
            bw = min(int(bb.width), w - x)
            bh = min(int(bb.height), h - y)
            if bw <= 0 or bh <= 0:
                continue

            roi = frame[y : y + bh, x : x + bw].copy()
            results.append(DetectionResult((x, y, bw, bh), score, label, roi))

        return results
