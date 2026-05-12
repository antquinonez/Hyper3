"""
Explore a Research Topic with ConceptSet
=========================================

Build a climate science knowledge graph and use ConceptSet's chainable
exploration to discover relationships, find influential concepts, trace
causal chains, and identify research gaps -- all through fluent pipelines
that compose selectors, explorers, and analysis methods.

Run with:
    .venv/bin/python examples/showcase/domain/topic_exploration/topic_exploration.py
"""

from __future__ import annotations

from hyper3 import HypergraphMemory, TransitiveRule


def main():
    mem = HypergraphMemory(evolve_interval=0)

    # =====================================================================
    # SECTION 1: Build the Knowledge Graph
    # =====================================================================

    print("=" * 70)
    print("SECTION 1: Building Climate Science Knowledge Graph")
    print("=" * 70)

    phenomena = {}
    for i, (name, cat, impact) in enumerate([
        ("greenhouse_effect", "radiative", "high"),
        ("global_warming", "temperature", "critical"),
        ("sea_level_rise", "oceanic", "critical"),
        ("ocean_acidification", "oceanic", "high"),
        ("glacier_retreat", "cryospheric", "high"),
        ("permafrost_thaw", "cryospheric", "high"),
        ("ice_albedo_feedback", "feedback", "high"),
        ("water_vapor_feedback", "feedback", "high"),
        ("carbon_cycle_feedback", "feedback", "critical"),
        ("arctic_amplification", "regional", "high"),
        ("el_nino", "oscillation", "moderate"),
        ("la_nina", "oscillation", "moderate"),
        ("atlantic_meridional_overturning", "oceanic", "critical"),
        ("stratospheric_ozone_depletion", "atmospheric", "high"),
        ("tropospheric_ozone", "atmospheric", "moderate"),
        ("extreme_precipitation", "extreme_event", "high"),
        ("heat_waves", "extreme_event", "high"),
        ("drought_intensity", "extreme_event", "high"),
        ("wildfire_frequency", "extreme_event", "high"),
        ("hurricane_intensity", "extreme_event", "high"),
    ], start=1):
        phenomena[name] = {
            "domain": "phenomenon",
            "category": cat,
            "impact_level": impact,
            "certainty": round(0.7 + (i % 5) * 0.06, 2),
        }

    drivers = {}
    for i, (name, sector) in enumerate([
        ("co2_emissions", "energy"),
        ("methane_emissions", "agriculture"),
        ("nitrous_oxide", "agriculture"),
        ("deforestation", "land_use"),
        ("fossil_fuel_combustion", "energy"),
        ("industrial_processes", "industry"),
        ("cement_production", "industry"),
        ("landfill_methane", "waste"),
        ("agricultural_tillage", "agriculture"),
        ("aviation_emissions", "transport"),
        ("shipping_emissions", "transport"),
        ("transport_emissions", "transport"),
        ("electricity_generation", "energy"),
        ("residential_heating", "buildings"),
        ("fluorinated_gases", "industry"),
    ], start=1):
        drivers[name] = {
            "domain": "driver",
            "sector": sector,
            "mitigation_cost": round(10 + (i % 8) * 15),
            "abatement_potential": round(0.3 + (i % 6) * 0.1, 1),
        }

    impacts = {}
    for i, (name, system) in enumerate([
        ("coral_bleaching", "marine"),
        ("biodiversity_loss", "ecosystem"),
        ("crop_yield_decline", "agriculture"),
        ("water_scarcity", "hydrological"),
        ("coastal_flooding", "infrastructure"),
        ("species_migration", "ecosystem"),
        ("desertification", "land"),
        ("fisheries_decline", "marine"),
        ("vector_borne_disease", "health"),
        ("heat_related_mortality", "health"),
        ("infrastructure_damage", "infrastructure"),
        ("food_insecurity", "agriculture"),
        ("freshwater_contamination", "hydrological"),
        ("habitat_fragmentation", "ecosystem"),
        ("economic_displacement", "societal"),
    ], start=1):
        impacts[name] = {
            "domain": "impact",
            "affected_system": system,
            "irreversibility": round(0.3 + (i % 7) * 0.1, 1),
            "adaptation_capacity": round(0.2 + (i % 5) * 0.15, 1),
        }

    solutions = {}
    for i, (name, sol_type) in enumerate([
        ("renewable_energy", "mitigation"),
        ("carbon_capture", "mitigation"),
        ("reforestation", "mitigation"),
        ("nuclear_energy", "mitigation"),
        ("energy_efficiency", "mitigation"),
        ("electric_vehicles", "mitigation"),
        ("green_hydrogen", "mitigation"),
        ("carbon_pricing", "policy"),
        ("emissions_trading", "policy"),
        ("climate_adaptation", "adaptation"),
        ("sea_wall_construction", "adaptation"),
        ("drought_resistant_crops", "adaptation"),
        ("early_warning_systems", "adaptation"),
        ("ecosystem_restoration", "nature_based"),
        ("wetland_conservation", "nature_based"),
    ], start=1):
        solutions[name] = {
            "domain": "solution",
            "type": sol_type,
            "readiness_level": min(9, 3 + (i % 5)),
            "cobenefits": round(0.4 + (i % 6) * 0.1, 1),
        }

    measurements = {}
    for i, (name, method) in enumerate([
        ("ice_core_data", "paleoclimate"),
        ("satellite_temperature", "remote_sensing"),
        ("tide_gauge_network", "oceanographic"),
        ("atmospheric_co2_monitoring", "atmospheric"),
        ("tree_ring_analysis", "dendrochronology"),
        ("ocean_buoy_array", "oceanographic"),
        ("glacier_mass_balance", "glaciology"),
        ("permafrost_temperature", "geothermal"),
        ("weather_station_network", "meteorological"),
        ("climate_model_output", "simulation"),
        ("ensemble_projections", "simulation"),
        ("radiative_forcing_estimates", "radiative"),
    ], start=1):
        measurements[name] = {
            "domain": "measurement",
            "method": method,
            "temporal_resolution": ["annual", "monthly", "daily", "decadal"][i % 4],
            "uncertainty": round(0.05 + (i % 5) * 0.04, 2),
        }

    concepts = {}
    for group in [phenomena, drivers, impacts, solutions, measurements]:
        concepts.update(group)

    for label, data in concepts.items():
        mem.add(label, data=data)

    print(f"  Stored {len(concepts)} concepts across 5 domains")
    print()

    # =====================================================================
    # SECTION 2: Create Knowledge Edges
    # =====================================================================

    print("=" * 70)
    print("SECTION 2: Creating Knowledge Relationships")
    print("=" * 70)

    edges = []

    edges += [
        ("co2_emissions", "greenhouse_effect", "causes"),
        ("methane_emissions", "greenhouse_effect", "causes"),
        ("nitrous_oxide", "greenhouse_effect", "causes"),
        ("fluorinated_gases", "greenhouse_effect", "causes"),
        ("greenhouse_effect", "global_warming", "causes"),
        ("global_warming", "sea_level_rise", "causes"),
        ("global_warming", "ocean_acidification", "causes"),
        ("global_warming", "glacier_retreat", "causes"),
        ("global_warming", "permafrost_thaw", "causes"),
        ("global_warming", "extreme_precipitation", "causes"),
        ("global_warming", "heat_waves", "causes"),
        ("global_warming", "drought_intensity", "causes"),
        ("global_warming", "wildfire_frequency", "causes"),
        ("global_warming", "hurricane_intensity", "causes"),
        ("global_warming", "arctic_amplification", "causes"),
        ("fossil_fuel_combustion", "co2_emissions", "contributes_to"),
        ("cement_production", "co2_emissions", "contributes_to"),
        ("deforestation", "co2_emissions", "contributes_to"),
        ("electricity_generation", "fossil_fuel_combustion", "enables"),
        ("transport_emissions", "fossil_fuel_combustion", "contributes_to"),
        ("aviation_emissions", "fossil_fuel_combustion", "contributes_to"),
        ("shipping_emissions", "fossil_fuel_combustion", "contributes_to"),
        ("residential_heating", "fossil_fuel_combustion", "contributes_to"),
        ("agricultural_tillage", "nitrous_oxide", "contributes_to"),
        ("landfill_methane", "methane_emissions", "contributes_to"),
        ("industrial_processes", "fluorinated_gases", "contributes_to"),
        ("industrial_processes", "co2_emissions", "contributes_to"),
    ]

    edges += [
        ("glacier_retreat", "sea_level_rise", "contributes_to"),
        ("permafrost_thaw", "methane_emissions", "triggers"),
        ("ice_albedo_feedback", "arctic_amplification", "drives"),
        ("arctic_amplification", "permafrost_thaw", "accelerates"),
        ("water_vapor_feedback", "greenhouse_effect", "amplifies"),
        ("carbon_cycle_feedback", "global_warming", "amplifies"),
        ("global_warming", "water_vapor_feedback", "triggers"),
        ("global_warming", "ice_albedo_feedback", "triggers"),
        ("global_warming", "carbon_cycle_feedback", "triggers"),
        ("el_nino", "extreme_precipitation", "modulates"),
        ("la_nina", "drought_intensity", "modulates"),
        ("atlantic_meridional_overturning", "sea_level_rise", "modulates"),
        ("global_warming", "atlantic_meridional_overturning", "weakens"),
        ("stratospheric_ozone_depletion", "arctic_amplification", "contributes_to"),
        ("tropospheric_ozone", "greenhouse_effect", "contributes_to"),
    ]

    edges += [
        ("sea_level_rise", "coastal_flooding", "causes"),
        ("sea_level_rise", "freshwater_contamination", "causes"),
        ("ocean_acidification", "coral_bleaching", "causes"),
        ("ocean_acidification", "fisheries_decline", "causes"),
        ("global_warming", "biodiversity_loss", "causes"),
        ("global_warming", "species_migration", "causes"),
        ("global_warming", "vector_borne_disease", "causes"),
        ("global_warming", "heat_related_mortality", "causes"),
        ("heat_waves", "heat_related_mortality", "causes"),
        ("drought_intensity", "crop_yield_decline", "causes"),
        ("drought_intensity", "water_scarcity", "causes"),
        ("drought_intensity", "desertification", "causes"),
        ("drought_intensity", "wildfire_frequency", "exacerbates"),
        ("extreme_precipitation", "coastal_flooding", "causes"),
        ("wildfire_frequency", "biodiversity_loss", "causes"),
        ("wildfire_frequency", "habitat_fragmentation", "causes"),
        ("wildfire_frequency", "co2_emissions", "contributes_to"),
        ("hurricane_intensity", "coastal_flooding", "causes"),
        ("hurricane_intensity", "infrastructure_damage", "causes"),
        ("glacier_retreat", "water_scarcity", "causes"),
        ("crop_yield_decline", "food_insecurity", "causes"),
        ("food_insecurity", "economic_displacement", "causes"),
        ("infrastructure_damage", "economic_displacement", "causes"),
        ("desertification", "habitat_fragmentation", "causes"),
        ("coral_bleaching", "biodiversity_loss", "contributes_to"),
        ("species_migration", "biodiversity_loss", "contributes_to"),
    ]

    edges += [
        ("renewable_energy", "fossil_fuel_combustion", "displaces"),
        ("nuclear_energy", "fossil_fuel_combustion", "displaces"),
        ("carbon_capture", "co2_emissions", "reduces"),
        ("reforestation", "co2_emissions", "absorbs"),
        ("energy_efficiency", "electricity_generation", "reduces"),
        ("electric_vehicles", "transport_emissions", "reduces"),
        ("green_hydrogen", "industrial_processes", "displaces"),
        ("carbon_pricing", "co2_emissions", "reduces"),
        ("emissions_trading", "co2_emissions", "reduces"),
        ("climate_adaptation", "sea_level_rise", "addresses"),
        ("sea_wall_construction", "coastal_flooding", "mitigates"),
        ("drought_resistant_crops", "crop_yield_decline", "mitigates"),
        ("early_warning_systems", "heat_related_mortality", "mitigates"),
        ("ecosystem_restoration", "biodiversity_loss", "reverses"),
        ("wetland_conservation", "coastal_flooding", "mitigates"),
        ("renewable_energy", "electricity_generation", "replaces"),
        ("reforestation", "deforestation", "counteracts"),
        ("ecosystem_restoration", "desertification", "counteracts"),
        ("wetland_conservation", "habitat_fragmentation", "counteracts"),
    ]

    edges += [
        ("ice_core_data", "greenhouse_effect", "evidence_for"),
        ("ice_core_data", "global_warming", "evidence_for"),
        ("satellite_temperature", "global_warming", "evidence_for"),
        ("satellite_temperature", "arctic_amplification", "evidence_for"),
        ("tide_gauge_network", "sea_level_rise", "evidence_for"),
        ("atmospheric_co2_monitoring", "co2_emissions", "measures"),
        ("atmospheric_co2_monitoring", "greenhouse_effect", "evidence_for"),
        ("tree_ring_analysis", "drought_intensity", "evidence_for"),
        ("tree_ring_analysis", "global_warming", "evidence_for"),
        ("ocean_buoy_array", "ocean_acidification", "evidence_for"),
        ("ocean_buoy_array", "atlantic_meridional_overturning", "monitors"),
        ("glacier_mass_balance", "glacier_retreat", "evidence_for"),
        ("permafrost_temperature", "permafrost_thaw", "evidence_for"),
        ("weather_station_network", "heat_waves", "evidence_for"),
        ("weather_station_network", "extreme_precipitation", "evidence_for"),
        ("climate_model_output", "global_warming", "projects"),
        ("climate_model_output", "sea_level_rise", "projects"),
        ("climate_model_output", "extreme_precipitation", "projects"),
        ("ensemble_projections", "global_warming", "projects"),
        ("ensemble_projections", "global_warming", "projects"),
        ("radiative_forcing_estimates", "greenhouse_effect", "quantifies"),
        ("radiative_forcing_estimates", "co2_emissions", "quantifies"),
    ]

    edges += [
        ("renewable_energy", "greenhouse_effect", "addresses"),
        ("renewable_energy", "energy_efficiency", "complements"),
        ("electric_vehicles", "energy_efficiency", "complements"),
        ("carbon_capture", "renewable_energy", "complements"),
        ("reforestation", "ecosystem_restoration", "complements"),
        ("carbon_pricing", "emissions_trading", "complements"),
        ("nuclear_energy", "renewable_energy", "complements"),
        ("green_hydrogen", "renewable_energy", "requires"),
    ]

    seen = set()
    unique_edges = []
    for src, tgt, label in edges:
        key = (src, tgt, label)
        if key not in seen:
            seen.add(key)
            unique_edges.append((src, tgt, label))

    for src, tgt, label in unique_edges:
        mem.link(src, tgt, label=label)

    print(f"  {mem.size[0]} nodes, {mem.size[1]} edges")
    print()

    # =====================================================================
    # SECTION 3: Seed and Explore with ConceptSet
    # =====================================================================

    print("=" * 70)
    print("SECTION 3: Seeded Exploration with ConceptSet")
    print("=" * 70)

    seed = mem.find("global_warming")
    print(f"  Seed: {seed.labels}")

    immediate = seed.neighbors(direction="out")
    print(f"  Direct consequences ({len(immediate)}):")
    for label in immediate.labels[:10]:
        info = mem.info(label)
        cat = info.data.get("category", "?") if info else "?"
        print(f"    {label} [{cat}]")
    if len(immediate) > 10:
        print(f"    ... and {len(immediate) - 10} more")
    print()

    second_order = immediate.neighbors(direction="out").exclude("global_warming").unique()
    print(f"  Second-order consequences ({len(second_order)}):")
    for label in second_order.top(10).labels:
        info = mem.info(label)
        cat = info.data.get("category", "?") if info else "?"
        print(f"    {label} [{cat}]")
    print()

    # =====================================================================
    # SECTION 4: Causal Chain Discovery
    # =====================================================================

    print("=" * 70)
    print("SECTION 4: Causal Chain Discovery")
    print("=" * 70)

    causes = mem.find("co2_emissions")
    chain = (causes
             .paths_to("coastal_flooding", label="causes", max_depth=6, max_paths=5))
    print(f"  Causal paths from co2_emissions to coastal_flooding:")
    path_concepts = chain.unique().labels
    print(f"    Concepts in causal chain: {path_concepts}")
    print()

    methane_paths = (mem.find("methane_emissions")
                     .paths_to("global_warming", max_depth=4, max_paths=3))
    print(f"  Paths from methane_emissions to global_warming:")
    print(f"    Chain concepts: {methane_paths.unique().labels}")
    print()

    feedback = (mem.find("permafrost_thaw")
                .paths_to("global_warming", max_depth=6, max_paths=5))
    print(f"  Feedback loop via permafrost_thaw -> global_warming:")
    print(f"    Chain concepts: {feedback.unique().labels}")
    print()

    # =====================================================================
    # SECTION 5: Multi-Hop Impact Analysis
    # =====================================================================

    print("=" * 70)
    print("SECTION 5: Multi-Hop Impact Analysis")
    print("=" * 70)

    co2_neighbors = (mem.find("co2_emissions")
                     .neighbors(edge_label="causes", direction="out")
                     .neighbors(edge_label="causes", direction="out")
                     .unique())

    print(f"  Two-hop impacts of CO2 emissions via 'causes' edges ({len(co2_neighbors)}):")
    for label in co2_neighbors.top(10).labels:
        info = mem.info(label)
        impact = info.data.get("impact_level", "?") if info else "?"
        print(f"    {label} (impact: {impact})")
    print()

    all_catastrophic = (mem.find(data={"impact_level": "critical"})
                        .neighbors(direction="out")
                        .unique())
    print(f"  Concepts downstream of critical-impact phenomena ({len(all_catastrophic)}):")
    for label in all_catastrophic.top(8).labels:
        info = mem.info(label)
        cat = info.data.get("category", info.data.get("affected_system", "?")) if info else "?"
        print(f"    {label} [{cat}]")
    print()

    # =====================================================================
    # SECTION 6: Centrality-Guided Prioritization
    # =====================================================================

    print("=" * 70)
    print("SECTION 6: Centrality-Guided Prioritization")
    print("=" * 70)

    all_phenomena = mem.find(data={"domain": "phenomenon"})
    phenomena_centrality = all_phenomena.neighbors().unique().centrality("degree")

    print("  Phenomena neighbors ranked by degree centrality:")
    for label, score in phenomena_centrality.top(10).items:
        info = mem.info(label)
        domain = info.data.get("domain", "?") if info else "?"
        print(f"    {label:<40s} centrality={score:.3f}  [{domain}]")
    print()

    impact_set = mem.find(data={"domain": "impact"})
    impact_centrality = impact_set.neighbors().unique().centrality("pagerank")

    print("  Impact-related concepts ranked by PageRank:")
    for label, score in impact_centrality.top(10).items:
        info = mem.info(label)
        domain = info.data.get("domain", "?") if info else "?"
        print(f"    {label:<40s} pagerank={score:.4f}  [{domain}]")
    print()

    # =====================================================================
    # SECTION 7: Solution Coverage Analysis
    # =====================================================================

    print("=" * 70)
    print("SECTION 7: Solution Coverage and Gap Analysis")
    print("=" * 70)

    mitigation_solutions = mem.find(data={"type": "mitigation"})
    print(f"  Mitigation solutions: {mitigation_solutions.labels}")

    addressed = (mitigation_solutions
                 .neighbors(edge_label="reduces", direction="out")
                 .unique())
    print(f"  Directly reduced/absorbed drivers ({len(addressed)}):")
    for label in addressed.labels:
        info = mem.info(label)
        sector = info.data.get("sector", "?") if info else "?"
        print(f"    {label} [sector: {sector}]")
    print()

    adaptation_solutions = mem.find(data={"type": "adaptation"})
    adapted_impacts = (adaptation_solutions
                       .neighbors(edge_label="mitigates", direction="out")
                       .unique())
    all_impacts = mem.find(data={"domain": "impact"})

    all_impact_labels = set(all_impacts.labels)
    adapted_labels = set(adapted_impacts.labels)
    unaddressed = all_impact_labels - adapted_labels

    print(f"  Impacts addressed by adaptation ({len(adapted_labels)}):")
    for label in sorted(adapted_labels):
        info = mem.info(label)
        system = info.data.get("affected_system", "?") if info else "?"
        print(f"    {label} [{system}]")

    print(f"  Impacts with NO direct adaptation ({len(unaddressed)}):")
    for label in sorted(unaddressed):
        info = mem.info(label)
        system = info.data.get("affected_system", "?") if info else "?"
        irreversibility = info.data.get("irreversibility", "?") if info else "?"
        print(f"    {label} [{system}] irreversibility={irreversibility}")
    print()

    # =====================================================================
    # SECTION 8: Feedback Loop Detection
    # =====================================================================

    print("=" * 70)
    print("SECTION 8: Feedback Loop Mapping")
    print("=" * 70)

    feedback_concepts = mem.find(data={"category": "feedback"})
    print(f"  Feedback mechanisms: {feedback_concepts.labels}")

    for concept in feedback_concepts.labels:
        loop = (mem.find(concept)
                .neighbors(direction="out")
                .neighbors(direction="out")
                .unique())
        loop_back = loop.filter(lambda l, _: l == concept)
        is_cyclic = len(loop_back) > 0

        downstream = [l for l in loop.labels if l != concept][:8]
        print(f"  {concept}:")
        print(f"    2-hop downstream: {downstream}")
        print(f"    Self-reinforcing loop: {'yes' if is_cyclic else 'no'}")
    print()

    # =====================================================================
    # SECTION 9: Transitive Causal Inference
    # =====================================================================

    print("=" * 70)
    print("SECTION 9: Transitive Causal Inference")
    print("=" * 70)

    mem.add_rules(TransitiveRule(edge_label="causes", new_label="indirectly_causes"))
    result = mem.reason(
        seeds={"co2_emissions", "methane_emissions", "deforestation",
               "global_warming", "permafrost_thaw"},
        depth=4,
        max_states=80,
    )

    indirect_count = sum(1 for e in mem.engine.graph.edges if e.label == "indirectly_causes")
    print(f"  TransitiveRule discovered {indirect_count} indirect causal links")
    expansion = result.expansion
    if expansion:
        print(f"  States explored: {expansion.states_created}")
        print(f"  Rules applied: {expansion.rules_applied}")
        print(f"  Max depth: {expansion.max_depth}")

    indirect_edges = mem.pattern_match(edge_label="indirectly_causes")
    if indirect_edges:
        print("  Sample indirect causal chains:")
        for e in indirect_edges[:8]:
            s = e.source_labels[0] if e.source_labels else "?"
            t = e.target_labels[0] if e.target_labels else "?"
            print(f"    {s} --[indirectly_causes]--> {t}")
    print()

    # =====================================================================
    # SECTION 10: Cross-Domain ConceptSet Pipeline
    # =====================================================================

    print("=" * 70)
    print("SECTION 10: Cross-Domain Exploration Pipeline")
    print("=" * 70)

    pipeline = (mem.find("fossil_fuel_combustion")
                .neighbors(direction="out")
                .unique()
                .neighbors(direction="out")
                .unique()
                .neighbors(direction="out")
                .unique()
                .exclude("fossil_fuel_combustion"))

    print(f"  Multi-hop causal spread from fossil_fuel_combustion ({len(pipeline)}):")
    domain_counts: dict[str, int] = {}
    for label in pipeline.labels:
        info = mem.info(label)
        domain = info.data.get("domain", "unknown") if info else "unknown"
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
    for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
        print(f"    {domain}: {count} concepts")
    print()

    solution_pipeline = (pipeline
                         .filter(lambda l, _: True)
                         .neighbors(edge_label="mitigates", direction="in")
                         .unique())
    print(f"  Solutions that mitigate downstream impacts ({len(solution_pipeline)}):")
    for label in solution_pipeline.labels:
        info = mem.info(label)
        sol_type = info.data.get("type", "?") if info else "?"
        readiness = info.data.get("readiness_level", "?") if info else "?"
        print(f"    {label} [type: {sol_type}, readiness: {readiness}/9]")
    print()

    # =====================================================================
    # SECTION 11: Measurement Evidence Mapping
    # =====================================================================

    print("=" * 70)
    print("SECTION 11: Evidence Mapping")
    print("=" * 70)

    measurements_set = mem.find(data={"domain": "measurement"})
    evidence_targets = (measurements_set
                        .neighbors(edge_label="evidence_for", direction="out")
                        .unique())

    print(f"  Phenomena with direct measurement evidence ({len(evidence_targets)}):")
    for label in evidence_targets.labels:
        info = mem.info(label)
        cat = info.data.get("category", "?") if info else "?"
        evidence_count = len(mem.neighbors(label, edge_label="evidence_for", direction="in"))
        print(f"    {label:<40s} [{cat}] {evidence_count} evidence sources")
    print()

    all_phenomena_labels = set(mem.find(data={"domain": "phenomenon"}).labels)
    evidenced_labels = set(evidence_targets.labels)
    unevidenced = all_phenomena_labels - evidenced_labels

    print(f"  Phenomena WITHOUT direct measurement evidence ({len(unevidenced)}):")
    for label in sorted(unevidenced):
        info = mem.info(label)
        cat = info.data.get("category", "?") if info else "?"
        certainty = info.data.get("certainty", "?") if info else "?"
        print(f"    {label:<40s} [{cat}] certainty={certainty}")
    print()

    # =====================================================================
    # SUMMARY
    # =====================================================================

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    stats = mem.stats()
    print(f"  Graph: {stats.nodes} nodes, {stats.edges} edges")
    print(f"  Connected components: {stats.components}")
    print(f"  Domains: phenomenon, driver, impact, solution, measurement")
    print(f"  Direct causal edges: {len([e for e in mem.analyze.edges() if e['label'] == 'causes'])}")
    print(f"  Indirect causal links inferred: {indirect_count}")
    print(f"  Feedback mechanisms: {len(feedback_concepts.labels)}")
    print(f"  Unaddressed impacts: {len(unaddressed)}")
    print(f"  Unevidenced phenomena: {len(unevidenced)}")
    print()

    top_concept = phenomena_centrality.top(1)
    if top_concept.labels:
        tc = top_concept.labels[0]
        tc_score = top_concept.scores[tc]
        print(f"  Most central concept in phenomena network: {tc} (centrality={tc_score:.3f})")
        downstream_count = len(mem.find(tc).neighbors(direction="out").unique())
        print(f"  Its direct downstream influence: {downstream_count} concepts")
    print()


if __name__ == "__main__":
    main()
