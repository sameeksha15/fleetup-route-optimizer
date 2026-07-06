"""Hybrid density/centroid clustering of packages.

DBSCAN groups packages by geographic density; points it flags as noise are
swept into K-Means clusters so every package ends up in exactly one group.
"""

from __future__ import annotations

import numpy as np
from sklearn.cluster import DBSCAN, KMeans

from .entities import Package

# ~1.1 km at Mumbai's latitude, expressed in degrees for DBSCAN's metric.
DEFAULT_EPS_DEG = 0.01
DEFAULT_MIN_SAMPLES = 2
MAX_FALLBACK_CLUSTERS = 3


def assign_clusters(
    packages: list[Package],
    eps: float = DEFAULT_EPS_DEG,
    min_samples: int = DEFAULT_MIN_SAMPLES,
    random_state: int = 42,
) -> None:
    """Set ``cluster`` on each package in place."""
    if not packages:
        return
    coords = np.array([[p.latitude, p.longitude] for p in packages])
    labels = DBSCAN(eps=eps, min_samples=min_samples).fit(coords).labels_

    noise_idx = np.flatnonzero(labels == -1)
    if noise_idx.size:
        n_clusters = min(noise_idx.size, MAX_FALLBACK_CLUSTERS)
        offset = labels.max() + 1
        if n_clusters > 1:
            kmeans_labels = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10).fit_predict(
                coords[noise_idx]
            )
            labels[noise_idx] = kmeans_labels + offset
        else:
            labels[noise_idx] = offset

    for package, label in zip(packages, labels):
        package.cluster = int(label)
