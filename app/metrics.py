from prometheus_client import Counter, Histogram

REQUESTS = Counter(
    "gateway_requests_total",
    "Total HTTP requests received by the gateway",
    ["user", "model", "status"],
)

DURATION = Histogram(
    "gateway_request_duration_seconds",
    "End-to-end request latency as measured by the gateway",
    ["user", "model"],
)

TOKENS = Counter(
    "gateway_tokens_total",
    "Total tokens, split by prompt vs completion",
    ["user", "model", "type"],
)

# Time to first content token on streaming responses. Captures the latency
# the user actually feels — how long until something starts appearing.
TTFT = Histogram(
    "gateway_ttft_seconds",
    "Time to first content token on streaming responses",
    ["user", "model"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0),
)
