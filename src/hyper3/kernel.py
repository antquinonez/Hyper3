from __future__ import annotations

from hyper3.kernel_base import CoreMixin
from hyper3.kernel_centrality import CentralityMixin
from hyper3.kernel_clustering import ClusteringMixin
from hyper3.kernel_components import ComponentMixin
from hyper3.kernel_cycles import CycleMixin
from hyper3.kernel_dynamics import DynamicsMixin
from hyper3.kernel_paths import PathMixin
from hyper3.kernel_pattern import PatternMixin
from hyper3.kernel_query import QueryMixin
from hyper3.kernel_similarity import SimilarityMixin
from hyper3.kernel_spectral import SpectralMixin
from hyper3.kernel_transforms import TransformMixin
from hyper3.kernel_types import AbstractionLayer as AbstractionLayer
from hyper3.kernel_types import Hyperedge as Hyperedge
from hyper3.kernel_types import Hypernode as Hypernode
from hyper3.kernel_types import Metadata as Metadata
from hyper3.kernel_types import Modality as Modality


class Hypergraph(
    CoreMixin,
    QueryMixin,
    PathMixin,
    ComponentMixin,
    CycleMixin,
    CentralityMixin,
    SpectralMixin,
    ClusteringMixin,
    PatternMixin,
    TransformMixin,
    SimilarityMixin,
    DynamicsMixin,
):
    """Directed hypergraph with n-ary edges, label/dimension indexes, lazy neighbor caching, batch mutation support, and native algorithms for paths, centrality, PageRank, spectral embedding, and s-persistence."""
