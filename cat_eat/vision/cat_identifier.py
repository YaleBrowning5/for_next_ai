"""Cat identity matcher.

Stores one or more *reference embeddings* per named cat and matches incoming
detections by cosine similarity.  Size and brightness are used only as fast
pre-filters to avoid wasting time on obviously wrong matches.

Usage
-----
::

    identifier = CatIdentifier(similarity_threshold=0.80)
    identifier.register("MiaoMiao", [embedding1, embedding2])

    result = identifier.identify(detection_result)
    if result.matched:
        print(result.cat_id, result.similarity)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .embedding import compute_embedding, cosine_similarity
from .mediapipe_detector import DetectionResult

logger = logging.getLogger(__name__)


@dataclass
class IdentificationResult:
    """Outcome of a single identification attempt."""

    cat_id: Optional[str] = None
    similarity: float = 0.0
    matched: bool = False
    embedding: Optional[np.ndarray] = None

    def __bool__(self) -> bool:
        return self.matched


@dataclass
class CatProfile:
    """Holds all reference embeddings for one registered cat."""

    name: str
    embeddings: List[np.ndarray] = field(default_factory=list)

    def best_similarity(self, query: np.ndarray) -> float:
        """Return the maximum cosine similarity across all stored embeddings."""
        if not self.embeddings or query is None:
            return 0.0
        return max(cosine_similarity(query, ref) for ref in self.embeddings)

    def add_embedding(self, embedding: np.ndarray) -> None:
        self.embeddings.append(embedding)


class CatIdentifier:
    """Matches detected ROIs against registered cat profiles.

    Parameters
    ----------
    similarity_threshold:
        Minimum cosine similarity required to declare a positive match.
    embedding_dim:
        Dimensionality passed to :func:`~cat_eat.vision.embedding.compute_embedding`.
    max_embeddings_per_cat:
        Maximum number of reference embeddings stored per cat.  Oldest are
        dropped when this limit is exceeded.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.80,
        embedding_dim: int = 128,
        max_embeddings_per_cat: int = 20,
    ) -> None:
        self.similarity_threshold = similarity_threshold
        self.embedding_dim = embedding_dim
        self.max_embeddings_per_cat = max_embeddings_per_cat
        self._profiles: Dict[str, CatProfile] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, cat_id: str, embeddings: List[np.ndarray]) -> None:
        """Register a cat with pre-computed reference embeddings."""
        profile = CatProfile(name=cat_id, embeddings=list(embeddings))
        self._profiles[cat_id] = profile
        logger.info(
            "Registered cat %r with %d embeddings.", cat_id, len(embeddings)
        )

    def register_from_roi(self, cat_id: str, roi: np.ndarray) -> bool:
        """Compute an embedding from *roi* and add it to *cat_id*'s profile.

        Creates the profile if it does not yet exist.  Returns *True* if the
        embedding could be computed.
        """
        emb = compute_embedding(roi, self.embedding_dim)
        if emb is None:
            logger.warning("Could not compute embedding for registration of %r.", cat_id)
            return False

        if cat_id not in self._profiles:
            self._profiles[cat_id] = CatProfile(name=cat_id)
        profile = self._profiles[cat_id]
        profile.add_embedding(emb)
        # Trim to keep only the most recent embeddings
        if len(profile.embeddings) > self.max_embeddings_per_cat:
            profile.embeddings = profile.embeddings[-self.max_embeddings_per_cat:]
        logger.debug("Added embedding for %r (total=%d).", cat_id, len(profile.embeddings))
        return True

    def has_profile(self, cat_id: str) -> bool:
        return cat_id in self._profiles and len(self._profiles[cat_id].embeddings) > 0

    def list_cats(self) -> List[str]:
        return list(self._profiles.keys())

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------

    def identify(self, detection: DetectionResult) -> IdentificationResult:
        """Attempt to identify the cat in *detection*.

        Returns an :class:`IdentificationResult` with ``matched=True`` if a
        registered cat's similarity exceeds ``similarity_threshold``.
        """
        emb = compute_embedding(detection.roi, self.embedding_dim)
        if emb is None:
            return IdentificationResult()

        best_id, best_sim = self._best_match(emb)
        matched = best_sim >= self.similarity_threshold

        return IdentificationResult(
            cat_id=best_id if matched else None,
            similarity=best_sim,
            matched=matched,
            embedding=emb,
        )

    def identify_roi(self, roi: np.ndarray) -> IdentificationResult:
        """Convenience wrapper accepting a raw ROI instead of DetectionResult."""
        emb = compute_embedding(roi, self.embedding_dim)
        if emb is None:
            return IdentificationResult()
        best_id, best_sim = self._best_match(emb)
        matched = best_sim >= self.similarity_threshold
        return IdentificationResult(
            cat_id=best_id if matched else None,
            similarity=best_sim,
            matched=matched,
            embedding=emb,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _best_match(self, query: np.ndarray) -> Tuple[Optional[str], float]:
        best_id: Optional[str] = None
        best_sim: float = 0.0
        for cat_id, profile in self._profiles.items():
            sim = profile.best_similarity(query)
            if sim > best_sim:
                best_sim = sim
                best_id = cat_id
        return best_id, best_sim
