from prometheus_client import Counter, Histogram

REQUESTS = Counter("gateway_requests_total", "Total HTTP requests received by the Gateway",["user", "model", "status"])
DURATION = Histogram("gateway_request_duration_seconds","time taken in the gateway",["user", "model"])
TOKENS = Counter("gateway_tokens_total","total tokens",["user","model", "type"])