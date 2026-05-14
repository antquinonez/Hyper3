"""Infrastructure event data for a cloud service outage forensics scenario."""

SERVICES = {
    "web_app": {"type": "service", "tier": "frontend"},
    "api_gateway": {"type": "service", "tier": "middleware"},
    "database": {"type": "service", "tier": "backend"},
    "cache": {"type": "service", "tier": "backend"},
    "load_balancer": {"type": "service", "tier": "infrastructure"},
}

DEPENDENCY_EDGES = [
    ("web_app", "api_gateway", "depends_on"),
    ("api_gateway", "database", "depends_on"),
    ("api_gateway", "cache", "depends_on"),
    ("load_balancer", "web_app", "routes_to"),
]

EVENTS = [
    ("maint_window",    "database",      12.00, 13.30),
    ("deploy_cache",    "cache",         13.00, 13.45),
    ("deploy_api",      "api_gateway",   13.30, 14.00),
    ("alert_latency",   "api_gateway",   13.55, 14.05),
    ("incident",        "web_app",       14.00, 14.30),
    ("failover",        "database",      14.05, 14.15),
    ("cache_flush",     "cache",         14.10, 14.20),
    ("resolution",      "web_app",       14.30, 14.35),
    ("postmortem",      "web_app",       15.00, 16.00),
]

ALLEN_PAIRS = [
    ("maint_window", "incident",     "Maintenance ended before the incident started"),
    ("deploy_cache", "maint_window", "Cache deployment overlapped with maintenance"),
    ("incident",     "failover",     "Failover happened during the incident"),
    ("failover",     "cache_flush",  "Failover overlapped with cache flush"),
    ("resolution",   "postmortem",   "Postmortem happened after resolution"),
]
