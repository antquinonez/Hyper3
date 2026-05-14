ACTORS = {
    "company_a": {"type": "corporation", "sector": "manufacturing"},
    "company_b": {"type": "corporation", "sector": "logistics"},
    "company_c": {"type": "corporation", "sector": "retail"},
    "region_x": {"type": "region", "stability": "volatile"},
    "port_z": {"type": "infrastructure", "capacity": "large"},
    "commodity_y": {"type": "commodity", "criticality": "high"},
}

EDGES = [
    ("company_a", "company_b", "supplies", 3.0),
    ("company_b", "company_c", "distributes_to", 2.0),
    ("company_a", "region_x", "operates_in", 1.0),
    ("region_x", "port_z", "contains", 1.0),
    ("port_z", "company_b", "handles_shipping_for", 1.5),
    ("company_a", "commodity_y", "produces", 2.0),
]
