from typing import Literal

CentralityMethod = Literal[
    "degree",
    "in_degree",
    "out_degree",
    "betweenness",
    "closeness",
    "pagerank",
    "katz",
    "eigenvector",
    "h_eigenvector",
    "z_eigenvector",
    "c_eigenvector",
    "node_edge",
    "s_walk_betweenness",
    "s_walk_closeness",
    "subgraph",
    "core_periphery",
]

CommunityMethod = Literal[
    "label_propagation",
    "weighted_label_propagation",
    "connected_components",
    "louvain",
    "girvan_newman",
]

TemporalRelation = Literal[
    "before",
    "after",
    "overlapping",
    "containing",
    "proximity",
]
