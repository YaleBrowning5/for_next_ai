"""Embedding module: converts a cropped image ROI into a compact feature vector.

Design rationale
----------------
The embedding is the **primary** identification feature.  ``size`` and
``brightness`` are unstable under real-world lighting and distance variation
and are therefore relegated to fast pre-filters rather than primary features.

Algorithm
---------
1. Resize the ROI to ``TARGET_SIZE × TARGET_SIZE``.
2. Convert to float32 and L2-normalise per-channel.
3. Flatten to a 1-D vector of length ``EMBEDDING_DIM``.

When scikit-learn is available a small PCA can be applied to reduce
dimensionality further; for now we use a deterministic pixel-sampled approach
that requires only NumPy so the module works in all environments.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Size to which every ROI is resized before embedding
TARGET_SIZE: int = 32   # 32×32 × 3 channels = 3 072 dims → sampled to 128


def compute_embedding(roi: np.ndarray, dim: int = 128) -> Optional[np.ndarray]:
    """Compute a compact, L2-normalised embedding for *roi*.

    Parameters
    ----------
    roi:
        Cropped image region (H×W×3, uint8).  BGR or RGB order does not matter
        because we only care about relative similarity between embeddings of
        the same camera setup.
    dim:
        Desired embedding dimension (defaults to 128).

    Returns
    -------
    np.ndarray of shape (dim,), dtype float32, L2-normalised.
    Returns *None* if the ROI is invalid or empty.
    """
    if roi is None or roi.size == 0:
        return None

    try:
        resized = _resize(roi, TARGET_SIZE, TARGET_SIZE)
    except Exception as exc:
        logger.warning("Embedding resize failed: %s", exc)
        return None

    # Flatten and cast to float32
    flat = resized.astype(np.float32).flatten()  # length = TARGET_SIZE² × 3

    # Deterministic sub-sampling to the requested dimension
    if len(flat) > dim:
        indices = np.linspace(0, len(flat) - 1, dim, dtype=int)
        flat = flat[indices]
    elif len(flat) < dim:
        # Pad with zeros if the image is smaller than expected
        pad = np.zeros(dim, dtype=np.float32)
        pad[: len(flat)] = flat
        flat = pad

    return _l2_normalise(flat)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Return cosine similarity ∈ [-1, 1] between two L2-normalised vectors.

    Both *a* and *b* must have the same shape.  Because we always store
    L2-normalised embeddings the dot product equals the cosine similarity
    and is ~10× faster than calling ``scipy.spatial.distance.cosine``.
    """
    if a is None or b is None:
        return 0.0
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    if a.shape != b.shape or a.size == 0:
        return 0.0
    dot = float(np.dot(a, b))
    # Clamp to [-1, 1] to guard against floating-point drift
    return max(-1.0, min(1.0, dot))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resize(image: np.ndarray, width: int, height: int) -> np.ndarray:
    """Resize *image* to (height, width) using nearest-neighbour interpolation
    without requiring OpenCV."""
    try:
        import cv2  # type: ignore

        return cv2.resize(image, (width, height), interpolation=cv2.INTER_LINEAR)
    except ImportError:
        pass

    # Pure-NumPy fallback (nearest-neighbour)
    h, w = image.shape[:2]
    row_idx = (np.arange(height) * h / height).astype(int)
    col_idx = (np.arange(width) * w / width).astype(int)
    return image[np.ix_(row_idx, col_idx)]


def _l2_normalise(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    if norm < 1e-9:
        return v
    return v / norm
