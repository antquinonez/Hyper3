ENZYMES = {
    "kinase_a": {"type": "enzyme", "class": "kinase"},
    "kinase_b": {"type": "enzyme", "class": "kinase"},
    "phosphatase_c": {"type": "enzyme", "class": "phosphatase"},
    "protease_d": {"type": "enzyme", "class": "protease"},
    "synthetase_e": {"type": "enzyme", "class": "synthetase"},
}

SUBSTRATES = {
    "substrate_x": {"type": "substrate", "mw": 450},
    "substrate_y": {"type": "substrate", "mw": 320},
    "substrate_z": {"type": "substrate", "mw": 580},
    "atp": {"type": "cofactor", "role": "energy"},
    "adp": {"type": "cofactor", "role": "spent"},
}

PRODUCTS = {
    "product_m": {"type": "product", "toxicity": "low"},
    "product_n": {"type": "product", "toxicity": "medium"},
    "product_o": {"type": "product", "toxicity": "high"},
}

REACTIONS = [
    ("kinase_a", "substrate_x", "phosphorylates"),
    ("substrate_x", "kinase_b", "activates"),
    ("kinase_b", "substrate_y", "phosphorylates"),
    ("substrate_y", "synthetase_e", "activates"),
    ("synthetase_e", "product_m", "synthesizes"),
    ("phosphatase_c", "substrate_x", "deactivates"),
    ("protease_d", "kinase_a", "degrades"),
    ("atp", "kinase_a", "powers"),
    ("atp", "kinase_b", "powers"),
    ("kinase_a", "product_n", "produces"),
    ("product_m", "product_o", "converts_to"),
    ("substrate_z", "product_n", "inhibits"),
]
