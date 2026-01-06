from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
from sklearn.cluster import KMeans


@dataclass(frozen=True)
class ClusterResult:
    k: int
    labels: List[int]  # len = n, values in [0..k-1]


def kmeans_cluster(X: np.ndarray, k: int, seed: int = 42) -> ClusterResult:
    """
    KMeans clustering on embedding matrix X (n,d).
    """
    if X.ndim != 2 or X.shape[0] == 0:
        return ClusterResult(k=0, labels=[])

    if k <= 0:
        raise ValueError("k must be > 0")
    if k > X.shape[0]:
        k = X.shape[0]

    km = KMeans(n_clusters=k, random_state=seed, n_init="auto")
    labels = km.fit_predict(X)
    return ClusterResult(k=k, labels=[int(x) for x in labels])
