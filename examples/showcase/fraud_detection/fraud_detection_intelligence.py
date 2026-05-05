"""
Fraud Network Intelligence
===========================

Models a realistic fraud investigation scenario: a ring leader orchestrates
money laundering through shell companies, money mules, and layered transactions.
The investigation starts from a flagged alert, uses activation and retrieval to
surface related entities, applies reasoning rules to discover hidden connections,
detects circular money flows and funnel accounts, and ranks suspects by risk.

Run with:
    .venv/bin/python examples/showcase/fraud_detection/fraud_detection_intelligence.py
"""

from __future__ import annotations

from hyper3 import (
    HypergraphMemory,
    Modality,
    TransitiveRule,
    InverseRule,
)


def main():
    mem = HypergraphMemory(evolve_interval=0)

    print("=" * 70)
    print("SECTION 1: Fraud Network Construction")
    print("=" * 70)

    persons = {
        "viktor_kingpin": {"role": "ring_leader", "risk_score": 0.95, "country": "RU", "account_age_days": 1825},
        "lena_lieutenant": {"role": "lieutenant", "risk_score": 0.88, "country": "RU", "account_age_days": 1460},
        "boris_mule1": {"role": "money_mule", "risk_score": 0.75, "country": "UA", "account_age_days": 120},
        "olga_mule2": {"role": "money_mule", "risk_score": 0.72, "country": "UA", "account_age_days": 95},
        "sergei_mule3": {"role": "money_mule", "risk_score": 0.70, "country": "MD", "account_age_days": 200},
        "natasha_mule4": {"role": "money_mule", "risk_score": 0.68, "country": "RO", "account_age_days": 180},
        "dmitri_mule5": {"role": "money_mule", "risk_score": 0.65, "country": "BG", "account_age_days": 150},
        "alexei_runner1": {"role": "cash_runner", "risk_score": 0.60, "country": "RU", "account_age_days": 730},
        "yuri_runner2": {"role": "cash_runner", "risk_score": 0.58, "country": "UA", "account_age_days": 365},
        "marina_runner3": {"role": "cash_runner", "risk_score": 0.55, "country": "GE", "account_age_days": 250},
        "katya_recruiter": {"role": "recruiter", "risk_score": 0.82, "country": "RU", "account_age_days": 1095},
        "pavel_tech": {"role": "tech_support", "risk_score": 0.85, "country": "RU", "account_age_days": 2000},
        "irina_accountant": {"role": "accountant", "risk_score": 0.78, "country": "CY", "account_age_days": 900},
        "victim_martinez": {"role": "victim", "risk_score": 0.10, "country": "US", "account_age_days": 3650},
        "victim_chen": {"role": "victim", "risk_score": 0.08, "country": "CN", "account_age_days": 2555},
        "victim_okafor": {"role": "victim", "risk_score": 0.12, "country": "NG", "account_age_days": 1800},
        "victim_patel": {"role": "victim", "risk_score": 0.09, "country": "IN", "account_age_days": 3000},
        "victim_kowalski": {"role": "victim", "risk_score": 0.11, "country": "PL", "account_age_days": 2200},
        "biz_target_nexus": {"role": "victim", "risk_score": 0.05, "country": "US", "account_age_days": 5000},
        "biz_target_apex": {"role": "victim", "risk_score": 0.06, "country": "GB", "account_age_days": 4000},
        "teller_johnson": {"role": "bank_teller", "risk_score": 0.02, "country": "US", "account_age_days": 1500},
        "manager_williams": {"role": "branch_manager", "risk_score": 0.01, "country": "US", "account_age_days": 3000},
        "compliance_davis": {"role": "compliance_officer", "risk_score": 0.01, "country": "US", "account_age_days": 2500},
        "investigator_brown": {"role": "investigator", "risk_score": 0.01, "country": "US", "account_age_days": 1000},
        "auditor_white": {"role": "auditor", "risk_score": 0.01, "country": "US", "account_age_days": 800},
        "agent_clark": {"role": "law_enforcement", "risk_score": 0.01, "country": "US", "account_age_days": 500},
        "witness_halcomb": {"role": "witness", "risk_score": 0.03, "country": "US", "account_age_days": 400},
        "informant_reyes": {"role": "informant", "risk_score": 0.15, "country": "CO", "account_age_days": 300},
    }

    accounts = {
        "acct_viktor_personal": {"type": "checking", "balance": 15000, "opened_date": "2019-06-15", "flagged": True},
        "acct_viktor_business": {"type": "business", "balance": 250000, "opened_date": "2020-01-10", "flagged": True},
        "acct_lena_personal": {"type": "savings", "balance": 45000, "opened_date": "2020-03-22", "flagged": True},
        "acct_boris_checking": {"type": "checking", "balance": 8500, "opened_date": "2025-10-01", "flagged": True},
        "acct_olga_savings": {"type": "savings", "balance": 12000, "opened_date": "2025-10-15", "flagged": True},
        "acct_sergei_checking": {"type": "checking", "balance": 6000, "opened_date": "2025-07-01", "flagged": False},
        "acct_natasha_checking": {"type": "checking", "balance": 9500, "opened_date": "2025-08-15", "flagged": False},
        "acct_dmitri_invest": {"type": "investment", "balance": 28000, "opened_date": "2025-09-01", "flagged": True},
        "acct_global_trading": {"type": "business", "balance": 500000, "opened_date": "2021-05-01", "flagged": True},
        "acct_pacific_ventures": {"type": "business", "balance": 380000, "opened_date": "2021-08-15", "flagged": True},
        "acct_zenith_holdings": {"type": "business", "balance": 750000, "opened_date": "2022-02-01", "flagged": True},
        "acct_alpha_consulting": {"type": "business", "balance": 120000, "opened_date": "2022-06-15", "flagged": True},
        "acct_nordic_services": {"type": "business", "balance": 200000, "opened_date": "2023-01-10", "flagged": False},
        "acct_meridian_invest": {"type": "business", "balance": 150000, "opened_date": "2023-04-20", "flagged": False},
        "acct_victim_martinez": {"type": "checking", "balance": 3500, "opened_date": "2017-03-15", "flagged": False},
        "acct_victim_chen": {"type": "savings", "balance": 50000, "opened_date": "2019-01-20", "flagged": False},
        "acct_victim_okafor": {"type": "checking", "balance": 7200, "opened_date": "2020-07-10", "flagged": False},
        "acct_victim_patel": {"type": "checking", "balance": 4500, "opened_date": "2018-11-05", "flagged": False},
        "acct_victim_kowalski": {"type": "savings", "balance": 22000, "opened_date": "2019-08-30", "flagged": False},
        "acct_nexus_corporate": {"type": "corporate", "balance": 1500000, "opened_date": "2015-01-01", "flagged": False},
        "acct_apex_ltd": {"type": "corporate", "balance": 800000, "opened_date": "2016-06-15", "flagged": False},
        "acct_katya_personal": {"type": "checking", "balance": 18000, "opened_date": "2022-01-10", "flagged": True},
    }

    transactions = {
        "tx_001": {"amount": 9800, "currency": "USD", "timestamp": "2025-11-01T09:15:00", "channel": "wire"},
        "tx_002": {"amount": 9900, "currency": "USD", "timestamp": "2025-11-01T14:30:00", "channel": "wire"},
        "tx_003": {"amount": 9700, "currency": "USD", "timestamp": "2025-11-02T10:00:00", "channel": "wire"},
        "tx_004": {"amount": 9500, "currency": "USD", "timestamp": "2025-11-02T16:45:00", "channel": "ach"},
        "tx_005": {"amount": 250000, "currency": "USD", "timestamp": "2025-11-03T08:00:00", "channel": "wire"},
        "tx_006": {"amount": 180000, "currency": "EUR", "timestamp": "2025-11-03T11:30:00", "channel": "swift"},
        "tx_007": {"amount": 45000, "currency": "USD", "timestamp": "2025-11-04T09:00:00", "channel": "ach"},
        "tx_008": {"amount": 32000, "currency": "USD", "timestamp": "2025-11-04T13:15:00", "channel": "wire"},
        "tx_009": {"amount": 8900, "currency": "USD", "timestamp": "2025-11-05T10:30:00", "channel": "atm"},
        "tx_010": {"amount": 7500, "currency": "USD", "timestamp": "2025-11-05T15:00:00", "channel": "ach"},
        "tx_011": {"amount": 125000, "currency": "USD", "timestamp": "2025-11-06T08:45:00", "channel": "wire"},
        "tx_012": {"amount": 150000, "currency": "USD", "timestamp": "2025-11-06T14:00:00", "channel": "swift"},
        "tx_013": {"amount": 50000, "currency": "GBP", "timestamp": "2025-11-07T09:30:00", "channel": "swift"},
        "tx_014": {"amount": 9200, "currency": "USD", "timestamp": "2025-11-07T11:00:00", "channel": "wire"},
        "tx_015": {"amount": 38000, "currency": "USD", "timestamp": "2025-11-08T10:00:00", "channel": "ach"},
        "tx_016": {"amount": 47500, "currency": "USD", "timestamp": "2025-11-08T14:30:00", "channel": "wire"},
        "tx_017": {"amount": 200000, "currency": "CHF", "timestamp": "2025-11-09T09:00:00", "channel": "swift"},
        "tx_018": {"amount": 15000, "currency": "USD", "timestamp": "2025-11-09T16:00:00", "channel": "ach"},
    }

    entities = {
        "ent_global_trading_ltd": {"type": "company", "verified": False},
        "ent_pacific_ventures_inc": {"type": "company", "verified": False},
        "ent_zenith_holdings_llc": {"type": "company", "verified": False},
        "ent_alpha_consulting_gmbh": {"type": "company", "verified": False},
        "ent_nordic_services_ab": {"type": "company", "verified": False},
        "ent_meridian_investments_sa": {"type": "company", "verified": False},
        "addr_downtown_4b": {"type": "address", "verified": False},
        "addr_harbour_12": {"type": "address", "verified": False},
        "addr_midtown_po45": {"type": "address", "verified": True},
        "addr_riverside_22": {"type": "address", "verified": False},
        "addr_oakwood_101": {"type": "address", "verified": False},
        "phone_5550101": {"type": "phone", "verified": False},
        "phone_5550102": {"type": "phone", "verified": False},
        "phone_5550103": {"type": "phone", "verified": False},
        "phone_5550201": {"type": "phone", "verified": True},
        "phone_5550202": {"type": "phone", "verified": False},
    }

    patterns = {
        "pat_structuring": {"scheme_type": "structuring", "severity": "high", "detection_method": "threshold_analysis"},
        "pat_circular_flow": {"scheme_type": "circular_flow", "severity": "critical", "detection_method": "cycle_detection"},
        "pat_funnel_account": {"scheme_type": "funnel_account", "severity": "high", "detection_method": "degree_analysis"},
        "pat_smurfing": {"scheme_type": "smurfing", "severity": "medium", "detection_method": "pattern_matching"},
        "pat_identity_theft": {"scheme_type": "identity_theft", "severity": "high", "detection_method": "anomaly_detection"},
        "pat_shell_layering": {"scheme_type": "layering", "severity": "critical", "detection_method": "network_analysis"},
        "pat_rapid_movement": {"scheme_type": "rapid_movement", "severity": "high", "detection_method": "velocity_check"},
        "pat_mule_network": {"scheme_type": "mule_network", "severity": "high", "detection_method": "clustering"},
        "pat_bec_scheme": {"scheme_type": "bec", "severity": "critical", "detection_method": "email_analysis"},
        "pat_kyc_evasion": {"scheme_type": "kyc_evasion", "severity": "medium", "detection_method": "document_analysis"},
        "pat_round_trip": {"scheme_type": "round_trip", "severity": "high", "detection_method": "cycle_detection"},
        "pat_fatf_red_flag": {"scheme_type": "fatf_indicator", "severity": "high", "detection_method": "compliance_check"},
    }

    ip_devices = {
        "ip_vpn_moscow": {"type": "vpn", "location": "Moscow_RU", "first_seen": "2025-09-01"},
        "ip_vpn_kiev": {"type": "vpn", "location": "Kiev_UA", "first_seen": "2025-09-15"},
        "ip_tor_exit1": {"type": "tor", "location": "Unknown", "first_seen": "2025-10-01"},
        "ip_tor_exit2": {"type": "tor", "location": "Unknown", "first_seen": "2025-10-05"},
        "device_laptop_pavel": {"type": "laptop", "location": "Moscow_RU", "first_seen": "2025-08-01"},
        "device_phone_boris": {"type": "phone", "location": "Odessa_UA", "first_seen": "2025-09-20"},
        "device_phone_olga": {"type": "phone", "location": "Lviv_UA", "first_seen": "2025-09-25"},
        "device_tablet_alexei": {"type": "tablet", "location": "Tbilisi_GE", "first_seen": "2025-10-01"},
        "ip_cafe_downtown": {"type": "public_wifi", "location": "New_York_US", "first_seen": "2025-10-10"},
        "ip_cafe_midtown": {"type": "public_wifi", "location": "New_York_US", "first_seen": "2025-10-12"},
        "ip_home_viktor": {"type": "residential", "location": "Moscow_RU", "first_seen": "2025-01-01"},
        "device_desktop_viktor": {"type": "desktop", "location": "Moscow_RU", "first_seen": "2025-01-01"},
    }

    alerts = {
        "alert_structuring_001": {"type": "structuring", "severity": "high", "status": "active"},
        "alert_circular_001": {"type": "circular_flow", "severity": "critical", "status": "active"},
        "alert_funnel_001": {"type": "funnel_account", "severity": "high", "status": "active"},
        "alert_identity_001": {"type": "identity_theft", "severity": "high", "status": "investigating"},
        "alert_shell_001": {"type": "shell_company", "severity": "critical", "status": "active"},
        "alert_rapid_001": {"type": "rapid_movement", "severity": "medium", "status": "active"},
        "alert_mule_001": {"type": "mule_activity", "severity": "high", "status": "investigating"},
        "alert_bec_001": {"type": "bec", "severity": "critical", "status": "escalated"},
        "alert_kyc_001": {"type": "kyc_violation", "severity": "medium", "status": "active"},
        "alert_vpn_001": {"type": "suspicious_access", "severity": "medium", "status": "active"},
        "alert_device_001": {"type": "device_sharing", "severity": "high", "status": "investigating"},
    }

    all_nodes = {}
    all_nodes.update(persons)
    all_nodes.update(accounts)
    all_nodes.update(transactions)
    all_nodes.update(entities)
    all_nodes.update(patterns)
    all_nodes.update(ip_devices)
    all_nodes.update(alerts)

    for label, data in all_nodes.items():
        mem.store(label, data=data)

    owns_edges = [
        ("viktor_kingpin", "acct_viktor_personal"),
        ("viktor_kingpin", "acct_viktor_business"),
        ("lena_lieutenant", "acct_lena_personal"),
        ("boris_mule1", "acct_boris_checking"),
        ("olga_mule2", "acct_olga_savings"),
        ("sergei_mule3", "acct_sergei_checking"),
        ("natasha_mule4", "acct_natasha_checking"),
        ("dmitri_mule5", "acct_dmitri_invest"),
        ("katya_recruiter", "acct_katya_personal"),
        ("victim_martinez", "acct_victim_martinez"),
        ("victim_chen", "acct_victim_chen"),
        ("victim_okafor", "acct_victim_okafor"),
        ("victim_patel", "acct_victim_patel"),
        ("victim_kowalski", "acct_victim_kowalski"),
        ("biz_target_nexus", "acct_nexus_corporate"),
        ("biz_target_apex", "acct_apex_ltd"),
        ("viktor_kingpin", "acct_global_trading"),
        ("viktor_kingpin", "acct_pacific_ventures"),
        ("viktor_kingpin", "acct_zenith_holdings"),
        ("lena_lieutenant", "acct_nordic_services"),
        ("lena_lieutenant", "acct_meridian_invest"),
        ("katya_recruiter", "acct_alpha_consulting"),
        ("irina_accountant", "acct_global_trading"),
        ("irina_accountant", "acct_pacific_ventures"),
        ("irina_accountant", "acct_zenith_holdings"),
        ("irina_accountant", "acct_alpha_consulting"),
        ("pavel_tech", "acct_nordic_services"),
        ("marina_runner3", "acct_meridian_invest"),
    ]

    transferred_to_edges = [
        ("acct_victim_martinez", "acct_viktor_personal"),
        ("acct_victim_chen", "acct_viktor_business"),
        ("acct_victim_okafor", "acct_lena_personal"),
        ("acct_victim_patel", "acct_boris_checking"),
        ("acct_victim_kowalski", "acct_olga_savings"),
        ("acct_nexus_corporate", "acct_global_trading"),
        ("acct_apex_ltd", "acct_pacific_ventures"),
        ("acct_viktor_personal", "acct_lena_personal"),
        ("acct_viktor_business", "acct_global_trading"),
        ("acct_lena_personal", "acct_boris_checking"),
        ("acct_lena_personal", "acct_olga_savings"),
        ("acct_boris_checking", "acct_natasha_checking"),
        ("acct_olga_savings", "acct_dmitri_invest"),
        ("acct_sergei_checking", "acct_natasha_checking"),
        ("acct_natasha_checking", "acct_zenith_holdings"),
        ("acct_dmitri_invest", "acct_zenith_holdings"),
        ("acct_global_trading", "acct_pacific_ventures"),
        ("acct_pacific_ventures", "acct_zenith_holdings"),
        ("acct_zenith_holdings", "acct_alpha_consulting"),
        ("acct_alpha_consulting", "acct_nordic_services"),
        ("acct_nordic_services", "acct_meridian_invest"),
        ("acct_meridian_invest", "acct_viktor_business"),
        ("acct_katya_personal", "acct_boris_checking"),
        ("acct_katya_personal", "acct_olga_savings"),
        ("acct_viktor_personal", "acct_boris_checking"),
        ("acct_viktor_personal", "acct_olga_savings"),
        ("acct_viktor_business", "acct_pacific_ventures"),
        ("acct_global_trading", "acct_zenith_holdings"),
        ("acct_pacific_ventures", "acct_alpha_consulting"),
        ("acct_alpha_consulting", "acct_viktor_personal"),
        ("acct_sergei_checking", "acct_dmitri_invest"),
        ("acct_natasha_checking", "acct_dmitri_invest"),
        ("acct_nordic_services", "acct_viktor_personal"),
        ("acct_zenith_holdings", "acct_viktor_business"),
        ("acct_meridian_invest", "acct_lena_personal"),
    ]

    shares_address_edges = [
        ("viktor_kingpin", "addr_downtown_4b"),
        ("lena_lieutenant", "addr_downtown_4b"),
        ("irina_accountant", "addr_downtown_4b"),
        ("boris_mule1", "addr_harbour_12"),
        ("olga_mule2", "addr_harbour_12"),
        ("sergei_mule3", "addr_harbour_12"),
        ("natasha_mule4", "addr_riverside_22"),
        ("dmitri_mule5", "addr_riverside_22"),
        ("katya_recruiter", "addr_oakwood_101"),
        ("alexei_runner1", "addr_oakwood_101"),
        ("yuri_runner2", "addr_midtown_po45"),
        ("marina_runner3", "addr_midtown_po45"),
        ("pavel_tech", "addr_downtown_4b"),
        ("informant_reyes", "addr_riverside_22"),
        ("viktor_kingpin", "addr_oakwood_101"),
        ("lena_lieutenant", "addr_harbour_12"),
        ("katya_recruiter", "addr_harbour_12"),
        ("irina_accountant", "addr_oakwood_101"),
        ("boris_mule1", "addr_oakwood_101"),
        ("olga_mule2", "addr_oakwood_101"),
    ]

    shares_phone_edges = [
        ("viktor_kingpin", "phone_5550101"),
        ("lena_lieutenant", "phone_5550101"),
        ("boris_mule1", "phone_5550102"),
        ("olga_mule2", "phone_5550102"),
        ("sergei_mule3", "phone_5550103"),
        ("natasha_mule4", "phone_5550103"),
        ("dmitri_mule5", "phone_5550202"),
        ("katya_recruiter", "phone_5550202"),
        ("alexei_runner1", "phone_5550101"),
        ("pavel_tech", "phone_5550101"),
        ("irina_accountant", "phone_5550201"),
        ("marina_runner3", "phone_5550103"),
    ]

    accessed_from_edges = [
        ("acct_viktor_personal", "ip_home_viktor"),
        ("acct_viktor_personal", "device_desktop_viktor"),
        ("acct_viktor_business", "ip_vpn_moscow"),
        ("acct_viktor_business", "device_laptop_pavel"),
        ("acct_lena_personal", "ip_vpn_moscow"),
        ("acct_boris_checking", "ip_vpn_kiev"),
        ("acct_boris_checking", "device_phone_boris"),
        ("acct_olga_savings", "ip_vpn_kiev"),
        ("acct_olga_savings", "device_phone_olga"),
        ("acct_sergei_checking", "ip_tor_exit1"),
        ("acct_natasha_checking", "ip_tor_exit2"),
        ("acct_dmitri_invest", "ip_tor_exit1"),
        ("acct_global_trading", "ip_vpn_moscow"),
        ("acct_pacific_ventures", "ip_vpn_moscow"),
        ("acct_zenith_holdings", "device_laptop_pavel"),
        ("acct_alpha_consulting", "device_laptop_pavel"),
        ("acct_nordic_services", "ip_vpn_moscow"),
        ("acct_meridian_invest", "ip_vpn_moscow"),
        ("acct_victim_martinez", "ip_cafe_downtown"),
        ("acct_victim_chen", "ip_cafe_midtown"),
        ("acct_katya_personal", "ip_vpn_moscow"),
        ("acct_nexus_corporate", "ip_cafe_downtown"),
    ]

    flagged_by_edges = [
        ("tx_001", "alert_structuring_001"),
        ("tx_002", "alert_structuring_001"),
        ("tx_003", "alert_structuring_001"),
        ("tx_004", "alert_structuring_001"),
        ("tx_009", "alert_structuring_001"),
        ("tx_014", "alert_structuring_001"),
        ("acct_zenith_holdings", "alert_circular_001"),
        ("acct_global_trading", "alert_circular_001"),
        ("acct_meridian_invest", "alert_circular_001"),
        ("acct_zenith_holdings", "alert_funnel_001"),
        ("acct_global_trading", "alert_funnel_001"),
        ("acct_alpha_consulting", "alert_funnel_001"),
        ("acct_pacific_ventures", "alert_shell_001"),
        ("acct_nordic_services", "alert_shell_001"),
        ("acct_meridian_invest", "alert_shell_001"),
        ("acct_boris_checking", "alert_mule_001"),
        ("acct_olga_savings", "alert_mule_001"),
        ("acct_natasha_checking", "alert_mule_001"),
        ("acct_dmitri_invest", "alert_mule_001"),
        ("acct_nexus_corporate", "alert_bec_001"),
        ("acct_apex_ltd", "alert_bec_001"),
        ("ip_vpn_moscow", "alert_vpn_001"),
        ("ip_tor_exit1", "alert_vpn_001"),
        ("ip_tor_exit2", "alert_vpn_001"),
        ("device_laptop_pavel", "alert_device_001"),
        ("device_desktop_viktor", "alert_device_001"),
        ("ip_home_viktor", "alert_kyc_001"),
        ("acct_viktor_business", "alert_kyc_001"),
    ]

    similar_to_edges = [
        ("tx_001", "tx_002"),
        ("tx_002", "tx_003"),
        ("tx_003", "tx_004"),
        ("tx_004", "tx_009"),
        ("tx_009", "tx_014"),
        ("tx_005", "tx_011"),
        ("tx_011", "tx_012"),
        ("tx_006", "tx_017"),
        ("tx_007", "tx_015"),
        ("tx_008", "tx_016"),
        ("acct_boris_checking", "acct_olga_savings"),
        ("acct_sergei_checking", "acct_natasha_checking"),
        ("acct_global_trading", "acct_pacific_ventures"),
        ("acct_zenith_holdings", "acct_alpha_consulting"),
        ("boris_mule1", "olga_mule2"),
        ("sergei_mule3", "natasha_mule4"),
        ("sergei_mule3", "dmitri_mule5"),
        ("ent_global_trading_ltd", "ent_pacific_ventures_inc"),
        ("ent_zenith_holdings_llc", "ent_alpha_consulting_gmbh"),
    ]

    associated_with_edges = [
        ("viktor_kingpin", "ent_global_trading_ltd"),
        ("viktor_kingpin", "ent_zenith_holdings_llc"),
        ("lena_lieutenant", "ent_pacific_ventures_inc"),
        ("lena_lieutenant", "ent_nordic_services_ab"),
        ("irina_accountant", "ent_global_trading_ltd"),
        ("irina_accountant", "ent_pacific_ventures_inc"),
        ("irina_accountant", "ent_zenith_holdings_llc"),
        ("irina_accountant", "ent_alpha_consulting_gmbh"),
        ("irina_accountant", "ent_meridian_investments_sa"),
        ("irina_accountant", "ent_nordic_services_ab"),
        ("pavel_tech", "ent_nordic_services_ab"),
        ("katya_recruiter", "boris_mule1"),
        ("katya_recruiter", "olga_mule2"),
        ("katya_recruiter", "sergei_mule3"),
        ("katya_recruiter", "natasha_mule4"),
        ("katya_recruiter", "dmitri_mule5"),
        ("viktor_kingpin", "lena_lieutenant"),
        ("viktor_kingpin", "katya_recruiter"),
        ("viktor_kingpin", "pavel_tech"),
        ("viktor_kingpin", "irina_accountant"),
        ("lena_lieutenant", "alexei_runner1"),
        ("lena_lieutenant", "yuri_runner2"),
        ("alexei_runner1", "boris_mule1"),
        ("alexei_runner1", "olga_mule2"),
        ("yuri_runner2", "sergei_mule3"),
        ("yuri_runner2", "natasha_mule4"),
        ("marina_runner3", "dmitri_mule5"),
        ("marina_runner3", "natasha_mule4"),
        ("informant_reyes", "katya_recruiter"),
        ("informant_reyes", "boris_mule1"),
        ("witness_halcomb", "victim_martinez"),
        ("witness_halcomb", "investigator_brown"),
        ("investigator_brown", "compliance_davis"),
        ("investigator_brown", "agent_clark"),
        ("compliance_davis", "manager_williams"),
        ("teller_johnson", "victim_martinez"),
        ("teller_johnson", "investigator_brown"),
    ]

    pattern_match_edges = [
        ("tx_001", "pat_structuring"),
        ("tx_002", "pat_structuring"),
        ("tx_003", "pat_structuring"),
        ("tx_004", "pat_structuring"),
        ("tx_009", "pat_smurfing"),
        ("tx_014", "pat_smurfing"),
        ("acct_zenith_holdings", "pat_funnel_account"),
        ("acct_global_trading", "pat_funnel_account"),
        ("acct_alpha_consulting", "pat_funnel_account"),
        ("acct_pacific_ventures", "pat_shell_layering"),
        ("acct_nordic_services", "pat_shell_layering"),
        ("acct_meridian_invest", "pat_shell_layering"),
        ("ent_global_trading_ltd", "pat_shell_layering"),
        ("ent_pacific_ventures_inc", "pat_shell_layering"),
        ("ent_zenith_holdings_llc", "pat_shell_layering"),
        ("boris_mule1", "pat_mule_network"),
        ("olga_mule2", "pat_mule_network"),
        ("sergei_mule3", "pat_mule_network"),
        ("natasha_mule4", "pat_mule_network"),
        ("dmitri_mule5", "pat_mule_network"),
        ("acct_nexus_corporate", "pat_bec_scheme"),
        ("acct_apex_ltd", "pat_bec_scheme"),
        ("tx_005", "pat_rapid_movement"),
        ("tx_006", "pat_rapid_movement"),
        ("tx_011", "pat_rapid_movement"),
        ("tx_012", "pat_rapid_movement"),
        ("ip_vpn_moscow", "pat_kyc_evasion"),
        ("ip_tor_exit1", "pat_kyc_evasion"),
        ("acct_viktor_business", "pat_kyc_evasion"),
        ("acct_global_trading", "pat_round_trip"),
        ("acct_zenith_holdings", "pat_round_trip"),
        ("acct_meridian_invest", "pat_round_trip"),
        ("acct_viktor_business", "pat_fatf_red_flag"),
        ("acct_zenith_holdings", "pat_fatf_red_flag"),
        ("acct_global_trading", "pat_fatf_red_flag"),
        ("ip_home_viktor", "pat_kyc_evasion"),
    ]

    edge_groups = {
        "owns": owns_edges,
        "transferred_to": transferred_to_edges,
        "shares_address": shares_address_edges,
        "shares_phone": shares_phone_edges,
        "accessed_from": accessed_from_edges,
        "flagged_by": flagged_by_edges,
        "similar_to": similar_to_edges,
        "associated_with": associated_with_edges,
        "pattern_match": pattern_match_edges,
    }

    total_edges = 0
    for label, pairs in edge_groups.items():
        for src, tgt in pairs:
            mem.relate(src, tgt, label=label)
        total_edges += len(pairs)

    print(f"  Nodes: {mem.graph.node_count}")
    print(f"  Edges: {mem.graph.edge_count}")
    print(f"  Edge breakdown:")
    for label, pairs in edge_groups.items():
        print(f"    {label}: {len(pairs)}")
    print(f"  Total edge tuples: {total_edges}")
    print()

    print("=" * 70)
    print("SECTION 2: Alert Triage and Activation")
    print("=" * 70)

    activated = mem.activate("alert_circular_001", energy=1.0, top_k=15)
    print("  Spreading activation from alert_circular_001:")
    for r in activated:
        data = mem.graph.get_node_by_label(r.label)
        dtype = data.data.get("type", data.data.get("role", "?")) if data and data.data else "?"
        print(f"    {r.label:35s} activation={r.activation:.3f} depth={r.depth} [{dtype}]")
    print()

    retrieved = mem.retrieve("acct_zenith_holdings", top_k=15, iterations=3)
    print("  Retrieval from acct_zenith_holdings (suspicious hub account):")
    for r in retrieved[:10]:
        data = mem.graph.get_node_by_label(r.label)
        dtype = data.data.get("type", data.data.get("role", "?")) if data and data.data else "?"
        print(f"    {r.label:35s} [{dtype}]")
    print()

    print("=" * 70)
    print("SECTION 3: Reasoning and Hidden Connection Discovery")
    print("=" * 70)

    mem.add_rules(
        TransitiveRule(edge_label="transferred_to", new_label="transfers_indirectly"),
        InverseRule(edge_label="owns", inverse_label="owned_by"),
        TransitiveRule(edge_label="associated_with", new_label="indirectly_associated"),
    )

    reason_result = mem.reason(
        seed_concepts={"acct_zenith_holdings", "acct_global_trading", "viktor_kingpin"},
        max_depth=3,
        max_total_states=50,
    )

    expansion = reason_result.expansion
    if expansion:
        print(f"  States created:     {expansion.states_created}")
        print(f"  Rules applied:      {expansion.rules_applied}")
        print(f"  Max depth reached:  {expansion.max_depth}")
    print()

    indirect_edges = mem.pattern_match(edge_label="transfers_indirectly")
    print(f"  Indirect transfer chains discovered: {len(indirect_edges)}")
    for edge in indirect_edges[:8]:
        src_label = edge.source_labels[0] if edge.source_labels else "?"
        tgt_label = edge.target_labels[0] if edge.target_labels else "?"
        print(f"    {src_label} -> {tgt_label}")
    if len(indirect_edges) > 8:
        print(f"    ... and {len(indirect_edges) - 8} more")
    print()

    indirect_assoc = mem.pattern_match(edge_label="indirectly_associated")
    print(f"  Indirect associations discovered: {len(indirect_assoc)}")
    for edge in indirect_assoc[:8]:
        src_label = edge.source_labels[0] if edge.source_labels else "?"
        tgt_label = edge.target_labels[0] if edge.target_labels else "?"
        print(f"    {src_label} -- {tgt_label}")
    if len(indirect_assoc) > 8:
        print(f"    ... and {len(indirect_assoc) - 8} more")
    print()

    print("=" * 70)
    print("SECTION 4: Pattern Detection")
    print("=" * 70)

    cycles = mem.detect_cycles(max_cycles=10)
    print(f"  Circular money flows detected: {len(cycles)}")
    for i, cycle in enumerate(cycles):
        print(f"    Cycle {i + 1}: {' -> '.join(cycle)} -> {cycle[0]}")
    print()

    similar = mem.find_similar("acct_zenith_holdings", top_k=10)
    print("  Accounts similar to acct_zenith_holdings:")
    for s in similar:
        other = s.label_b if s.label_a == "acct_zenith_holdings" else s.label_a
        print(f"    {other:35s} similarity={s.similarity:.3f}")
    print()

    print("=" * 70)
    print("SECTION 5: Funnel Account Identification")
    print("=" * 70)

    degree = mem.degree_centrality()
    transferred = mem.pattern_match(edge_label="transferred_to")

    in_degree: dict[str, int] = {}
    out_degree: dict[str, int] = {}
    for edge in transferred:
        for lbl in edge.target_labels:
            in_degree[lbl] = in_degree.get(lbl, 0) + 1
        for lbl in edge.source_labels:
            out_degree[lbl] = out_degree.get(lbl, 0) + 1

    all_acct_labels = set(in_degree.keys()) | set(out_degree.keys())
    funnel_accounts = []
    for acct in all_acct_labels:
        ind = in_degree.get(acct, 0)
        outd = out_degree.get(acct, 0)
        if ind >= 2 and outd >= 2:
            funnel_accounts.append((acct, ind, outd, ind + outd))

    funnel_accounts.sort(key=lambda x: -x[3])
    print(f"  Funnel accounts (in_degree >= 2 AND out_degree >= 2):")
    for acct, ind, outd, total in funnel_accounts:
        node = mem.graph.get_node_by_label(acct)
        flagged = node.data.get("flagged", False) if node and node.data else False
        flag_str = "FLAGGED" if flagged else "clean"
        print(f"    {acct:30s} in={ind} out={outd} total={total} [{flag_str}]")
    print()

    print("=" * 70)
    print("SECTION 6: Cluster Analysis and Risk Ranking")
    print("=" * 70)

    flagged_node_labels = set()
    for label, data in accounts.items():
        if data.get("flagged"):
            flagged_node_labels.add(label)
    for label, data in persons.items():
        if data.get("risk_score", 0) >= 0.60:
            flagged_node_labels.add(label)
    for label, data in alerts.items():
        if data.get("status") in ("active", "escalated"):
            flagged_node_labels.add(label)
    for label, data in ip_devices.items():
        if data.get("type") in ("vpn", "tor"):
            flagged_node_labels.add(label)

    components = mem.connected_components()
    suspicious_clusters = []
    for comp in components:
        overlap = comp & flagged_node_labels
        if len(overlap) >= 3:
            suspicious_clusters.append((comp, overlap))

    suspicious_clusters.sort(key=lambda x: -len(x[1]))
    print(f"  Suspicious entity clusters (>= 3 flagged nodes): {len(suspicious_clusters)}")
    for i, (comp, overlap) in enumerate(suspicious_clusters[:5]):
        print(f"    Cluster {i + 1}: {len(comp)} nodes, {len(overlap)} flagged")
        persons_in = [l for l in comp if l in persons]
        accounts_in = [l for l in comp if l in accounts]
        entities_in = [l for l in comp if l in entities]
        ip_in = [l for l in comp if l in ip_devices]
        if persons_in:
            print(f"      Persons: {', '.join(sorted(persons_in)[:8])}")
        if accounts_in:
            print(f"      Accounts: {', '.join(sorted(accounts_in)[:8])}")
        if entities_in:
            print(f"      Entities: {', '.join(sorted(entities_in)[:6])}")
        if ip_in:
            print(f"      IPs/Devices: {', '.join(sorted(ip_in)[:6])}")
    print()

    betweenness = mem.betweenness_centrality()
    suspect_persons = {l: d for l, d in persons.items() if d.get("risk_score", 0) >= 0.50}
    ranked = sorted(suspect_persons.items(), key=lambda x: -betweenness.get(x[0], 0))
    print("  Risk ranking of suspects (by betweenness centrality):")
    for label, data in ranked:
        bc = betweenness.get(label, 0)
        dc = degree.get(label, 0)
        print(f"    {label:25s} risk={data['risk_score']:.2f} "
              f"betweenness={bc:.4f} degree={dc:.3f} "
              f"role={data['role']}")
    print()

    print("=" * 70)
    print("SECTION 7: Investigation Summary")
    print("=" * 70)

    stats = mem.stats()
    print(f"  Graph: {stats.nodes} nodes, {stats.edges} edges")
    print(f"  Connected components: {stats.components}")
    print(f"  Cycles detected: {len(cycles)}")
    print(f"  Funnel accounts: {len(funnel_accounts)}")
    print(f"  Suspicious clusters: {len(suspicious_clusters)}")
    print(f"  Indirect transfers inferred: {len(indirect_edges)}")
    print(f"  Indirect associations inferred: {len(indirect_assoc)}")
    print()

    if ranked:
        leader = ranked[0]
        print(f"  Identified ring leader: {leader[0]}")
        print(f"    Role: {leader[1]['role']}")
        print(f"    Risk score: {leader[1]['risk_score']:.2f}")
        print(f"    Betweenness centrality: {betweenness.get(leader[0], 0):.4f}")
    print()

    if suspicious_clusters:
        sg = mem.subgraph(suspicious_clusters[0][0])
        print(f"  Largest suspicious subgraph: {sg.node_count} nodes, {sg.edge_count} edges")
    print()

    print("  Recommended next steps:")
    print("    1. File SAR for structuring: tx_001 through tx_004, tx_009, tx_014")
    print("    2. Freeze accounts: acct_zenith_holdings, acct_global_trading, acct_alpha_consulting")
    print("    3. Subpoena records for ent_global_trading_ltd, ent_zenith_holdings_llc")
    print("    4. Interview informant_reyes regarding katya_recruiter and mule network")
    print("    5. Coordinate with agent_clark for cross-border request on offshore entities")
    print("    6. Monitor ip_vpn_moscow, ip_tor_exit1, ip_tor_exit2 for further access")


if __name__ == "__main__":
    main()
