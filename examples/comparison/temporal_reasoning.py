"""
Incident Timeline Analysis for IT Operations (Plain Python)
============================================================

Reimplements examples/showcase/temporal_reasoning/temporal_reasoning.py using only
standard Python classes and networkx. No Hyper3 imports.

Run with:
    .venv/bin/python examples/comparison/04_temporal_reasoning.py
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field


class AllenRelation(Enum):
    BEFORE = "before"
    AFTER = "after"
    MEETS = "meets"
    MET_BY = "met_by"
    OVERLAPS = "overlaps"
    OVERLAPPED_BY = "overlapped_by"
    DURING = "during"
    CONTAINS = "contains"
    STARTS = "starts"
    STARTED_BY = "started_by"
    FINISHES = "finishes"
    FINISHED_BY = "finished_by"
    EQUALS = "equals"


@dataclass
class TimeInterval:
    start: float
    end: float

    def relate_to(self, other: TimeInterval) -> AllenRelation:
        if self.start == other.start and self.end == other.end:
            return AllenRelation.EQUALS
        if self.end <= other.start:
            if self.end == other.start:
                return AllenRelation.MEETS
            return AllenRelation.BEFORE
        if self.start >= other.end:
            if self.start == other.end:
                return AllenRelation.MET_BY
            return AllenRelation.AFTER
        if self.start < other.start:
            if self.end < other.end:
                return AllenRelation.OVERLAPS
            if self.end == other.end:
                return AllenRelation.FINISHED_BY
            if self.start == other.start:
                return AllenRelation.STARTED_BY
            return AllenRelation.CONTAINS
        if self.start > other.start:
            if self.end < other.end:
                return AllenRelation.DURING
            if self.end == other.end:
                return AllenRelation.FINISHES
            if self.start == other.start:
                return AllenRelation.STARTS
            return AllenRelation.OVERLAPPED_BY
        if self.start == other.start:
            if self.end < other.end:
                return AllenRelation.STARTS
            if self.end > other.end:
                return AllenRelation.STARTED_BY
        return AllenRelation.EQUALS


@dataclass
class TemporalEvent:
    event_id: str
    label: str
    interval: TimeInterval
    metadata: dict = field(default_factory=dict)


BASE = 1700000000.0
H = 3600.0

EVENTS = [
    ("recon_port_scan", 0, 2, "reconnaissance", "External port scan against perimeter"),
    ("recon_vuln_scan", 3, 5, "reconnaissance", "Web application vulnerability scanning"),
    ("recon_osint", 6, 10, "reconnaissance", "OSINT research on target employees"),
    ("recon_dns_enum", 8, 9, "reconnaissance", "DNS enumeration and subdomain discovery"),

    ("access_phish_send", 24, 24.5, "initial_access", "Phishing emails sent to finance team"),
    ("access_phish_click", 25, 25.1, "initial_access", "Employee clicks phishing link"),
    ("access_harvest_cred", 25.1, 26, "initial_access", "Credential harvesting page served"),
    ("access_cred_captured", 26, 26.1, "initial_access", "Corporate credentials captured"),
    ("access_vpn_login", 28, 28.5, "initial_access", "VPN login with stolen credentials"),

    ("exec_payload_dl", 30, 30.5, "execution", "Malware payload downloaded"),
    ("exec_powershell", 31, 32, "execution", "Obfuscated PowerShell script executed"),
    ("exec_c2_beacon", 33, 33.5, "execution", "C2 beacon established to external server"),
    ("exec_mimikatz", 35, 36, "execution", "Mimikatz credential extraction"),

    ("persist_backdoor", 36, 37, "persistence", "Backdoor binary installed on workstation"),
    ("persist_schtasks", 37, 37.5, "persistence", "Scheduled task created for persistence"),
    ("persist_registry", 38, 38.5, "persistence", "Registry run key modified"),
    ("persist_webshell", 40, 41, "persistence", "Web shell deployed on web server"),

    ("lat_network_scan", 42, 44, "lateral_movement", "Internal network scanning via SMB"),
    ("lat_cred_dump_dc", 44, 46, "lateral_movement", "Credential dumping from domain controller"),
    ("lat_move_filesvr", 46, 47, "lateral_movement", "Lateral movement to file server via RDP"),
    ("lat_compromise_db", 48, 50, "lateral_movement", "Database server compromise"),
    ("lat_admin_creds", 50, 50.5, "lateral_movement", "Domain admin credentials obtained"),

    ("exfil_stage_data", 52, 54, "exfiltration", "Sensitive data staged on file server"),
    ("exfil_dns_tunnel", 54, 60, "exfiltration", "DNS tunneling channel active"),
    ("exfil_transfer", 58, 65, "exfiltration", "Bulk data transfer to external server"),
    ("exfil_archive", 60, 63, "exfiltration", "Encrypted archive creation"),
    ("exfil_complete", 65, 65.5, "exfiltration", "Exfiltration marked complete by attacker"),

    ("detect_ids_alert", 66, 66.5, "detection", "IDS anomaly alert on DNS traffic"),
    ("detect_siem_alert", 67, 67.5, "detection", "SIEM correlation for lateral movement"),
    ("detect_soc_investigate", 70, 73, "detection", "SOC analyst investigation"),
    ("detect_confirmed", 73, 73.5, "detection", "Security incident confirmed"),
    ("detect_forensic", 73.5, 74, "detection", "Forensic disk images captured"),

    ("resp_declared", 75, 75.5, "response", "P1 incident officially declared"),
    ("resp_isolate", 76, 78, "response", "Network isolation of affected systems"),
    ("resp_evidence", 78, 79, "response", "Evidence preservation and chain of custody"),
    ("resp_ir_team", 80, 82, "response", "External IR team engaged and on-site"),

    ("rem_av_update", 72, 73, "remediation", "AV signature update pushed prematurely"),
    ("rem_malware_rm", 76, 78, "remediation", "Malware removed from infected endpoints"),
    ("rem_patch", 78, 80, "remediation", "Critical vulnerability patch deployed"),
    ("rem_pwd_reset", 80, 82, "remediation", "Domain-wide password reset enforced"),

    ("rec_restore", 82, 86, "recovery", "System restoration from clean backups"),
    ("rec_services", 86, 88, "recovery", "Production services brought online"),
    ("rec_monitor", 88, 96, "recovery", "Enhanced monitoring deployed"),
    ("rec_review", 96, 98, "recovery", "Post-incident review conducted"),
    ("rec_closed", 100, 100.5, "recovery", "Incident officially closed"),

    ("maint_window", 40, 44, "maintenance", "Scheduled CRM system maintenance"),
]

SYSTEMS = [
    "web-server-01", "mail-server-01", "workstation-42", "vpn-gateway-01",
    "dc-01", "file-server-01", "db-server-01", "dns-server-01",
    "firewall-01", "ids-sensor-01",
]

EVENT_SYSTEMS = {
    "recon_port_scan": ["firewall-01"],
    "recon_vuln_scan": ["web-server-01"],
    "recon_dns_enum": ["dns-server-01"],
    "access_phish_send": ["mail-server-01"],
    "access_phish_click": ["workstation-42"],
    "access_harvest_cred": ["web-server-01"],
    "access_cred_captured": ["mail-server-01"],
    "access_vpn_login": ["vpn-gateway-01"],
    "exec_payload_dl": ["workstation-42"],
    "exec_powershell": ["workstation-42"],
    "exec_c2_beacon": ["workstation-42", "firewall-01"],
    "exec_mimikatz": ["workstation-42"],
    "persist_backdoor": ["workstation-42"],
    "persist_schtasks": ["workstation-42"],
    "persist_registry": ["workstation-42"],
    "persist_webshell": ["web-server-01"],
    "lat_network_scan": ["dc-01"],
    "lat_cred_dump_dc": ["dc-01"],
    "lat_move_filesvr": ["file-server-01"],
    "lat_compromise_db": ["db-server-01"],
    "lat_admin_creds": ["dc-01"],
    "exfil_stage_data": ["file-server-01"],
    "exfil_dns_tunnel": ["dns-server-01"],
    "exfil_transfer": ["file-server-01", "firewall-01"],
    "exfil_archive": ["file-server-01"],
    "exfil_complete": ["file-server-01"],
    "detect_ids_alert": ["ids-sensor-01"],
    "detect_siem_alert": ["ids-sensor-01"],
    "detect_forensic": ["workstation-42", "dc-01"],
    "resp_isolate": ["firewall-01"],
    "resp_evidence": ["workstation-42"],
    "rem_av_update": ["workstation-42", "dc-01"],
    "rem_malware_rm": ["workstation-42"],
    "rem_patch": ["web-server-01"],
    "rem_pwd_reset": ["dc-01"],
    "rec_restore": ["workstation-42", "web-server-01"],
    "rec_services": ["web-server-01", "db-server-01"],
    "rec_monitor": ["ids-sensor-01", "firewall-01"],
    "maint_window": ["crm-server-01"],
}

PHASE_ORDER = [
    "reconnaissance", "initial_access", "execution", "persistence",
    "lateral_movement", "exfiltration", "detection", "response",
    "remediation", "recovery",
]


def fmt(offset_hours: float) -> str:
    h = int(offset_hours)
    m = int((offset_hours - h) * 60)
    return f"T+{h:3d}h{m:02d}m"


def find_critical_path(events: list[TemporalEvent]) -> list[str]:
    sorted_evts = sorted(events, key=lambda e: e.interval.start)
    adj: dict[str, list[str]] = {e.event_id: [] for e in sorted_evts}
    causal_rels = {AllenRelation.BEFORE, AllenRelation.MEETS}
    for a in sorted_evts:
        for b in sorted_evts:
            if a.event_id == b.event_id:
                continue
            if a.interval.relate_to(b.interval) in causal_rels:
                adj[a.event_id].append(b.event_id)

    dp: dict[str, int] = {}
    parent: dict[str, str | None] = {}

    def longest(eid: str) -> int:
        if eid in dp:
            return dp[eid]
        best = 1
        best_next = None
        for nxt in adj[eid]:
            length = 1 + longest(nxt)
            if length > best:
                best = length
                best_next = nxt
        dp[eid] = best
        parent[eid] = best_next
        return best

    best_start = None
    best_len = 0
    for e in sorted_evts:
        length = longest(e.event_id)
        if length > best_len:
            best_len = length
            best_start = e.event_id

    path: list[str] = []
    curr = best_start
    while curr:
        path.append(curr)
        curr = parent.get(curr)
    return path


def causal_chain(events: list[TemporalEvent]) -> list[str]:
    sorted_evts = sorted(events, key=lambda e: e.interval.start)
    return [e.event_id for e in sorted_evts]


def find_overlapping(events: dict[str, TemporalEvent], label: str) -> list[dict]:
    target = events.get(label)
    if not target:
        return []
    results = []
    for eid, evt in events.items():
        if eid == label:
            continue
        rel = target.interval.relate_to(evt.interval)
        if rel in {
            AllenRelation.OVERLAPS, AllenRelation.OVERLAPPED_BY,
            AllenRelation.DURING, AllenRelation.CONTAINS,
            AllenRelation.STARTS, AllenRelation.STARTED_BY,
            AllenRelation.FINISHES, AllenRelation.FINISHED_BY,
            AllenRelation.EQUALS,
        }:
            results.append({"label": eid})
    return results


def main():
    temporal_events: dict[str, TemporalEvent] = {}

    print("=" * 70)
    print("SECTION 1: Incident Timeline Construction")
    print("=" * 70)

    for label, start_h, end_h, phase, desc in EVENTS:
        temporal_events[label] = TemporalEvent(
            event_id=label,
            label=label,
            interval=TimeInterval(start=BASE + start_h * H, end=BASE + end_h * H),
            metadata={"phase": phase, "description": desc},
        )

    print(f"  {len(temporal_events)} events across {len(PHASE_ORDER)} phases\n")

    phase_spans: dict[str, list[tuple[float, float]]] = {}
    for label, start_h, end_h, phase, _ in EVENTS:
        phase_spans.setdefault(phase, []).append((start_h, end_h))

    for phase in PHASE_ORDER:
        if phase not in phase_spans:
            continue
        intervals = phase_spans[phase]
        p_start = min(s for s, _ in intervals)
        p_end = max(e for _, e in intervals)
        n = len(intervals)
        print(f"  {phase:20s} {fmt(p_start)} - {fmt(p_end)}  "
              f"({n} events, {p_end - p_start:.1f}h span)")
    print()

    print("=" * 70)
    print("SECTION 2: Knowledge Graph - Affected Systems")
    print("=" * 70)

    systems_set = set(SYSTEMS) | {"crm-server-01"}
    related_count = 0
    for event_label, systems in EVENT_SYSTEMS.items():
        for sys in systems:
            related_count += 1

    system_hit_count: dict[str, int] = {}
    for systems in EVENT_SYSTEMS.values():
        for sys in systems:
            system_hit_count[sys] = system_hit_count.get(sys, 0) + 1

    print(f"  {len(systems_set)} systems, {related_count} event-system edges\n")
    print("  Systems by number of implicated events:")
    for sys, count in sorted(system_hit_count.items(), key=lambda x: -x[1]):
        bar = "#" * count
        print(f"    {sys:20s} {count:2d} {bar}")
    print()

    print("=" * 70)
    print("SECTION 3: Allen Relations Between Key Phase Transitions")
    print("=" * 70)

    key_pairs = [
        ("recon_port_scan", "access_phish_send", "Recon -> Access"),
        ("access_vpn_login", "exec_payload_dl", "Access -> Execution"),
        ("exec_mimikatz", "persist_backdoor", "Execution -> Persistence"),
        ("persist_webshell", "lat_network_scan", "Persistence -> Lateral"),
        ("lat_admin_creds", "exfil_stage_data", "Lateral -> Exfiltration"),
        ("exfil_complete", "detect_ids_alert", "Exfiltration -> Detection"),
        ("detect_confirmed", "resp_declared", "Detection -> Response"),
        ("rem_av_update", "detect_confirmed", "Remediation vs Detection"),
        ("resp_ir_team", "rec_restore", "Response -> Recovery"),
    ]
    print(f"  {'Event A':25s} {'Relation':15s} {'Event B':25s} Context")
    print(f"  {'-' * 25} {'-' * 15} {'-' * 25} {'-' * 25}")
    for a, b, context in key_pairs:
        ea = temporal_events.get(a)
        eb = temporal_events.get(b)
        if ea and eb:
            rel = ea.interval.relate_to(eb.interval)
            print(f"  {a:25s} {rel.value:15s} {b:25s} {context}")
    print()

    print("=" * 70)
    print("SECTION 4: Simultaneous Activity (Parallel Operations)")
    print("=" * 70)

    overlap_targets = [
        ("recon_osint", "Reconnaissance phase"),
        ("exec_mimikatz", "Execution phase"),
        ("exfil_dns_tunnel", "Exfiltration phase"),
        ("persist_webshell", "Persistence phase"),
        ("maint_window", "Red herring maintenance window"),
    ]
    for label, context in overlap_targets:
        results = find_overlapping(temporal_events, label)
        if results:
            ev = temporal_events[label]
            print(f"  Overlapping with {label} ({context}):")
            for r in results:
                other = temporal_events.get(r["label"])
                if ev and other:
                    rel = ev.interval.relate_to(other.interval)
                    off_s = (other.interval.start - BASE) / H
                    print(f"    {r['label']:25s} {fmt(off_s)} [{rel.value}]")
            print()

    print("=" * 70)
    print("SECTION 5: Critical Path Analysis (Longest BEFORE/MEETS Chain)")
    print("=" * 70)

    all_events_list = list(temporal_events.values())
    critical_path = find_critical_path(all_events_list)
    print(f"  Critical path: {len(critical_path)} events\n")

    for eid in critical_path:
        evt = temporal_events.get(eid)
        if evt:
            off_s = (evt.interval.start - BASE) / H
            phase = evt.metadata.get("phase", "")
            desc = evt.metadata.get("description", "")
            print(f"    {fmt(off_s)} {evt.label:25s} [{phase:18s}] {desc}")
    print()

    attack_milestones = [
        "recon_port_scan", "access_phish_send", "access_vpn_login",
        "exec_payload_dl", "exec_c2_beacon", "persist_backdoor",
        "lat_network_scan", "lat_cred_dump_dc", "lat_compromise_db",
        "exfil_stage_data", "exfil_transfer", "exfil_complete",
        "detect_ids_alert", "detect_confirmed", "resp_declared",
        "resp_isolate", "rem_malware_rm", "rem_patch",
        "rec_restore", "rec_services", "rec_closed",
    ]
    existing = [l for l in attack_milestones if l in temporal_events]
    if len(existing) >= 2:
        milestone_events = [temporal_events[l] for l in existing if l in temporal_events]
        ordered = causal_chain(milestone_events)
        print("  Key milestones in causal order:")
        for eid in ordered:
            evt = temporal_events.get(eid)
            if evt:
                off_s = (evt.interval.start - BASE) / H
                phase = evt.metadata.get("phase", "")
                print(f"    {fmt(off_s)} {evt.label:25s} [{phase}]")
        print()

    print("=" * 70)
    print("SECTION 6: Temporal Constraint Checking (Process Compliance)")
    print("=" * 70)

    constraints_to_add = [
        ("detect_confirmed", "resp_declared", AllenRelation.BEFORE,
         "Incident confirmed before response declared"),
        ("detect_confirmed", "rem_av_update", AllenRelation.BEFORE,
         "Detection complete before remediation starts"),
        ("detect_forensic", "resp_isolate", AllenRelation.BEFORE,
         "Forensic imaging before network isolation"),
        ("resp_isolate", "rem_malware_rm", AllenRelation.BEFORE,
         "Isolation before malware removal"),
    ]
    for a, b, expected_rel, desc in constraints_to_add:
        ea = temporal_events.get(a)
        eb = temporal_events.get(b)
        if ea and eb:
            actual = ea.interval.relate_to(eb.interval)
            passed = actual == expected_rel
            mark = "PASS" if passed else "FAIL"
            print(f"  [{mark:4s}] {desc}")
            if not passed and actual:
                print(f"        actual: {a} [{actual.value}] {b} "
                      f"(expected [{expected_rel.value}])")
    print()

    inconsistencies = []
    for a, b, expected_rel, _ in constraints_to_add:
        ea = temporal_events.get(a)
        eb = temporal_events.get(b)
        if ea and eb:
            actual = ea.interval.relate_to(eb.interval)
            if actual != expected_rel:
                inconsistencies.append({
                    "event_a": a, "event_b": b,
                    "expected_relation": expected_rel.value,
                    "actual_relation": actual.value,
                })
    if inconsistencies:
        print(f"  {len(inconsistencies)} constraint violation(s):")
        for inc in inconsistencies:
            print(f"    {inc['event_a']} vs {inc['event_b']}: "
                  f"expected {inc['expected_relation']}, "
                  f"got {inc['actual_relation']}")
    else:
        print("  All temporal constraints satisfied.")
    print()

    print("=" * 70)
    print("SECTION 7: Allen Relation Distribution (All Event Pairs)")
    print("=" * 70)

    event_list = list(temporal_events.values())
    counts: dict[str, int] = {}
    total_pairs = 0
    for i, a in enumerate(event_list):
        for j, b in enumerate(event_list):
            if i == j:
                continue
            if i < j:
                rel = a.interval.relate_to(b.interval)
                name = rel.value
                counts[name] = counts.get(name, 0) + 1
                total_pairs += 1

    print(f"  {total_pairs} pairwise relations across {len(event_list)} events:\n")
    for name, count in sorted(counts.items(), key=lambda x: -x[1]):
        bar = "#" * min(count, 50)
        print(f"    {name:15s} {count:4d} {bar}")
    print()

    print("=" * 70)
    print("SECTION 8: Incident Summary")
    print("=" * 70)

    all_events_sorted = sorted(temporal_events.values(), key=lambda e: e.interval.start)
    incident_start_h = (all_events_sorted[0].interval.start - BASE) / H
    incident_end_h = (max(e.interval.end for e in all_events_sorted) - BASE) / H
    total_hours = incident_end_h - incident_start_h

    attack_phases = {
        "reconnaissance", "initial_access", "execution", "persistence",
        "lateral_movement", "exfiltration",
    }
    defense_phases = {"detection", "response", "remediation", "recovery"}

    attack_evts = [e for e in all_events_sorted if e.metadata.get("phase") in attack_phases]
    attack_start_h = (min(e.interval.start for e in attack_evts) - BASE) / H
    attack_end_h = (max(e.interval.end for e in attack_evts) - BASE) / H

    defense_evts = [e for e in all_events_sorted if e.metadata.get("phase") in defense_phases]
    defense_start_h = (min(e.interval.start for e in defense_evts) - BASE) / H

    detection_gap = defense_start_h - attack_end_h

    print(f"  Total incident window:      {total_hours:.1f} hours")
    print(f"  Active attack phase:        {attack_end_h - attack_start_h:.1f} hours "
          f"({len(attack_evts)} events)")
    print(f"  Defense/recovery phase:     {incident_end_h - defense_start_h:.1f} hours "
          f"({len(defense_evts)} events)")
    print(f"  Detection gap:              {detection_gap:.1f} hours "
          f"(last attack event to first defense event)")
    print(f"  Total events:               {len(all_events_sorted)}")
    print(f"  Systems affected:           {len(system_hit_count)}")
    print(f"  Most impacted system:       "
          f"{max(system_hit_count, key=system_hit_count.get)} "
          f"({system_hit_count[max(system_hit_count, key=system_hit_count.get)]} events)")
    print(f"  Critical path length:       {len(critical_path)} events")

    print()
    print("  Temporal anomalies:")

    rem_start = temporal_events.get("rem_av_update")
    det_end = temporal_events.get("detect_confirmed")
    if rem_start and det_end:
        rem_off = (rem_start.interval.start - BASE) / H
        det_off = (det_end.interval.start - BASE) / H
        rel = rem_start.interval.relate_to(det_end.interval)
        print(f"    rem_av_update ({fmt(rem_off)}) [{rel.value}] "
              f"detect_confirmed ({fmt(det_off)})")
        print(f"      Remediation started BEFORE detection was complete")

    mw = temporal_events.get("maint_window")
    ws = temporal_events.get("persist_webshell")
    if mw and ws:
        rel = mw.interval.relate_to(ws.interval)
        mw_off_s = (mw.interval.start - BASE) / H
        ws_off_s = (ws.interval.start - BASE) / H
        print(f"    maint_window ({fmt(mw_off_s)}) [{rel.value}] "
              f"persist_webshell ({fmt(ws_off_s)})")
        print(f"      Unrelated CRM maintenance coincided with web shell deployment")
    print()

    print("  Parallel attacker activity:")
    parallel_pairs = [
        ("exfil_dns_tunnel", "exfil_transfer",
         "DNS tunneling overlapped with bulk data transfer"),
        ("recon_osint", "recon_dns_enum",
         "OSINT overlapped with DNS enumeration"),
    ]
    for a, b, note in parallel_pairs:
        ea = temporal_events.get(a)
        eb = temporal_events.get(b)
        if ea and eb:
            rel = ea.interval.relate_to(eb.interval)
            print(f"    {note}: {a} [{rel.value}] {b}")
    print()


if __name__ == "__main__":
    main()
