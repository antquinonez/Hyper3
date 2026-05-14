SERVICES = {
    "auth_service": {"type": "service", "language": "go"},
    "api_gateway": {"type": "service", "language": "go"},
    "user_service": {"type": "service", "language": "python"},
    "payment_service": {"type": "service", "language": "java"},
    "notification_service": {"type": "service", "language": "python"},
    "search_service": {"type": "service", "language": "rust"},
    "analytics_service": {"type": "service", "language": "python"},
    "ml_service": {"type": "service", "language": "python"},
    "cache_service": {"type": "service", "language": "go"},
    "db_service": {"type": "service", "language": "postgresql"},
}

INFRA = {
    "kubernetes": {"type": "platform", "role": "orchestration"},
    "prometheus": {"type": "platform", "role": "monitoring"},
    "grafana": {"type": "platform", "role": "visualization"},
    "rabbitmq": {"type": "platform", "role": "messaging"},
}

LIBS = {
    "react": {"type": "library", "ecosystem": "frontend"},
    "django": {"type": "library", "ecosystem": "backend"},
    "tensorflow": {"type": "library", "ecosystem": "ml"},
    "redis_client": {"type": "library", "ecosystem": "cache"},
}

DEPENDENCY_EDGES = [
    ("api_gateway", "auth_service", "depends_on"),
    ("api_gateway", "user_service", "depends_on"),
    ("api_gateway", "payment_service", "depends_on"),
    ("api_gateway", "search_service", "depends_on"),
    ("user_service", "db_service", "depends_on"),
    ("payment_service", "db_service", "depends_on"),
    ("payment_service", "notification_service", "depends_on"),
    ("search_service", "cache_service", "depends_on"),
    ("search_service", "db_service", "depends_on"),
    ("analytics_service", "db_service", "depends_on"),
    ("analytics_service", "ml_service", "depends_on"),
    ("ml_service", "tensorflow", "depends_on"),
    ("ml_service", "cache_service", "depends_on"),
    ("auth_service", "cache_service", "depends_on"),
    ("auth_service", "db_service", "depends_on"),
    ("notification_service", "rabbitmq", "depends_on"),
    ("analytics_service", "prometheus", "depends_on"),
    ("cache_service", "redis_client", "depends_on"),
    ("user_service", "django", "depends_on"),
    ("notification_service", "django", "depends_on"),
]

MONITORING_EDGES = [
    ("prometheus", "api_gateway", "monitors"),
    ("prometheus", "auth_service", "monitors"),
    ("prometheus", "user_service", "monitors"),
    ("prometheus", "payment_service", "monitors"),
    ("grafana", "prometheus", "visualizes"),
]
