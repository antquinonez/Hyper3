"""Dataset for the hyperedge walkthrough: research lab with n-ary collaborations.

People, resources, deliverables, hyperedges (joint authorship, shared datasets),
and pairwise mentorship edges.
"""

PEOPLE = {
    "alice": {"role": "pi", "expertise": "nlp"},
    "bob": {"role": "postdoc", "expertise": "cv"},
    "carol": {"role": "phd", "expertise": "rl"},
    "dave": {"role": "phd", "expertise": "nlp"},
    "eve": {"role": "phd", "expertise": "cv"},
    "frank": {"role": "ms", "expertise": "data"},
}

RESOURCES = {
    "gpu_cluster": {"type": "compute", "units": 8},
    "lab_budget": {"type": "funding", "amount": 500000},
    "dataset_x": {"type": "data", "size": "10TB"},
}

DELIVERABLES = {
    "paper_transformers": {"type": "publication", "venue": "neurips"},
    "paper_diffusion": {"type": "publication", "venue": "icml"},
    "paper_rl_agent": {"type": "publication", "venue": "icra"},
    "grant_nsf": {"type": "grant", "agency": "nsf"},
}

MENTORSHIP_EDGES = [
    ("alice", "bob", "mentors"),
    ("alice", "carol", "mentors"),
    ("alice", "dave", "mentors"),
    ("bob", "eve", "mentors"),
    ("carol", "frank", "mentors"),
]

# N-ary hyperedges: (sources_set, targets_set, label, weight)
HYPEREDGES = [
    ({"alice", "dave"}, {"paper_transformers"}, "coauthored", 3.0),
    ({"bob", "eve", "alice"}, {"paper_diffusion"}, "coauthored", 2.5),
    ({"carol", "frank"}, {"paper_rl_agent"}, "coauthored", 2.0),
    ({"grant_nsf"}, {"paper_transformers", "paper_rl_agent"}, "funds", 4.0),
    ({"alice", "bob", "carol"}, {"dataset_x"}, "approved_access_to", 2.0),
    ({"alice", "bob", "carol", "dave", "eve", "frank"}, {"gpu_cluster"}, "shares", 1.0),
]
