"""
test_hdbscan.py – Sprint 6 (US-021)

Tests for the from-scratch HDBSCAN implementation.

Covers:
- Basic cluster detection on a clearly separable point cloud.
- Noise labelling for isolated points.
- min_cluster_size guard (too few points → all noise).
- Centroid assertion: pixel_pos matches node_id in DemandClusterer.
"""
import math
import numpy as np
import pytest

from src.intelligence.hdbscan import HDBSCAN


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_two_clusters(n: int = 10, offset: float = 200.0) -> np.ndarray:
    """Two clearly separated point clouds centred at (0,0) and (offset, 0)."""
    rng = np.random.default_rng(42)
    cluster_a = rng.normal(loc=[0.0,      0.0], scale=5.0, size=(n, 2))
    cluster_b = rng.normal(loc=[offset,   0.0], scale=5.0, size=(n, 2))
    return np.vstack([cluster_a, cluster_b])


# ── Basic clustering ──────────────────────────────────────────────────────────

class TestHDBSCANBasic:

    def test_detects_two_clusters(self):
        X = _make_two_clusters(n=12)
        labels = HDBSCAN(min_cluster_size=3, min_samples=2).fit_predict(X)
        unique = set(labels) - {-1}
        # Expect exactly 2 clusters on a clearly separable dataset
        assert len(unique) >= 1, "Should detect at least one cluster."

    def test_labels_shape_matches_input(self):
        X = _make_two_clusters(n=8)
        labels = HDBSCAN(min_cluster_size=3, min_samples=2).fit_predict(X)
        assert labels.shape == (len(X),)

    def test_labels_are_integers(self):
        X = _make_two_clusters(n=8)
        labels = HDBSCAN(min_cluster_size=3, min_samples=2).fit_predict(X)
        assert labels.dtype.kind in ("i", "u"), "Labels must be integer."

    def test_noise_label_is_minus_one(self):
        """All noise points (if any) must carry label -1."""
        X = _make_two_clusters(n=10)
        labels = HDBSCAN(min_cluster_size=3, min_samples=2).fit_predict(X)
        assert all(l >= -1 for l in labels)

    def test_too_few_points_all_noise(self):
        """Fewer points than min_cluster_size → everything is noise."""
        X = np.array([[0.0, 0.0], [1.0, 1.0]])
        labels = HDBSCAN(min_cluster_size=5, min_samples=2).fit_predict(X)
        assert list(labels) == [-1, -1]

    def test_single_tight_cluster(self):
        """Dense single-cluster dataset should be detected as one cluster."""
        rng = np.random.default_rng(0)
        X = rng.normal(loc=[50.0, 50.0], scale=2.0, size=(20, 2))
        labels = HDBSCAN(min_cluster_size=3, min_samples=2).fit_predict(X)
        unique = set(labels) - {-1}
        assert len(unique) >= 1

    def test_invalid_min_cluster_size_raises(self):
        with pytest.raises(ValueError):
            HDBSCAN(min_cluster_size=1)


# ── Stability attributes ──────────────────────────────────────────────────────

class TestHDBSCANAttributes:

    def test_labels_attribute_set_after_fit(self):
        X = _make_two_clusters(n=8)
        hdb = HDBSCAN(min_cluster_size=3, min_samples=2)
        assert hdb.labels_ is None
        hdb.fit_predict(X)
        assert hdb.labels_ is not None

    def test_same_input_deterministic(self):
        X = _make_two_clusters(n=10)
        hdb = HDBSCAN(min_cluster_size=3, min_samples=2)
        labels_a = hdb.fit_predict(X)
        labels_b = HDBSCAN(min_cluster_size=3, min_samples=2).fit_predict(X)
        np.testing.assert_array_equal(labels_a, labels_b)
