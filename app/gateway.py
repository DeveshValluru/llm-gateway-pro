import json
import time
import httpx
from fastapi import FastAPI, HTTPException, Header, Depends, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Any

from config import VLLM_BASE_URL, VLLM_API_KEY, GATEWAY_HOST, GATEWAY_PORT, PERSONALITIES
from database import get_user_by_api_key, log_request, count_recent_requests, init_db, seed_users
from metrics import REQUESTS, DURATION, TOKENS, TTFT
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(title="LLM Gateway Pro")


@app.on_event("startup")
def startup():
    init_db()
    seed_users()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list[Message]
    max_tokens: Optional[int] = 200
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False
    stream_options: Optional[dict[str, Any]] = None


def get_current_user(authorization: Optional[str] = Header(None)):
    if authorization is None or not authorization.startswith("Bearer "):
        REQUESTS.labels(user="unknown", model="unknown", status="401").inc()
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    api_key = authorization.replace("Bearer ", "")
    user = get_user_by_api_key(api_key)

    if user is None:
        REQUESTS.labels(user="unknown", model="unknown", status="401").inc()
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return user


def _record_success(user, model, latency_ms, prompt_tokens, completion_tokens, status):
    log_request(
        user_id=user["id"],
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        status_code=status,
    )
    REQUESTS.labels(user=user["username"], model=model, status=str(status)).inc()
    DURATION.labels(user=user["username"], model=model).observe(latency_ms / 1000)
    TOKENS.labels(user=user["username"], model=model, type="prompt").inc(prompt_tokens)
    TOKENS.labels(user=user["username"], model=model, type="completion").inc(completion_tokens)


@app.post("/v1/chat/completions")
async def chat_completions(
    body: ChatRequest,
    user: dict = Depends(get_current_user),
):
    if body.model not in user["allowed_models"]:
        REQUESTS.labels(user=user["username"], model=body.model, status="403").inc()
        raise HTTPException(status_code=403, detail=f"User '{user['username']}' not allowed to use model '{body.model}'")

    recent = count_recent_requests(user["id"], 60)
    if recent >= user["rate_limit"]:
        REQUESTS.labels(user=user["username"], model=body.model, status="429").inc()
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded: {user['rate_limit']} requests/min")

    payload = body.model_dump(exclude_none=True)

    if body.stream:
        payload["stream_options"] = {"include_usage": True}
        return StreamingResponse(
            _stream_from_vllm(payload, user, body.model),
            media_type="text/event-stream",
        )

    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{VLLM_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {VLLM_API_KEY}"},
            json=payload,
        )
    latency_ms = (time.perf_counter() - t0) * 1000
    status = response.status_code

    if status == 200:
        data = response.json()
        usage = data.get("usage", {})
        _record_success(
            user, body.model, latency_ms,
            usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), status,
        )
        return data
    else:
        log_request(
            user_id=user["id"], model=body.model,
            prompt_tokens=0, completion_tokens=0,
            latency_ms=latency_ms, status_code=status,
        )
        REQUESTS.labels(user=user["username"], model=body.model, status=str(status)).inc()
        DURATION.labels(user=user["username"], model=body.model).observe(latency_ms / 1000)
        raise HTTPException(status_code=status, detail=response.text)


async def _stream_from_vllm(payload: dict, user: dict, model: str):
    t0 = time.perf_counter()
    first_token_at: Optional[float] = None
    prompt_tokens = 0
    completion_tokens = 0
    status = 200

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{VLLM_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {VLLM_API_KEY}"},
                json=payload,
            ) as response:
                status = response.status_code
                async for line in response.aiter_lines():
                    if not line:
                        yield "\n"
                        continue
                    yield line + "\n\n"
                    if line.startswith("data: ") and not line.endswith("[DONE]"):
                        try:
                            chunk = json.loads(line[6:])
                            if first_token_at is None:
                                choices = chunk.get("choices") or []
                                if choices and choices[0].get("delta", {}).get("content"):
                                    first_token_at = time.perf_counter()
                            usage = chunk.get("usage")
                            if usage:
                                prompt_tokens = usage.get("prompt_tokens", 0)
                                completion_tokens = usage.get("completion_tokens", 0)
                        except json.JSONDecodeError:
                            pass
    finally:
        latency_ms = (time.perf_counter() - t0) * 1000
        if status == 200:
            _record_success(user, model, latency_ms, prompt_tokens, completion_tokens, status)
            if first_token_at is not None:
                TTFT.labels(user=user["username"], model=model).observe(first_token_at - t0)
        else:
            log_request(
                user_id=user["id"], model=model,
                prompt_tokens=0, completion_tokens=0,
                latency_ms=latency_ms, status_code=status,
            )
            REQUESTS.labels(user=user["username"], model=model, status=str(status)).inc()
            DURATION.labels(user=user["username"], model=model).observe(latency_ms / 1000)


@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
def root():
    return {"service": "llm-gateway-pro", "status": "ok"}


@app.get("/health")
async def health():
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(f"{VLLM_BASE_URL.replace('/v1', '')}/health")
            vllm_ok = resp.status_code == 200
        except Exception:
            vllm_ok = False
    return {
        "gateway": "ok",
        "vllm": "ok" if vllm_ok else "unreachable",
        "personalities": PERSONALITIES,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=GATEWAY_HOST, port=GATEWAY_PORT)
