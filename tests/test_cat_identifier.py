"""Unit tests for CatIdentifier and embedding helpers."""

import unittest

import numpy as np

from cat_eat.vision.embedding import (
    _l2_normalise,
    compute_embedding,
    cosine_similarity,
)
from cat_eat.vision.cat_identifier import CatIdentifier, CatProfile
from cat_eat.vision.mediapipe_detector import DetectionResult


def _make_roi(h: int = 64, w: int = 64, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 255, (h, w, 3), dtype=np.uint8)


class TestEmbedding(unittest.TestCase):

    def test_compute_embedding_returns_correct_dim(self):
        roi = _make_roi()
        emb = compute_embedding(roi, dim=128)
        self.assertIsNotNone(emb)
        self.assertEqual(emb.shape, (128,))

    def test_compute_embedding_is_l2_normalised(self):
        emb = compute_embedding(_make_roi(), dim=64)
        self.assertAlmostEqual(float(np.linalg.norm(emb)), 1.0, places=5)

    def test_compute_embedding_none_for_empty_roi(self):
        self.assertIsNone(compute_embedding(np.array([]), dim=128))
        self.assertIsNone(compute_embedding(None, dim=128))

    def test_cosine_similarity_identical(self):
        v = _l2_normalise(np.random.rand(64).astype(np.float32))
        self.assertAlmostEqual(cosine_similarity(v, v), 1.0, places=5)

    def test_cosine_similarity_orthogonal(self):
        a = np.zeros(4, dtype=np.float32)
        b = np.zeros(4, dtype=np.float32)
        a[0] = 1.0
        b[1] = 1.0
        self.assertAlmostEqual(cosine_similarity(a, b), 0.0, places=5)

    def test_cosine_similarity_none_returns_zero(self):
        v = np.ones(4, dtype=np.float32) / 2.0
        self.assertEqual(cosine_similarity(None, v), 0.0)
        self.assertEqual(cosine_similarity(v, None), 0.0)

    def test_cosine_similarity_clamped(self):
        # Craft slightly out-of-bound values due to float precision
        v = np.array([1.0000001], dtype=np.float32)
        result = cosine_similarity(v, v)
        self.assertLessEqual(result, 1.0)
        self.assertGreaterEqual(result, -1.0)


class TestCatProfile(unittest.TestCase):

    def test_best_similarity_empty_profile(self):
        p = CatProfile(name="MiaoMiao")
        emb = compute_embedding(_make_roi(), dim=64)
        self.assertEqual(p.best_similarity(emb), 0.0)

    def test_best_similarity_returns_max(self):
        p = CatProfile(name="Cat")
        emb_a = compute_embedding(_make_roi(seed=1), dim=64)
        emb_b = compute_embedding(_make_roi(seed=2), dim=64)
        query = compute_embedding(_make_roi(seed=1), dim=64)
        p.add_embedding(emb_a)
        p.add_embedding(emb_b)
        result = p.best_similarity(query)
        self.assertGreater(result, 0.0)


class TestCatIdentifier(unittest.TestCase):

    def _make_roi_for_cat(self, seed: int) -> np.ndarray:
        rng = np.random.default_rng(seed)
        return rng.integers(0, 255, (32, 32, 3), dtype=np.uint8)

    def test_register_and_has_profile(self):
        ident = CatIdentifier(similarity_threshold=0.5, embedding_dim=64)
        emb = compute_embedding(_make_roi(), dim=64)
        ident.register("MiaoMiao", [emb])
        self.assertTrue(ident.has_profile("MiaoMiao"))

    def test_list_cats(self):
        ident = CatIdentifier(embedding_dim=64)
        emb = compute_embedding(_make_roi(), dim=64)
        ident.register("cat_a", [emb])
        ident.register("cat_b", [emb])
        cats = ident.list_cats()
        self.assertIn("cat_a", cats)
        self.assertIn("cat_b", cats)

    def test_identify_same_image_matches(self):
        """The same ROI used as reference and query should match (sim ≈ 1)."""
        ident = CatIdentifier(similarity_threshold=0.99, embedding_dim=128)
        roi = _make_roi(seed=42)
        emb = compute_embedding(roi, dim=128)
        ident.register("MiaoMiao", [emb])
        result = ident.identify_roi(roi)
        self.assertTrue(result.matched)
        self.assertEqual(result.cat_id, "MiaoMiao")
        self.assertAlmostEqual(result.similarity, 1.0, places=4)

    def test_identify_different_image_no_match(self):
        ident = CatIdentifier(similarity_threshold=0.99, embedding_dim=128)
        roi_ref = _make_roi(seed=1)
        roi_query = _make_roi(seed=99)
        emb = compute_embedding(roi_ref, dim=128)
        ident.register("cat_a", [emb])
        result = ident.identify_roi(roi_query)
        # Random images should not accidentally match at 0.99 threshold
        self.assertFalse(result.matched)

    def test_identify_no_profiles_returns_unmatched(self):
        ident = CatIdentifier(embedding_dim=64)
        result = ident.identify_roi(_make_roi())
        self.assertFalse(result.matched)
        self.assertIsNone(result.cat_id)

    def test_register_from_roi(self):
        ident = CatIdentifier(embedding_dim=64)
        roi = _make_roi()
        success = ident.register_from_roi("TabbyTom", roi)
        self.assertTrue(success)
        self.assertTrue(ident.has_profile("TabbyTom"))

    def test_identify_detection_result(self):
        ident = CatIdentifier(similarity_threshold=0.99, embedding_dim=128)
        roi = _make_roi(seed=7)
        emb = compute_embedding(roi, dim=128)
        ident.register("Nyan", [emb])
        det = DetectionResult(bbox=(0, 0, 32, 32), confidence=0.9, label="cat", roi=roi)
        result = ident.identify(det)
        self.assertTrue(result.matched)

    def test_max_embeddings_per_cat_enforced(self):
        ident = CatIdentifier(embedding_dim=32, max_embeddings_per_cat=3)
        for i in range(5):
            ident.register_from_roi("cat", _make_roi(seed=i))
        self.assertLessEqual(len(ident._profiles["cat"].embeddings), 3)


if __name__ == "__main__":
    unittest.main()
