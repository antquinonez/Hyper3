"""
Dataset for the Bayesian reasoning demo.

Defines the medical conditions, symptoms, evidence likelihoods, and the
knowledge graph structure used by run.py. Separating data from logic keeps
the main walkthrough script focused on Hyper3 API calls.

Schema (stored in SQLite via storage.py):
    conditions  — name, severity, description
    symptoms    — name, associated_conditions
    evidence    — name, description, likelihoods per condition
"""

CONDITIONS = {
    "mi": {
        "severity": "critical",
        "description": "Myocardial infarction (heart attack)",
        "prevalence": 0.30,
    },
    "pe": {
        "severity": "critical",
        "description": "Pulmonary embolism",
        "prevalence": 0.10,
    },
    "aortic_dissection": {
        "severity": "critical",
        "description": "Tear in the aortic wall",
        "prevalence": 0.02,
    },
    "gerd": {
        "severity": "mild",
        "description": "Gastroesophageal reflux disease",
        "prevalence": 0.35,
    },
    "costochondritis": {
        "severity": "benign",
        "description": "Inflammation of chest wall cartilage",
        "prevalence": 0.23,
    },
}

SYMPTOMS = {
    "chest_pain": {
        "description": "Retrosternal pressure or tightness",
        "conditions": ["mi", "pe", "gerd", "costochondritis"],
    },
    "shortness_of_breath": {
        "description": "Dyspnea at rest or with exertion",
        "conditions": ["mi", "pe"],
    },
    "radiating_pain": {
        "description": "Pain radiating to left arm or jaw",
        "conditions": ["mi", "costochondritis"],
    },
    "heartburn": {
        "description": "Burning sensation after meals",
        "conditions": ["gerd"],
    },
    "tenderness": {
        "description": "Reproducible chest wall tenderness",
        "conditions": ["costochondritis"],
    },
}

# Each evidence item maps condition names to likelihood P(evidence | condition).
EVIDENCE_SEQUENCE = [
    {
        "name": "st_elevation",
        "description": "ECG shows ST-segment elevation",
        "likelihoods": {
            "mi": 0.85,
            "pe": 0.05,
            "aortic_dissection": 0.10,
            "gerd": 0.01,
            "costochondritis": 0.01,
        },
    },
    {
        "name": "troponin_elevated",
        "description": "Cardiac troponin levels above threshold",
        "likelihoods": {
            "mi": 0.95,
            "pe": 0.30,
            "aortic_dissection": 0.40,
            "gerd": 0.01,
            "costochondritis": 0.01,
        },
    },
    {
        "name": "d_dimer_elevated",
        "description": "D-dimer above 500 ng/mL (sensitive for PE, non-specific)",
        "likelihoods": {
            "mi": 0.50,
            "pe": 0.90,
            "aortic_dissection": 0.60,
            "gerd": 0.10,
            "costochondritis": 0.05,
        },
    },
]

# Knowledge graph edges: (source, target, label)
CONDITION_EDGES = [
    ("chest_pain", "mi", "presents_with"),
    ("shortness_of_breath", "mi", "presents_with"),
    ("radiating_pain", "mi", "presents_with"),
    ("shortness_of_breath", "pe", "presents_with"),
    ("chest_pain", "pe", "presents_with"),
    ("chest_pain", "gerd", "presents_with"),
    ("heartburn", "gerd", "presents_with"),
    ("chest_pain", "costochondritis", "presents_with"),
    ("tenderness", "costochondritis", "presents_with"),
    ("radiating_pain", "costochondritis", "presents_with"),
    ("mi", "pe", "differential_of"),
    ("mi", "gerd", "differential_of"),
    ("mi", "costochondritis", "differential_of"),
    ("mi", "aortic_dissection", "differential_of"),
]
