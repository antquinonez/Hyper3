from typing import Literal

CentralityMethod = Literal[
    "degree",
    "in_degree",
    "out_degree",
    "betweenness",
    "pagerank",
    "katz",
    "h_eigenvector",
    "z_eigenvector",
    "c_eigenvector",
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
