import os

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "gateway.db"))

VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://localhost:9000/v1")
VLLM_API_KEY = os.environ.get("VLLM_API_KEY", "dev-secret-abc")
VLLM_SERVED_MODEL = os.environ.get("VLLM_SERVED_MODEL", "chat-small")

PERSONALITIES = ["pirate", "genz", "formal"]

GATEWAY_HOST = os.environ.get("GATEWAY_HOST", "0.0.0.0")
GATEWAY_PORT = int(os.environ.get("GATEWAY_PORT", "8000"))

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000/v1")