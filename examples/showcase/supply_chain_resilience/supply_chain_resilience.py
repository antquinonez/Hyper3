"""
Supply Chain Risk Assessment and Disruption Analysis
=====================================================

Models a multi-tier global supply chain network with 120+ nodes and 250+ edges,
analyzes it for vulnerabilities, single points of failure, risk cascade
propagation, and produces actionable diversification recommendations.

Run with:
    .venv/bin/python examples/showcase/supply_chain_resilience/supply_chain_resilience.py
"""

from __future__ import annotations

from hyper3 import HypergraphMemory, TransitiveRule, InverseRule, Modality, top_k


def main():
    mem = HypergraphMemory(evolve_interval=0)

    # =====================================================================
    # SECTION 1: Supply Chain Network Construction
    # =====================================================================
    print("=" * 70)
    print("SECTION 1: Supply Chain Network Construction")
    print("=" * 70)

    suppliers = {
        "sup_t1_us_steel": {"category": "supplier", "tier": 1, "country": "US", "lead_time_days": 14, "reliability_score": 0.92, "capacity": 50000, "single_source": False, "material": "steel"},
        "sup_t1_us_aluminum": {"category": "supplier", "tier": 1, "country": "US", "lead_time_days": 12, "reliability_score": 0.89, "capacity": 30000, "single_source": False, "material": "aluminum"},
        "sup_t1_germany_semicon": {"category": "supplier", "tier": 1, "country": "Germany", "lead_time_days": 21, "reliability_score": 0.95, "capacity": 10000, "single_source": True, "material": "semiconductor"},
        "sup_t1_taiwan_semicon": {"category": "supplier", "tier": 1, "country": "Taiwan", "lead_time_days": 28, "reliability_score": 0.93, "capacity": 15000, "single_source": True, "material": "semiconductor"},
        "sup_t1_japan_sensor": {"category": "supplier", "tier": 1, "country": "Japan", "lead_time_days": 18, "reliability_score": 0.96, "capacity": 8000, "single_source": True, "material": "sensor"},
        "sup_t1_china_rare_earth": {"category": "supplier", "tier": 1, "country": "China", "lead_time_days": 35, "reliability_score": 0.85, "capacity": 12000, "single_source": True, "material": "rare_earth"},
        "sup_t1_sk_battery": {"category": "supplier", "tier": 1, "country": "South_Korea", "lead_time_days": 25, "reliability_score": 0.91, "capacity": 20000, "single_source": False, "material": "battery"},
        "sup_t1_mexico_rubber": {"category": "supplier", "tier": 1, "country": "Mexico", "lead_time_days": 10, "reliability_score": 0.88, "capacity": 25000, "single_source": False, "material": "rubber"},
        "sup_t1_chile_copper": {"category": "supplier", "tier": 1, "country": "Chile", "lead_time_days": 22, "reliability_score": 0.90, "capacity": 40000, "single_source": False, "material": "copper"},
        "sup_t1_vietnam_elec": {"category": "supplier", "tier": 1, "country": "Vietnam", "lead_time_days": 30, "reliability_score": 0.82, "capacity": 18000, "single_source": False, "material": "electronics"},
        "sup_t1_india_textile": {"category": "supplier", "tier": 1, "country": "India", "lead_time_days": 20, "reliability_score": 0.87, "capacity": 22000, "single_source": False, "material": "textile"},
        "sup_t1_canada_lumber": {"category": "supplier", "tier": 1, "country": "Canada", "lead_time_days": 15, "reliability_score": 0.93, "capacity": 35000, "single_source": False, "material": "lumber"},
        "sup_t2_australia_iron": {"category": "supplier", "tier": 2, "country": "Australia", "lead_time_days": 40, "reliability_score": 0.88, "capacity": 80000, "single_source": False, "material": "iron_ore"},
        "sup_t2_brazil_iron": {"category": "supplier", "tier": 2, "country": "Brazil", "lead_time_days": 45, "reliability_score": 0.84, "capacity": 70000, "single_source": False, "material": "iron_ore"},
        "sup_t2_congo_cobalt": {"category": "supplier", "tier": 2, "country": "DRC", "lead_time_days": 50, "reliability_score": 0.72, "capacity": 15000, "single_source": True, "material": "cobalt"},
        "sup_t2_indonesia_nickel": {"category": "supplier", "tier": 2, "country": "Indonesia", "lead_time_days": 38, "reliability_score": 0.80, "capacity": 25000, "single_source": False, "material": "nickel"},
        "sup_t2_china_silicon": {"category": "supplier", "tier": 2, "country": "China", "lead_time_days": 30, "reliability_score": 0.83, "capacity": 20000, "single_source": True, "material": "silicon"},
        "sup_t2_thailand_rubber": {"category": "supplier", "tier": 2, "country": "Thailand", "lead_time_days": 25, "reliability_score": 0.86, "capacity": 30000, "single_source": False, "material": "natural_rubber"},
        "sup_t2_kazakhstan_uranium": {"category": "supplier", "tier": 2, "country": "Kazakhstan", "lead_time_days": 55, "reliability_score": 0.78, "capacity": 5000, "single_source": True, "material": "uranium"},
        "sup_t2_peru_zinc": {"category": "supplier", "tier": 2, "country": "Peru", "lead_time_days": 35, "reliability_score": 0.82, "capacity": 18000, "single_source": False, "material": "zinc"},
        "sup_t2_sa_platinum": {"category": "supplier", "tier": 2, "country": "South_Africa", "lead_time_days": 42, "reliability_score": 0.80, "capacity": 8000, "single_source": True, "material": "platinum"},
        "sup_t2_china_graphite": {"category": "supplier", "tier": 2, "country": "China", "lead_time_days": 32, "reliability_score": 0.84, "capacity": 35000, "single_source": True, "material": "graphite"},
        "sup_t2_mongolia_copper": {"category": "supplier", "tier": 2, "country": "Mongolia", "lead_time_days": 48, "reliability_score": 0.75, "capacity": 12000, "single_source": False, "material": "copper_ore"},
        "sup_t2_chile_lithium": {"category": "supplier", "tier": 2, "country": "Chile", "lead_time_days": 36, "reliability_score": 0.87, "capacity": 28000, "single_source": False, "material": "lithium"},
        "sup_t3_australia_bauxite": {"category": "supplier", "tier": 3, "country": "Australia", "lead_time_days": 60, "reliability_score": 0.90, "capacity": 100000, "single_source": False, "material": "bauxite"},
        "sup_t3_brazil_nickel": {"category": "supplier", "tier": 3, "country": "Brazil", "lead_time_days": 55, "reliability_score": 0.82, "capacity": 20000, "single_source": False, "material": "nickel_ore"},
        "sup_t3_drc_cobalt": {"category": "supplier", "tier": 3, "country": "DRC", "lead_time_days": 65, "reliability_score": 0.68, "capacity": 10000, "single_source": True, "material": "cobalt_ore"},
        "sup_t3_russia_palladium": {"category": "supplier", "tier": 3, "country": "Russia", "lead_time_days": 70, "reliability_score": 0.65, "capacity": 6000, "single_source": True, "material": "palladium"},
        "sup_t3_china_coal": {"category": "supplier", "tier": 3, "country": "China", "lead_time_days": 20, "reliability_score": 0.88, "capacity": 200000, "single_source": False, "material": "coal"},
        "sup_t3_india_mica": {"category": "supplier", "tier": 3, "country": "India", "lead_time_days": 45, "reliability_score": 0.76, "capacity": 15000, "single_source": False, "material": "mica"},
        "sup_t3_chile_lithium_ore": {"category": "supplier", "tier": 3, "country": "Chile", "lead_time_days": 58, "reliability_score": 0.85, "capacity": 32000, "single_source": False, "material": "lithium_ore"},
        "sup_t3_argentina_lithium": {"category": "supplier", "tier": 3, "country": "Argentina", "lead_time_days": 52, "reliability_score": 0.83, "capacity": 25000, "single_source": False, "material": "lithium_brine"},
    }

    products = {
        "prod_raw_steel": {"category": "product", "type": "raw_material", "criticality": "high", "alternate_count": 3},
        "prod_raw_aluminum": {"category": "product", "type": "raw_material", "criticality": "high", "alternate_count": 4},
        "prod_raw_copper": {"category": "product", "type": "raw_material", "criticality": "critical", "alternate_count": 2},
        "prod_semiconductor": {"category": "product", "type": "electronic", "criticality": "critical", "alternate_count": 2},
        "prod_sensor": {"category": "product", "type": "electronic", "criticality": "critical", "alternate_count": 1},
        "prod_rare_earth_magnet": {"category": "product", "type": "raw_material", "criticality": "critical", "alternate_count": 1},
        "prod_battery_cell": {"category": "product", "type": "component", "criticality": "critical", "alternate_count": 2},
        "prod_rubber_compound": {"category": "product", "type": "raw_material", "criticality": "medium", "alternate_count": 5},
        "prod_wiring_harness": {"category": "product", "type": "component", "criticality": "high", "alternate_count": 3},
        "prod_circuit_board": {"category": "product", "type": "electronic", "criticality": "high", "alternate_count": 4},
        "prod_microcontroller": {"category": "product", "type": "electronic", "criticality": "critical", "alternate_count": 2},
        "prod_led_display": {"category": "product", "type": "electronic", "criticality": "medium", "alternate_count": 3},
        "prod_power_module": {"category": "product", "type": "component", "criticality": "high", "alternate_count": 2},
        "prod_chassis": {"category": "product", "type": "assembly", "criticality": "high", "alternate_count": 1},
        "prod_engine": {"category": "product", "type": "assembly", "criticality": "critical", "alternate_count": 1},
        "prod_transmission": {"category": "product", "type": "assembly", "criticality": "critical", "alternate_count": 1},
        "prod_battery_pack": {"category": "product", "type": "assembly", "criticality": "critical", "alternate_count": 1},
        "prod_ecu": {"category": "product", "type": "assembly", "criticality": "critical", "alternate_count": 1},
        "prod_infotainment": {"category": "product", "type": "assembly", "criticality": "medium", "alternate_count": 2},
        "prod_adas": {"category": "product", "type": "assembly", "criticality": "critical", "alternate_count": 1},
        "prod_ev_motor": {"category": "product", "type": "assembly", "criticality": "critical", "alternate_count": 1},
        "prod_vehicle": {"category": "product", "type": "finished_product", "criticality": "critical", "alternate_count": 0},
    }

    factories = {
        "mfg_detroit_engine": {"category": "factory", "location": "Detroit_US", "utilization": 0.88, "automation_level": "high"},
        "mfg_stuttgart_ecu": {"category": "factory", "location": "Stuttgart_DE", "utilization": 0.92, "automation_level": "high"},
        "mfg_tokyo_sensor": {"category": "factory", "location": "Tokyo_JP", "utilization": 0.85, "automation_level": "high"},
        "mfg_shanghai_chip": {"category": "factory", "location": "Shanghai_CN", "utilization": 0.95, "automation_level": "high"},
        "mfg_monterrey_chassis": {"category": "factory", "location": "Monterrey_MX", "utilization": 0.78, "automation_level": "medium"},
        "mfg_seoul_battery": {"category": "factory", "location": "Seoul_KR", "utilization": 0.90, "automation_level": "high"},
        "mfg_pune_wiring": {"category": "factory", "location": "Pune_IN", "utilization": 0.82, "automation_level": "medium"},
        "mfg_bangkok_rubber": {"category": "factory", "location": "Bangkok_TH", "utilization": 0.75, "automation_level": "low"},
        "mfg_taipei_board": {"category": "factory", "location": "Taipei_TW", "utilization": 0.88, "automation_level": "high"},
        "mfg_munich_transmission": {"category": "factory", "location": "Munich_DE", "utilization": 0.91, "automation_level": "high"},
        "mfg_chicago_adas": {"category": "factory", "location": "Chicago_US", "utilization": 0.86, "automation_level": "high"},
        "mfg_atlanta_suv": {"category": "factory", "location": "Atlanta_US", "utilization": 0.93, "automation_level": "high"},
        "mfg_dallas_sedan": {"category": "factory", "location": "Dallas_US", "utilization": 0.87, "automation_level": "high"},
        "mfg_frankfurt_motor": {"category": "factory", "location": "Frankfurt_DE", "utilization": 0.89, "automation_level": "high"},
        "mfg_nagoya_display": {"category": "factory", "location": "Nagoya_JP", "utilization": 0.84, "automation_level": "high"},
        "mfg_louisville_truck": {"category": "factory", "location": "Louisville_US", "utilization": 0.80, "automation_level": "medium"},
    }

    dist_centers = {
        "dc_nyc_east": {"category": "distribution", "region": "Northeast_US", "capacity": 5000, "backup": True},
        "dc_la_west": {"category": "distribution", "region": "West_US", "capacity": 4500, "backup": True},
        "dc_chicago_midwest": {"category": "distribution", "region": "Midwest_US", "capacity": 6000, "backup": True},
        "dc_dallas_south": {"category": "distribution", "region": "South_US", "capacity": 4000, "backup": False},
        "dc_miami_se": {"category": "distribution", "region": "Southeast_US", "capacity": 3500, "backup": True},
        "dc_seattle_nw": {"category": "distribution", "region": "Pacific_NW", "capacity": 3000, "backup": False},
        "dc_london_eu": {"category": "distribution", "region": "Western_EU", "capacity": 5500, "backup": True},
        "dc_frankfurt_eu": {"category": "distribution", "region": "Central_EU", "capacity": 5000, "backup": True},
        "dc_tokyo_apac": {"category": "distribution", "region": "Japan", "capacity": 4000, "backup": True},
        "dc_shanghai_apac": {"category": "distribution", "region": "China", "capacity": 7000, "backup": False},
        "dc_sydney_oceania": {"category": "distribution", "region": "Oceania", "capacity": 2500, "backup": True},
        "dc_mumbai_sa": {"category": "distribution", "region": "South_Asia", "capacity": 3500, "backup": False},
        "dc_saopaulo_latam": {"category": "distribution", "region": "Latin_America", "capacity": 4000, "backup": True},
        "dc_mexicocity_latam": {"category": "distribution", "region": "Mexico", "capacity": 3000, "backup": False},
        "dc_dubai_mena": {"category": "distribution", "region": "Middle_East", "capacity": 3500, "backup": True},
        "dc_singapore_sea": {"category": "distribution", "region": "Southeast_Asia", "capacity": 4500, "backup": True},
    }

    transport = {
        "trans_pacific_ship": {"category": "transport", "mode": "ship", "transit_days": 28, "cost": 2800},
        "trans_atlantic_ship": {"category": "transport", "mode": "ship", "transit_days": 21, "cost": 2200},
        "trans_asia_europe_rail": {"category": "transport", "mode": "rail", "transit_days": 18, "cost": 3500},
        "trans_na_truck": {"category": "transport", "mode": "truck", "transit_days": 5, "cost": 1200},
        "trans_eu_rail": {"category": "transport", "mode": "rail", "transit_days": 3, "cost": 800},
        "trans_intra_asia_ship": {"category": "transport", "mode": "ship", "transit_days": 10, "cost": 900},
        "trans_air_global": {"category": "transport", "mode": "air", "transit_days": 2, "cost": 12000},
        "trans_truck_us_east": {"category": "transport", "mode": "truck", "transit_days": 3, "cost": 600},
        "trans_truck_us_west": {"category": "transport", "mode": "truck", "transit_days": 4, "cost": 700},
        "trans_truck_eu": {"category": "transport", "mode": "truck", "transit_days": 2, "cost": 500},
        "trans_rail_china_eu": {"category": "transport", "mode": "rail", "transit_days": 16, "cost": 3000},
        "trans_suez_ship": {"category": "transport", "mode": "ship", "transit_days": 25, "cost": 2500},
        "trans_panama_ship": {"category": "transport", "mode": "ship", "transit_days": 15, "cost": 1800},
        "trans_air_asia_na": {"category": "transport", "mode": "air", "transit_days": 1, "cost": 15000},
        "trans_rail_siberian": {"category": "transport", "mode": "rail", "transit_days": 22, "cost": 2800},
        "trans_truck_mx_us": {"category": "transport", "mode": "truck", "transit_days": 2, "cost": 400},
    }

    risks = {
        "risk_earthquake_pacific": {"category": "risk", "type": "natural", "probability": 0.15, "impact": 0.90},
        "risk_typhoon_asia": {"category": "risk", "type": "natural", "probability": 0.25, "impact": 0.70},
        "risk_trade_war": {"category": "risk", "type": "geopolitical", "probability": 0.40, "impact": 0.85},
        "risk_sanctions": {"category": "risk", "type": "geopolitical", "probability": 0.30, "impact": 0.80},
        "risk_pandemic": {"category": "risk", "type": "natural", "probability": 0.10, "impact": 0.95},
        "risk_port_congestion": {"category": "risk", "type": "climate", "probability": 0.35, "impact": 0.60},
        "risk_cyber_attack": {"category": "risk", "type": "regulatory", "probability": 0.20, "impact": 0.75},
        "risk_tariff": {"category": "risk", "type": "regulatory", "probability": 0.45, "impact": 0.50},
        "risk_flood": {"category": "risk", "type": "climate", "probability": 0.20, "impact": 0.65},
        "risk_labor_strike": {"category": "risk", "type": "regulatory", "probability": 0.15, "impact": 0.70},
        "risk_material_shortage": {"category": "risk", "type": "natural", "probability": 0.30, "impact": 0.80},
        "risk_geopolitical_tension": {"category": "risk", "type": "geopolitical", "probability": 0.35, "impact": 0.75},
    }

    customers = {
        "mkt_na_automotive": {"category": "customer", "region": "North_America", "revenue_share": 0.35},
        "mkt_eu_automotive": {"category": "customer", "region": "Europe", "revenue_share": 0.25},
        "mkt_apac_automotive": {"category": "customer", "region": "Asia_Pacific", "revenue_share": 0.20},
        "mkt_latam_automotive": {"category": "customer", "region": "Latin_America", "revenue_share": 0.08},
        "mkt_na_trucking": {"category": "customer", "region": "North_America", "revenue_share": 0.10},
        "mkt_eu_ev": {"category": "customer", "region": "Europe", "revenue_share": 0.15},
        "mkt_china_ev": {"category": "customer", "region": "China", "revenue_share": 0.18},
        "mkt_india_ev": {"category": "customer", "region": "India", "revenue_share": 0.07},
        "mkt_fleet_na": {"category": "customer", "region": "North_America", "revenue_share": 0.12},
        "mkt_rental": {"category": "customer", "region": "Global", "revenue_share": 0.05},
        "mkt_defense": {"category": "customer", "region": "North_America", "revenue_share": 0.08},
        "mkt_agriculture": {"category": "customer", "region": "Global", "revenue_share": 0.04},
    }

    all_nodes = {**suppliers, **products, **factories, **dist_centers, **transport, **risks, **customers}
    for name, data in all_nodes.items():
        mem.add(name, data=data)

    supplies_to = [
        ("sup_t3_australia_bauxite", "sup_t2_australia_iron"),
        ("sup_t3_australia_bauxite", "sup_t2_brazil_iron"),
        ("sup_t3_brazil_nickel", "sup_t2_indonesia_nickel"),
        ("sup_t3_drc_cobalt", "sup_t2_congo_cobalt"),
        ("sup_t3_russia_palladium", "sup_t2_sa_platinum"),
        ("sup_t3_china_coal", "sup_t2_china_silicon"),
        ("sup_t3_china_coal", "sup_t2_china_graphite"),
        ("sup_t3_india_mica", "sup_t2_china_silicon"),
        ("sup_t3_chile_lithium_ore", "sup_t2_chile_lithium"),
        ("sup_t3_argentina_lithium", "sup_t2_chile_lithium"),
        ("sup_t3_australia_bauxite", "sup_t2_mongolia_copper"),
        ("sup_t3_brazil_nickel", "sup_t2_brazil_iron"),
        ("sup_t3_drc_cobalt", "sup_t2_indonesia_nickel"),
        ("sup_t3_russia_palladium", "sup_t2_mongolia_copper"),
        ("sup_t3_india_mica", "sup_t2_peru_zinc"),
        ("sup_t3_chile_lithium_ore", "sup_t2_china_graphite"),
        ("sup_t2_australia_iron", "sup_t1_us_steel"),
        ("sup_t2_brazil_iron", "sup_t1_us_steel"),
        ("sup_t2_china_silicon", "sup_t1_germany_semicon"),
        ("sup_t2_china_silicon", "sup_t1_taiwan_semicon"),
        ("sup_t2_congo_cobalt", "sup_t1_sk_battery"),
        ("sup_t2_indonesia_nickel", "sup_t1_sk_battery"),
        ("sup_t2_thailand_rubber", "sup_t1_mexico_rubber"),
        ("sup_t2_sa_platinum", "sup_t1_germany_semicon"),
        ("sup_t2_chile_lithium", "sup_t1_sk_battery"),
        ("sup_t2_china_graphite", "sup_t1_china_rare_earth"),
        ("sup_t2_mongolia_copper", "sup_t1_chile_copper"),
        ("sup_t2_peru_zinc", "sup_t1_chile_copper"),
        ("sup_t2_china_silicon", "sup_t1_vietnam_elec"),
        ("sup_t2_australia_iron", "sup_t1_us_aluminum"),
        ("sup_t2_kazakhstan_uranium", "sup_t1_sk_battery"),
        ("sup_t2_brazil_iron", "sup_t1_us_aluminum"),
        ("sup_t2_china_graphite", "sup_t1_sk_battery"),
        ("sup_t2_thailand_rubber", "sup_t1_india_textile"),
        ("sup_t2_australia_iron", "sup_t1_canada_lumber"),
        ("sup_t1_us_steel", "prod_raw_steel"),
        ("sup_t1_us_aluminum", "prod_raw_aluminum"),
        ("sup_t1_chile_copper", "prod_raw_copper"),
        ("sup_t1_germany_semicon", "prod_semiconductor"),
        ("sup_t1_taiwan_semicon", "prod_semiconductor"),
        ("sup_t1_japan_sensor", "prod_sensor"),
        ("sup_t1_china_rare_earth", "prod_rare_earth_magnet"),
        ("sup_t1_sk_battery", "prod_battery_cell"),
        ("sup_t1_mexico_rubber", "prod_rubber_compound"),
        ("sup_t1_chile_copper", "prod_wiring_harness"),
        ("sup_t1_germany_semicon", "prod_circuit_board"),
        ("sup_t1_taiwan_semicon", "prod_microcontroller"),
        ("sup_t1_vietnam_elec", "prod_led_display"),
        ("sup_t1_chile_copper", "prod_power_module"),
        ("sup_t1_us_steel", "prod_chassis"),
        ("sup_t1_us_aluminum", "prod_chassis"),
        ("sup_t1_us_steel", "prod_engine"),
        ("sup_t1_us_aluminum", "prod_engine"),
        ("sup_t1_germany_semicon", "prod_transmission"),
        ("sup_t1_sk_battery", "prod_battery_pack"),
        ("sup_t1_china_rare_earth", "prod_ev_motor"),
        ("sup_t1_japan_sensor", "prod_adas"),
        ("sup_t1_taiwan_semicon", "prod_ecu"),
        ("sup_t1_vietnam_elec", "prod_infotainment"),
        ("sup_t1_india_textile", "prod_wiring_harness"),
        ("sup_t1_canada_lumber", "prod_rubber_compound"),
    ]

    manufactured_at = [
        ("prod_engine", "mfg_detroit_engine"),
        ("prod_ecu", "mfg_stuttgart_ecu"),
        ("prod_sensor", "mfg_tokyo_sensor"),
        ("prod_semiconductor", "mfg_shanghai_chip"),
        ("prod_chassis", "mfg_monterrey_chassis"),
        ("prod_battery_cell", "mfg_seoul_battery"),
        ("prod_wiring_harness", "mfg_pune_wiring"),
        ("prod_rubber_compound", "mfg_bangkok_rubber"),
        ("prod_circuit_board", "mfg_taipei_board"),
        ("prod_transmission", "mfg_munich_transmission"),
        ("prod_adas", "mfg_chicago_adas"),
        ("prod_vehicle", "mfg_atlanta_suv"),
        ("prod_vehicle", "mfg_dallas_sedan"),
        ("prod_ev_motor", "mfg_frankfurt_motor"),
        ("prod_led_display", "mfg_nagoya_display"),
        ("prod_battery_pack", "mfg_louisville_truck"),
    ]

    stored_at = [
        ("prod_vehicle", "dc_nyc_east"),
        ("prod_vehicle", "dc_la_west"),
        ("prod_vehicle", "dc_chicago_midwest"),
        ("prod_vehicle", "dc_dallas_south"),
        ("prod_vehicle", "dc_miami_se"),
        ("prod_vehicle", "dc_london_eu"),
        ("prod_vehicle", "dc_frankfurt_eu"),
        ("prod_vehicle", "dc_tokyo_apac"),
        ("prod_vehicle", "dc_shanghai_apac"),
        ("prod_vehicle", "dc_saopaulo_latam"),
        ("prod_vehicle", "dc_dubai_mena"),
        ("prod_vehicle", "dc_singapore_sea"),
        ("prod_engine", "dc_nyc_east"),
        ("prod_engine", "dc_chicago_midwest"),
        ("prod_battery_pack", "dc_la_west"),
        ("prod_battery_pack", "dc_frankfurt_eu"),
        ("prod_ecu", "dc_tokyo_apac"),
        ("prod_ecu", "dc_frankfurt_eu"),
        ("prod_adas", "dc_nyc_east"),
        ("prod_adas", "dc_london_eu"),
        ("prod_ev_motor", "dc_frankfurt_eu"),
        ("prod_ev_motor", "dc_shanghai_apac"),
        ("prod_transmission", "dc_chicago_midwest"),
        ("prod_transmission", "dc_dallas_south"),
    ]

    transported_via = [
        ("mfg_shanghai_chip", "trans_pacific_ship"),
        ("mfg_tokyo_sensor", "trans_pacific_ship"),
        ("mfg_stuttgart_ecu", "trans_atlantic_ship"),
        ("mfg_munich_transmission", "trans_atlantic_ship"),
        ("mfg_taipei_board", "trans_asia_europe_rail"),
        ("mfg_detroit_engine", "trans_na_truck"),
        ("mfg_stuttgart_ecu", "trans_eu_rail"),
        ("mfg_bangkok_rubber", "trans_intra_asia_ship"),
        ("mfg_seoul_battery", "trans_air_global"),
        ("mfg_detroit_engine", "trans_truck_us_east"),
        ("mfg_chicago_adas", "trans_truck_us_west"),
        ("mfg_stuttgart_ecu", "trans_truck_eu"),
        ("mfg_taipei_board", "trans_rail_china_eu"),
        ("mfg_frankfurt_motor", "trans_suez_ship"),
        ("mfg_seoul_battery", "trans_panama_ship"),
        ("mfg_shanghai_chip", "trans_air_asia_na"),
        ("mfg_monterrey_chassis", "trans_rail_siberian"),
        ("mfg_monterrey_chassis", "trans_truck_mx_us"),
        ("mfg_pune_wiring", "trans_suez_ship"),
        ("mfg_nagoya_display", "trans_pacific_ship"),
    ]

    affected_by = [
        ("risk_earthquake_pacific", "sup_t1_japan_sensor"),
        ("risk_earthquake_pacific", "sup_t1_taiwan_semicon"),
        ("risk_typhoon_asia", "sup_t1_taiwan_semicon"),
        ("risk_typhoon_asia", "sup_t2_thailand_rubber"),
        ("risk_typhoon_asia", "sup_t1_vietnam_elec"),
        ("risk_trade_war", "sup_t1_china_rare_earth"),
        ("risk_trade_war", "sup_t1_us_steel"),
        ("risk_trade_war", "sup_t2_china_silicon"),
        ("risk_sanctions", "sup_t3_russia_palladium"),
        ("risk_sanctions", "sup_t2_kazakhstan_uranium"),
        ("risk_pandemic", "sup_t2_congo_cobalt"),
        ("risk_pandemic", "sup_t2_indonesia_nickel"),
        ("risk_pandemic", "sup_t3_drc_cobalt"),
        ("risk_port_congestion", "sup_t3_australia_bauxite"),
        ("risk_port_congestion", "sup_t2_australia_iron"),
        ("risk_port_congestion", "sup_t1_chile_copper"),
        ("risk_cyber_attack", "sup_t1_germany_semicon"),
        ("risk_cyber_attack", "sup_t1_taiwan_semicon"),
        ("risk_tariff", "sup_t1_mexico_rubber"),
        ("risk_tariff", "sup_t2_china_silicon"),
        ("risk_flood", "sup_t2_brazil_iron"),
        ("risk_flood", "sup_t3_brazil_nickel"),
        ("risk_labor_strike", "sup_t1_us_steel"),
        ("risk_labor_strike", "sup_t1_us_aluminum"),
        ("risk_material_shortage", "sup_t2_congo_cobalt"),
        ("risk_material_shortage", "sup_t2_chile_lithium"),
        ("risk_geopolitical_tension", "sup_t1_taiwan_semicon"),
        ("risk_geopolitical_tension", "sup_t2_china_graphite"),
        ("risk_earthquake_pacific", "mfg_tokyo_sensor"),
        ("risk_earthquake_pacific", "mfg_nagoya_display"),
        ("risk_typhoon_asia", "mfg_shanghai_chip"),
        ("risk_pandemic", "mfg_pune_wiring"),
        ("risk_pandemic", "mfg_bangkok_rubber"),
        ("risk_labor_strike", "mfg_detroit_engine"),
        ("risk_labor_strike", "mfg_atlanta_suv"),
        ("risk_flood", "mfg_monterrey_chassis"),
        ("risk_cyber_attack", "mfg_stuttgart_ecu"),
        ("risk_earthquake_pacific", "trans_pacific_ship"),
        ("risk_typhoon_asia", "trans_intra_asia_ship"),
        ("risk_port_congestion", "trans_suez_ship"),
        ("risk_port_congestion", "trans_panama_ship"),
        ("risk_trade_war", "trans_rail_china_eu"),
        ("risk_geopolitical_tension", "trans_rail_siberian"),
        ("sup_t1_japan_sensor", "prod_sensor"),
        ("sup_t1_taiwan_semicon", "prod_semiconductor"),
        ("sup_t1_germany_semicon", "prod_semiconductor"),
        ("sup_t1_china_rare_earth", "prod_rare_earth_magnet"),
        ("sup_t2_congo_cobalt", "prod_battery_cell"),
        ("sup_t1_sk_battery", "prod_battery_cell"),
        ("prod_semiconductor", "prod_microcontroller"),
        ("prod_semiconductor", "prod_circuit_board"),
        ("prod_sensor", "prod_adas"),
        ("prod_sensor", "prod_ecu"),
        ("prod_rare_earth_magnet", "prod_ev_motor"),
        ("prod_battery_cell", "prod_battery_pack"),
        ("prod_microcontroller", "prod_ecu"),
        ("prod_microcontroller", "prod_infotainment"),
        ("prod_microcontroller", "prod_adas"),
        ("prod_circuit_board", "prod_ecu"),
        ("prod_circuit_board", "prod_power_module"),
        ("prod_chassis", "prod_vehicle"),
        ("prod_engine", "prod_vehicle"),
        ("prod_transmission", "prod_vehicle"),
        ("prod_battery_pack", "prod_vehicle"),
        ("prod_ecu", "prod_vehicle"),
        ("prod_infotainment", "prod_vehicle"),
        ("prod_adas", "prod_vehicle"),
        ("prod_ev_motor", "prod_vehicle"),
    ]

    depends_on = [
        ("prod_wiring_harness", "prod_raw_copper"),
        ("prod_wiring_harness", "prod_rubber_compound"),
        ("prod_circuit_board", "prod_semiconductor"),
        ("prod_circuit_board", "prod_raw_copper"),
        ("prod_microcontroller", "prod_semiconductor"),
        ("prod_microcontroller", "prod_circuit_board"),
        ("prod_power_module", "prod_semiconductor"),
        ("prod_power_module", "prod_raw_copper"),
        ("prod_chassis", "prod_raw_steel"),
        ("prod_chassis", "prod_raw_aluminum"),
        ("prod_engine", "prod_raw_steel"),
        ("prod_engine", "prod_raw_aluminum"),
        ("prod_engine", "prod_wiring_harness"),
        ("prod_engine", "prod_power_module"),
        ("prod_transmission", "prod_raw_steel"),
        ("prod_transmission", "prod_semiconductor"),
        ("prod_battery_pack", "prod_battery_cell"),
        ("prod_battery_pack", "prod_rare_earth_magnet"),
        ("prod_battery_pack", "prod_power_module"),
        ("prod_ecu", "prod_semiconductor"),
        ("prod_ecu", "prod_microcontroller"),
        ("prod_ecu", "prod_sensor"),
        ("prod_ecu", "prod_circuit_board"),
        ("prod_infotainment", "prod_led_display"),
        ("prod_infotainment", "prod_microcontroller"),
        ("prod_infotainment", "prod_circuit_board"),
        ("prod_adas", "prod_sensor"),
        ("prod_adas", "prod_semiconductor"),
        ("prod_adas", "prod_microcontroller"),
        ("prod_ev_motor", "prod_rare_earth_magnet"),
        ("prod_ev_motor", "prod_raw_copper"),
        ("prod_vehicle", "prod_chassis"),
        ("prod_vehicle", "prod_engine"),
        ("prod_vehicle", "prod_transmission"),
        ("prod_vehicle", "prod_battery_pack"),
        ("prod_vehicle", "prod_ecu"),
        ("prod_vehicle", "prod_infotainment"),
        ("prod_vehicle", "prod_adas"),
        ("prod_vehicle", "prod_ev_motor"),
    ]

    serves_edges = [
        ("dc_nyc_east", "mkt_na_automotive"),
        ("dc_la_west", "mkt_na_automotive"),
        ("dc_chicago_midwest", "mkt_na_automotive"),
        ("dc_london_eu", "mkt_eu_automotive"),
        ("dc_frankfurt_eu", "mkt_eu_automotive"),
        ("dc_frankfurt_eu", "mkt_eu_ev"),
        ("dc_tokyo_apac", "mkt_apac_automotive"),
        ("dc_shanghai_apac", "mkt_china_ev"),
        ("dc_shanghai_apac", "mkt_apac_automotive"),
        ("dc_saopaulo_latam", "mkt_latam_automotive"),
        ("dc_mexicocity_latam", "mkt_latam_automotive"),
        ("dc_dallas_south", "mkt_na_trucking"),
        ("dc_dallas_south", "mkt_fleet_na"),
        ("dc_mumbai_sa", "mkt_india_ev"),
        ("dc_miami_se", "mkt_rental"),
        ("dc_nyc_east", "mkt_fleet_na"),
        ("dc_la_west", "mkt_defense"),
        ("dc_chicago_midwest", "mkt_na_trucking"),
        ("dc_london_eu", "mkt_rental"),
        ("dc_tokyo_apac", "mkt_china_ev"),
        ("dc_sydney_oceania", "mkt_apac_automotive"),
        ("dc_dubai_mena", "mkt_na_automotive"),
        ("dc_singapore_sea", "mkt_india_ev"),
        ("dc_dallas_south", "mkt_agriculture"),
        ("dc_london_eu", "mkt_defense"),
    ]

    backup_for = [
        ("sup_t1_us_steel", "sup_t2_brazil_iron"),
        ("sup_t1_us_aluminum", "sup_t2_australia_iron"),
        ("sup_t1_germany_semicon", "sup_t1_taiwan_semicon"),
        ("sup_t1_taiwan_semicon", "sup_t1_germany_semicon"),
        ("sup_t1_sk_battery", "sup_t2_chile_lithium"),
        ("sup_t1_mexico_rubber", "sup_t2_thailand_rubber"),
        ("sup_t1_chile_copper", "sup_t2_mongolia_copper"),
        ("sup_t2_australia_iron", "sup_t2_brazil_iron"),
        ("sup_t2_chile_lithium", "sup_t3_argentina_lithium"),
        ("sup_t2_china_silicon", "sup_t3_india_mica"),
        ("dc_nyc_east", "dc_miami_se"),
        ("dc_la_west", "dc_seattle_nw"),
        ("dc_chicago_midwest", "dc_dallas_south"),
        ("dc_london_eu", "dc_frankfurt_eu"),
        ("dc_frankfurt_eu", "dc_london_eu"),
    ]

    edge_groups = [
        (supplies_to, "supplies_to"),
        (manufactured_at, "manufactured_at"),
        (stored_at, "stored_at"),
        (transported_via, "transported_via"),
        (affected_by, "affected_by"),
        (depends_on, "depends_on"),
        (serves_edges, "serves"),
        (backup_for, "backup_for"),
    ]

    total_edges = 0
    for edges, label in edge_groups:
        for src, tgt in edges:
            mem.link(src, tgt, label=label)
        total_edges += len(edges)

    print(f"  Nodes: {mem.size[0]}")
    print(f"  Edges: {mem.size[1]}")
    print(f"    supplies_to:      {len(supplies_to)}")
    print(f"    manufactured_at:   {len(manufactured_at)}")
    print(f"    stored_at:         {len(stored_at)}")
    print(f"    transported_via:   {len(transported_via)}")
    print(f"    affected_by:       {len(affected_by)}")
    print(f"    depends_on:        {len(depends_on)}")
    print(f"    serves:            {len(serves_edges)}")
    print(f"    backup_for:        {len(backup_for)}")
    print()

    # =====================================================================
    # SECTION 2: Centrality Analysis - Critical Nodes & Chokepoints
    # =====================================================================
    print("=" * 70)
    print("SECTION 2: Centrality Analysis - Critical Nodes & Chokepoints")
    print("=" * 70)

    deg = mem.analyze.centrality("degree")
    btw = mem.analyze.centrality("betweenness")

    print("\n  Top 10 by degree centrality (most connected / highest ripple):")
    for name, score in top_k(deg, k=10):
        node = mem.engine.graph.get_node_by_label(name)
        cat = node.data.get("category", "?") if node and node.data else "?"
        print(f"    {name:35s} deg={score:.3f}  [{cat}]")

    print("\n  Top 10 by betweenness centrality (critical chokepoints):")
    for name, score in top_k(btw, k=10):
        node = mem.engine.graph.get_node_by_label(name)
        cat = node.data.get("category", "?") if node and node.data else "?"
        print(f"    {name:35s} btw={score:.3f}  [{cat}]")
    print()

    # =====================================================================
    # SECTION 3: Single Points of Failure
    # =====================================================================
    print("=" * 70)
    print("SECTION 3: Single Points of Failure")
    print("=" * 70)

    single_source_suppliers = [
        (name, data) for name, data in suppliers.items()
        if data.get("single_source")
    ]
    critical_low_alternate = [
        (name, data) for name, data in products.items()
        if data.get("criticality") == "critical" and data.get("alternate_count", 99) <= 1
    ]

    print(f"\n  Single-source suppliers ({len(single_source_suppliers)}):")
    for name, data in sorted(single_source_suppliers, key=lambda x: x[1]["reliability_score"]):
        print(f"    {name:35s} country={data['country']:15s} "
              f"reliability={data['reliability_score']:.2f}  "
              f"lead_time={data['lead_time_days']}d")

    print(f"\n  Critical products with <=1 alternate ({len(critical_low_alternate)}):")
    for name, data in critical_low_alternate:
        print(f"    {name:35s} type={data['type']:18s} alternates={data['alternate_count']}")

    backup_targets = {tgt for _, tgt in backup_for}
    unprotected_suppliers = [
        name for name, data in suppliers.items()
        if data.get("single_source") and name not in backup_targets
    ]
    print(f"\n  Single-source suppliers with NO backup coverage ({len(unprotected_suppliers)}):")
    for name in unprotected_suppliers:
        node = mem.engine.graph.get_node_by_label(name)
        d = node.data if node and node.data else {}
        print(f"    {name:35s} country={d.get('country', '?'):15s} "
              f"material={d.get('material', '?')}")
    print()

    # =====================================================================
    # SECTION 4: Risk Cascade Reasoning
    # =====================================================================
    print("=" * 70)
    print("SECTION 4: Risk Cascade Reasoning")
    print("=" * 70)

    mem.add_rules(
        TransitiveRule(edge_label="supplies_to", new_label="indirectly_supplies"),
        TransitiveRule(edge_label="affected_by", new_label="cascade_affected_by"),
        InverseRule(edge_label="supplies_to", inverse_label="supplied_by"),
    )

    cascade_seeds = (
        {"risk_earthquake_pacific", "risk_trade_war", "risk_pandemic",
         "risk_geopolitical_tension", "risk_sanctions", "risk_material_shortage"}
        | {n for n in suppliers}
        | {n for n in products}
    )
    print(f"\n  Seed nodes for reasoning: {len(cascade_seeds)}")

    print("\n  Phase 1: Risk cascade reasoning (affected_by)...")
    result1 = mem.reason(
        seeds=cascade_seeds,
        max_depth=3,
        max_total_states=50,
    )
    exp1 = result1.expansion
    print(f"    States explored: {exp1.states_created}")
    print(f"    Rules applied:   {exp1.rules_applied}")
    print(f"    New edges:       {exp1.edges_produced}")

    print("\n  Phase 2: Indirect supply chain reasoning (supplies_to)...")
    result2 = mem.reason(
        seeds=cascade_seeds,
        max_depth=3,
        max_total_states=50,
    )
    exp2 = result2.expansion
    print(f"    States explored: {exp2.states_created}")
    print(f"    Rules applied:   {exp2.rules_applied}")
    print(f"    New edges:       {exp2.edges_produced}")

    cascades = mem.pattern_match(edge_label="cascade_affected_by")
    indirect = mem.pattern_match(edge_label="indirectly_supplies")
    print(f"\n  Cascade edges discovered: {len(cascades)}")
    print(f"  Indirect supply edges:    {len(indirect)}")

    risk_impacts: dict[str, list[str]] = {}
    for edge_info in cascades:
        src_labels = edge_info.source_labels
        tgt_labels = edge_info.target_labels
        if src_labels and tgt_labels and src_labels[0].startswith("risk_"):
            risk_impacts.setdefault(src_labels[0], []).append(tgt_labels[0])

    print(f"\n  Risk cascade impact summary:")
    for risk_label in sorted(risk_impacts):
        targets = risk_impacts[risk_label]
        products_hit = [t for t in targets if t.startswith("prod_")]
        print(f"    {risk_label}:")
        print(f"      Reaches {len(targets)} nodes ({len(products_hit)} products)")
        for p in sorted(products_hit)[:5]:
            print(f"        -> {p}")
        if len(products_hit) > 5:
            print(f"        ... and {len(products_hit) - 5} more")
    print()

    # =====================================================================
    # SECTION 5: Risk Cascade Path Tracing
    # =====================================================================
    print("=" * 70)
    print("SECTION 5: Risk Cascade Path Tracing")
    print("=" * 70)

    high_impact_risks = sorted(risks.items(), key=lambda x: -(x[1].get("probability", 0) * x[1].get("impact", 0)))
    print("\n  Top risk-to-product disruption paths:")
    for risk_name, risk_data in high_impact_risks[:4]:
        print(f"\n  {risk_name} (p={risk_data['probability']:.2f}, impact={risk_data['impact']:.2f}):")
        paths = mem.find_paths(risk_name, "prod_vehicle", max_depth=8, max_paths=3)
        if paths:
            for i, path in enumerate(paths[:2]):
                lead_total = 0
                for step in path:
                    n = mem.engine.graph.get_node_by_label(step)
                    if n and n.data and "lead_time_days" in n.data:
                        lead_total += n.data["lead_time_days"]
                print(f"    Path {i+1} ({len(path)} hops, lead_time_sum={lead_total}d):")
                print(f"      {' -> '.join(path)}")
        else:
            print(f"    No direct path to final vehicle")

    components = mem.connected_components()
    print(f"\n  Connected components: {len(components)}")
    for i, comp in enumerate(sorted(components, key=len, reverse=True)[:3]):
        cats: dict[str, int] = {}
        for lbl in comp:
            n = mem.engine.graph.get_node_by_label(lbl)
            if n and n.data:
                c = n.data.get("category", "unknown")
                cats[c] = cats.get(c, 0) + 1
        print(f"    Component {i+1}: {len(comp)} nodes - {cats}")
    print()

    # =====================================================================
    # SECTION 6: Lead Time Analysis
    # =====================================================================
    print("=" * 70)
    print("SECTION 6: Lead Time Analysis")
    print("=" * 70)

    tier3_suppliers = [name for name, data in suppliers.items() if data.get("tier") == 3]
    print(f"\n  Tier 3 raw material suppliers (longest lead times):")
    for name in sorted(tier3_suppliers, key=lambda n: -suppliers[n]["lead_time_days"]):
        data = suppliers[name]
        print(f"    {name:35s} lead={data['lead_time_days']:3d}d  "
              f"reliability={data['reliability_score']:.2f}  "
              f"country={data['country']}")

    print(f"\n  Supply chain cumulative lead time by tier:")
    tier_totals: dict[int, list[int]] = {}
    for name, data in suppliers.items():
        tier = data.get("tier", 0)
        tier_totals.setdefault(tier, []).append(data["lead_time_days"])
    for tier in sorted(tier_totals):
        vals = tier_totals[tier]
        avg = sum(vals) / len(vals)
        print(f"    Tier {tier}: avg={avg:.0f}d  max={max(vals)}d  "
              f"min={min(vals)}d  count={len(vals)}")

    worst_chain_lead = 0
    worst_chain_path: list[str] = []
    for t3_name in tier3_suppliers:
        t3_node = mem.engine.graph.get_node_by_label(t3_name)
        if not t3_node:
            continue
        t3_lt = suppliers[t3_name]["lead_time_days"]
        for e1 in mem.engine.graph.incident_edges(t3_node.id):
            if e1.label != "supplies_to":
                continue
            for t2_id in e1.target_ids:
                t2_node = mem.engine.graph.get_node(t2_id)
                if not t2_node or t2_node.data.get("tier") != 2:
                    continue
                t2_lt = t2_node.data.get("lead_time_days", 0)
                for e2 in mem.engine.graph.incident_edges(t2_id):
                    if e2.label != "supplies_to":
                        continue
                    for t1_id in e2.target_ids:
                        t1_node = mem.engine.graph.get_node(t1_id)
                        if not t1_node or t1_node.data.get("tier") != 1:
                            continue
                        t1_lt = t1_node.data.get("lead_time_days", 0)
                        total = t3_lt + t2_lt + t1_lt
                        if total > worst_chain_lead:
                            worst_chain_lead = total
                            worst_chain_path = [t3_name, t2_node.label, t1_node.label]

    if worst_chain_path:
        print(f"\n  Worst-case supply chain lead time: {worst_chain_lead}d")
        print(f"    Path: {' -> '.join(worst_chain_path)}")
        for step in worst_chain_path:
            n = mem.engine.graph.get_node_by_label(step)
            if n and n.data:
                print(f"      {step}: {n.data.get('lead_time_days', '?')}d  "
                      f"[{n.data.get('material', '?')}]")

    print(f"\n  Supplier reliability risk ranking:")
    supplier_risk = []
    for name, data in suppliers.items():
        risk_factor = (1.0 - data["reliability_score"]) * data["lead_time_days"]
        if data.get("single_source"):
            risk_factor *= 1.5
        supplier_risk.append((name, risk_factor, data))
    supplier_risk.sort(key=lambda x: -x[1])
    for name, rf, data in supplier_risk[:8]:
        flag = " [SINGLE-SOURCE]" if data.get("single_source") else ""
        print(f"    {name:35s} risk_score={rf:.1f}  "
              f"reliability={data['reliability_score']:.2f}  "
              f"lead={data['lead_time_days']}d{flag}")
    print()

    # =====================================================================
    # SECTION 7: Backup Coverage & Diversification Recommendations
    # =====================================================================
    print("=" * 70)
    print("SECTION 7: Backup Coverage & Diversification Recommendations")
    print("=" * 70)

    dc_no_backup = [name for name, data in dist_centers.items() if not data.get("backup")]
    print(f"\n  Distribution centers without backup ({len(dc_no_backup)}):")
    for name in dc_no_backup:
        node = mem.engine.graph.get_node_by_label(name)
        d = node.data if node and node.data else {}
        print(f"    {name:25s} region={d.get('region', '?')} capacity={d.get('capacity', '?')}")

    backup_srcs = {src for src, _ in backup_for}
    suppliers_without_backup_entry = [
        name for name in suppliers if name not in backup_srcs
    ]
    print(f"\n  Suppliers not listed as backup providers ({len(suppliers_without_backup_entry)}):")
    critical_no_backup = []
    for name in suppliers_without_backup_entry:
        node = mem.engine.graph.get_node_by_label(name)
        d = node.data if node and node.data else {}
        if d.get("single_source") or d.get("reliability_score", 1.0) < 0.80:
            critical_no_backup.append((name, d))
    for name, d in sorted(critical_no_backup, key=lambda x: x[1].get("reliability_score", 1.0)):
        print(f"    {name:35s} reliability={d.get('reliability_score', 0):.2f}  "
              f"country={d.get('country', '?')}")

    print(f"\n  Diversification priorities (top 5):")
    priorities = []
    for name, data in suppliers.items():
        if not data.get("single_source"):
            continue
        risk_count = 0
        for edge_info in mem.pattern_match(edge_label="affected_by", target_label=name):
            src_labels = edge_info.source_labels
            if src_labels and src_labels[0].startswith("risk_"):
                risk_node = mem.engine.graph.get_node_by_label(src_labels[0])
                if risk_node and risk_node.data:
                    risk_count += risk_node.data.get("impact", 0)
        has_backup = name in backup_srcs
        priority_score = (1.0 - data["reliability_score"]) * data["lead_time_days"] * (risk_count + 1)
        if not has_backup:
            priority_score *= 2.0
        priorities.append((name, priority_score, data, risk_count, has_backup))

    priorities.sort(key=lambda x: -x[1])
    for i, (name, ps, data, rc, hb) in enumerate(priorities[:5]):
        print(f"    {i+1}. {name}")
        print(f"       country={data['country']}  material={data['material']}  "
              f"reliability={data['reliability_score']:.2f}")
        print(f"       lead_time={data['lead_time_days']}d  risk_exposure={rc:.2f}  "
              f"has_backup={'yes' if hb else 'NO'}")
    print()

    # =====================================================================
    # SUMMARY
    # =====================================================================
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    stats = mem.stats()
    print(f"  Network: {stats.nodes} nodes, {stats.edges} edges")
    print(f"  Connected components: {stats.components}")
    print()
    print("  Key findings:")
    print(f"    - {len(single_source_suppliers)} single-source suppliers identified")
    print(f"    - {len(critical_low_alternate)} critical products with <=1 alternate source")
    print(f"    - {len(cascades)} risk cascade paths discovered via reasoning")
    print(f"    - {len(dc_no_backup)} distribution centers lack backup coverage")
    if worst_chain_path:
        print(f"    - Worst-case supply chain lead time: {worst_chain_lead} days")
    print()
    print("  Recommended actions:")
    print("    1. Diversify semiconductor sourcing beyond Germany/Taiwan")
    print("    2. Establish backup for sensor supply (Japan single source)")
    print("    3. Reduce dependence on China for rare earth materials")
    print("    4. Add backup distribution in Seattle and Dallas regions")
    print("    5. Build strategic inventory buffer for DRC-sourced cobalt")
    print()


if __name__ == "__main__":
    main()
