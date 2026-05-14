"""
Dataset for the graph analytics demo.

Defines a professional network of technologists connected by reporting,
collaboration, and mentorship relationships. The structure includes:
  - A clear hierarchy (CTO -> VPs -> directors -> leads -> engineers)
  - Cross-functional collaboration edges (PM, design, data science)
  - Mentorship edges spanning levels

This creates a realistic network with identifiable hubs (middle management),
bridges (PMs connecting engineering and product), and peripheral nodes.
"""

PEOPLE = {
    "alice":   {"role": "cto",           "department": "engineering"},
    "bob":     {"role": "vp_eng",        "department": "engineering"},
    "carol":   {"role": "director",      "department": "engineering"},
    "dave":    {"role": "team_lead",     "department": "platform"},
    "eve":     {"role": "team_lead",     "department": "ml"},
    "frank":   {"role": "senior_eng",    "department": "platform"},
    "grace":   {"role": "senior_eng",    "department": "ml"},
    "heidi":   {"role": "engineer",      "department": "platform"},
    "ivan":    {"role": "engineer",      "department": "ml"},
    "judy":    {"role": "pm",            "department": "product"},
    "karl":    {"role": "designer",      "department": "design"},
    "mallory": {"role": "data_scientist","department": "data"},
    "nancy":   {"role": "devops",        "department": "infrastructure"},
    "oscar":   {"role": "qa_eng",        "department": "quality"},
}

REPORTING_EDGES = [
    ("alice", "bob", "manages"),
    ("bob", "carol", "manages"),
    ("carol", "dave", "manages"),
    ("carol", "eve", "manages"),
    ("dave", "frank", "manages"),
    ("dave", "heidi", "manages"),
    ("eve", "grace", "manages"),
    ("eve", "ivan", "manages"),
    ("alice", "judy", "manages"),
    ("alice", "karl", "manages"),
    ("bob", "nancy", "manages"),
    ("carol", "oscar", "manages"),
]

COLLABORATION_EDGES = [
    ("frank", "heidi", "collaborates"),
    ("grace", "ivan", "collaborates"),
    ("dave", "eve", "collaborates"),
    ("judy", "dave", "works_with"),
    ("judy", "eve", "works_with"),
    ("karl", "judy", "works_with"),
    ("mallory", "grace", "consults"),
    ("mallory", "ivan", "consults"),
    ("nancy", "dave", "supports"),
    ("nancy", "eve", "supports"),
    ("oscar", "frank", "tests_for"),
    ("oscar", "grace", "tests_for"),
    ("mallory", "mallory", "self_review"),
]

MENTORSHIP_EDGES = [
    ("alice", "carol", "mentors"),
    ("bob", "dave", "mentors"),
    ("bob", "eve", "mentors"),
    ("frank", "heidi", "mentors"),
    ("grace", "ivan", "mentors"),
    ("mallory", "oscar", "mentors"),
]

ALL_EDGES = REPORTING_EDGES + COLLABORATION_EDGES + MENTORSHIP_EDGES
