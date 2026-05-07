"""test_agent · Local Ollama bench harness.

Three things this harness measures, mapped to the crawler's actual workloads:

  1. Connectivity. Ollama lives behind a VPN (10.83.81.246:11434). If the VPN
     drops, /api/tags hangs forever; the health probe surfaces that fast.
  2. Per-tier latency. The crawler classifies vendor scope (tiny tier, ~200
     tokens in / yes-no JSON out), runs discovery (light tier, structured),
     and merges enrichment (heavy tier, ~6 KB context). Headline tokens/sec
     does not tell you which tier a model is actually fit for.
  3. Concurrency cliffs. ENRICHMENT_CONCURRENCY=16 on Ollama in production.
     Single-request timings hide the queueing wall.

Run:  python app.py
Open: http://127.0.0.1:5050
"""
from __future__ import annotations

import json
import os
import socket
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import urlparse

import requests
from flask import Flask, Response, jsonify, render_template, request, stream_with_context

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://10.83.81.246:11434").rstrip("/")
HTTP_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "300"))
APP_PORT = int(os.environ.get("APP_PORT", "5050"))

app = Flask(__name__, static_folder="static", template_folder="templates")


# Real crawler workloads, condensed. The bench fires these so a "fast" model
# on a generic prompt does not get mistaken for a fast model on our prompt.
PRESETS: dict[str, dict[str, Any]] = {
    "scope_classify": {
        "label": "Vendor scope classifier",
        "tier_hint": "tiny",
        "system": (
            "You judge whether a company sells security/defense/cyber/police/border products. "
            "Reply with strict JSON only: {\"is_in_scope\": bool, \"industry_tag\": str, "
            "\"confidence\": float, \"reason\": str}. industry_tag is one of: defense, "
            "cybersecurity, law_enforcement, surveillance, border_control, critical_infra, "
            "dual_use, hotel, news_media, academia, event_platform, other."
        ),
        "user": (
            "Domain: helsing.ai\n"
            "Company: Helsing\n"
            "Tagline: AI for defence\n"
            "Description: Helsing builds AI software and hardware for defence. We integrate "
            "real-time sensor data into mission systems for air, land and sea platforms.\n"
            "Products: AI mission systems, electronic warfare, autonomy stacks\n"
            "Industries (claimed): defense, AI\n"
            "Expos seen: DSEI 2024, Eurosatory 2024\n"
        ),
        "json_schema": {
            "type": "object",
            "properties": {
                "is_in_scope": {"type": "boolean"},
                "industry_tag": {"type": "string"},
                "confidence": {"type": "number"},
                "reason": {"type": "string"},
            },
            "required": ["is_in_scope", "industry_tag", "confidence", "reason"],
        },
    },
    "discovery": {
        "label": "Expo discovery query expansion",
        "tier_hint": "light",
        "system": (
            "You generate web search queries that surface official exhibitor lists for trade "
            "shows in defence, cybersecurity and policing. Return strict JSON only: "
            "{\"queries\": string[]} with 6-10 queries, no duplicates."
        ),
        "user": "Trade show: 'Milipol Paris 2025'. Country: France. Focus: homeland security.",
        "json_schema": {
            "type": "object",
            "properties": {
                "queries": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["queries"],
        },
    },
    "enrichment_merge": {
        "label": "Vendor enrichment merge (~6 KB)",
        "tier_hint": "heavy",
        "system": (
            "Merge the homepage, about and products pages of a vendor into a canonical Vendor "
            "object. Return strict JSON only: {company_name, tagline, description, products, "
            "industries, country}. Description capped at 600 characters; products and "
            "industries are short string arrays."
        ),
        "user": (
            "[homepage]\n"
            + ("Helsing is a defence AI company headquartered in Munich. " * 40)
            + "\n\n[about]\n"
            + (
                "We build mission systems integrating sensor fusion, autonomy and electronic "
                "warfare. Founded 2021. Operations across Germany, UK and France. " * 30
            )
            + "\n\n[products]\n"
            + ("- Altra: edge mission AI\n- Cirra: EW platform\n- Lura: AI-piloted aircraft\n" * 20)
        ),
        "json_schema": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string"},
                "tagline": {"type": "string"},
                "description": {"type": "string"},
                "products": {"type": "array", "items": {"type": "string"}},
                "industries": {"type": "array", "items": {"type": "string"}},
                "country": {"type": "string"},
            },
            "required": ["company_name", "description"],
        },
    },
    "freeform": {
        "label": "Freeform smoke test",
        "tier_hint": None,
        "system": "You are a concise assistant. Reply in 2-3 sentences.",
        "user": "Explain why TTFT matters more than tokens/sec for a binary classifier.",
    },
}

EMBED_TEXTS = [
    "Helsing GmbH (helsing.ai) defence AI company Munich",
    "Anduril Industries (anduril.com) autonomous defence systems USA",
    "BAE Systems (baesystems.com) defence prime UK",
    "Booking.com global hotel reservation platform",
    "MIT Lincoln Laboratory federally funded research center",
    "Reuters wire service news media",
]


def _now_ms() -> float:
    return time.perf_counter() * 1000.0


def _ns_to_ms(value: float | int | None) -> float | None:
    if value is None:
        return None
    return round(value / 1e6, 2)


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def _classify_tier(model: dict[str, Any]) -> str:
    name = (model.get("name") or "").lower()
    if "embed" in name:
        return "embedding"
    psize = ((model.get("details") or {}).get("parameter_size") or "").lower().replace("b", "").strip()
    try:
        billions = float(psize)
    except ValueError:
        billions = 0.0
    if billions >= 30:
        return "heavy"
    if billions >= 10:
        return "light"
    return "tiny"


def _tcp_probe(url: str, timeout: float = 2.0) -> dict[str, Any]:
    p = urlparse(url)
    host = p.hostname or ""
    port = p.port or (443 if p.scheme == "https" else 80)
    t0 = _now_ms()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"ok": True, "host": host, "port": port, "rtt_ms": round(_now_ms() - t0, 2)}
    except Exception as exc:
        return {"ok": False, "host": host, "port": port, "error": str(exc)}


def _ollama_chat(
    model: str,
    system: str | None,
    user: str,
    *,
    stream: bool = False,
    fmt: Any = None,
    num_ctx: int | None = None,
    num_predict: int | None = None,
    keep_alive: str | None = "5m",
    think: bool | None = None,
) -> Any:
    msgs: list[dict[str, str]] = []
    if system:
        msgs.append({"role": "system", "content": system})
    # Qwen3 also honors `/no_think` as a soft signal in the user prompt; we layer
    # it on top of the body-level flag so older Ollama daemons still benefit.
    user_payload = user
    if think is False and "/no_think" not in user_payload:
        user_payload = f"{user_payload}\n/no_think"
    msgs.append({"role": "user", "content": user_payload})
    options: dict[str, Any] = {"temperature": 0}
    if num_ctx:
        options["num_ctx"] = num_ctx
    if num_predict is not None:
        options["num_predict"] = num_predict
    body: dict[str, Any] = {
        "model": model,
        "messages": msgs,
        "stream": stream,
        "options": options,
    }
    if keep_alive:
        body["keep_alive"] = keep_alive
    if fmt is not None:
        body["format"] = fmt
    if think is not None:
        body["think"] = bool(think)
    if stream:
        return requests.post(f"{OLLAMA_URL}/api/chat", json=body, stream=True, timeout=HTTP_TIMEOUT)
    return requests.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=HTTP_TIMEOUT).json()


def _resolve_preset(preset_key: str | None, body: dict[str, Any], structured: bool) -> tuple[str | None, str, Any]:
    """Return (system, user, format). Body fields override preset."""
    user = body.get("prompt") or ""
    system = body.get("system")
    fmt: Any = body.get("format")
    if preset_key and preset_key in PRESETS:
        p = PRESETS[preset_key]
        if not user:
            user = p.get("user", "")
        if not system:
            system = p.get("system")
        if structured and "json_schema" in p and fmt is None:
            fmt = p["json_schema"]
    return system, user, fmt


@app.get("/")
def index() -> Any:
    return render_template("index.html", ollama_url=OLLAMA_URL)


@app.get("/api/health")
def health() -> Any:
    tcp = _tcp_probe(OLLAMA_URL)
    payload: dict[str, Any] = {
        "ollama_url": OLLAMA_URL,
        "tcp": tcp,
        "vpn_ok": bool(tcp.get("ok")),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    if not tcp["ok"]:
        payload.update(
            {
                "ok": False,
                "stage": "tcp",
                "hint": "TCP to Ollama failed. VPN likely down. Reconnect and retry.",
                "models": [],
            }
        )
        return jsonify(payload)

    try:
        t0 = _now_ms()
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=HTTP_TIMEOUT)
        rtt = round(_now_ms() - t0, 2)
        r.raise_for_status()
        raw = r.json().get("models", [])
        models = []
        for m in raw:
            d = m.get("details") or {}
            models.append(
                {
                    "name": m.get("name"),
                    "size_gb": round((m.get("size") or 0) / 1e9, 2),
                    "parameter_size": d.get("parameter_size"),
                    "quantization": d.get("quantization_level"),
                    "family": d.get("family"),
                    "tier": _classify_tier(m),
                    "modified_at": m.get("modified_at"),
                }
            )
        models.sort(key=lambda x: (x["tier"] != "embedding", x["tier"], x["name"]))
        payload.update({"ok": True, "stage": "ready", "tags_rtt_ms": rtt, "models": models})
        return jsonify(payload)
    except Exception as exc:
        payload.update(
            {
                "ok": False,
                "stage": "tags",
                "error": str(exc),
                "hint": "TCP works but /api/tags failed. Daemon reloading or upstream auth missing.",
                "models": [],
            }
        )
        return jsonify(payload)


@app.get("/api/presets")
def presets() -> Any:
    return jsonify(
        {
            k: {
                "label": v["label"],
                "tier_hint": v.get("tier_hint"),
                "has_schema": "json_schema" in v,
            }
            for k, v in PRESETS.items()
        }
    )


def _run_single_pass(
    *,
    model: str,
    system: str | None,
    user: str,
    fmt: Any,
    runs: int,
    num_ctx: int | None,
    num_predict: int | None,
    think: bool | None,
    preset_key: str | None,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for i in range(runs):
        t0 = _now_ms()
        try:
            data = _ollama_chat(
                model,
                system,
                user,
                stream=False,
                fmt=fmt,
                num_ctx=num_ctx,
                num_predict=num_predict,
                think=think,
            )
            wall_ms = round(_now_ms() - t0, 2)
            eval_count = data.get("eval_count") or 0
            eval_dur_ms = _ns_to_ms(data.get("eval_duration"))
            tps = round(eval_count / (eval_dur_ms / 1000.0), 2) if eval_dur_ms else None
            msg = data.get("message") or {}
            results.append(
                {
                    "run": i + 1,
                    "ok": True,
                    "wall_ms": wall_ms,
                    "load_ms": _ns_to_ms(data.get("load_duration")),
                    "prompt_eval_ms": _ns_to_ms(data.get("prompt_eval_duration")),
                    "eval_ms": eval_dur_ms,
                    "total_ms": _ns_to_ms(data.get("total_duration")),
                    "prompt_tokens": data.get("prompt_eval_count"),
                    "completion_tokens": eval_count,
                    "tokens_per_s": tps,
                    "content": (msg.get("content") or "")[:4000],
                    # Ollama returns thinking in `message.thinking` when emitted.
                    "thinking": (msg.get("thinking") or "")[:4000],
                }
            )
        except Exception as exc:
            results.append({"run": i + 1, "ok": False, "error": str(exc), "wall_ms": round(_now_ms() - t0, 2)})

    ok_runs = [r for r in results if r.get("ok")]
    walls = [r["wall_ms"] for r in ok_runs]
    tps_vals = [r["tokens_per_s"] for r in ok_runs if r.get("tokens_per_s")]
    completions = [r["completion_tokens"] for r in ok_runs if r.get("completion_tokens")]
    summary = {
        "model": model,
        "preset": preset_key,
        "think": think,
        "runs": runs,
        "ok": len(ok_runs),
        "wall_ms_p50": round(_percentile(walls, 0.5), 2) if walls else None,
        "tokens_per_s_avg": round(statistics.mean(tps_vals), 2) if tps_vals else None,
        "completion_tokens_avg": round(statistics.mean(completions), 1) if completions else None,
        "cold_wall_ms": ok_runs[0]["wall_ms"] if ok_runs else None,
        "warm_wall_ms": ok_runs[-1]["wall_ms"] if ok_runs else None,
    }
    return {"summary": summary, "runs": results}


def _resolve_think(body: dict[str, Any]) -> bool | None:
    """Body field -> tri-state. 'auto' / null / missing -> None (model default)."""
    raw = body.get("think")
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    s = str(raw).lower()
    if s in ("on", "true", "1", "yes"):
        return True
    if s in ("off", "false", "0", "no"):
        return False
    return None  # 'auto'


@app.post("/api/benchmark/single")
def bench_single() -> Any:
    body = request.get_json(force=True) or {}
    model: str = body["model"]
    runs = max(1, min(int(body.get("runs", 1)), 10))
    structured = bool(body.get("structured"))
    preset_key = body.get("preset")
    system, user, fmt = _resolve_preset(preset_key, body, structured)
    num_predict = body.get("num_predict")
    num_ctx = body.get("num_ctx")
    think = _resolve_think(body)

    common = dict(
        model=model, system=system, user=user, fmt=fmt, runs=runs,
        num_ctx=num_ctx, num_predict=num_predict, preset_key=preset_key,
    )

    if body.get("compare_think"):
        # A/B: same prompt twice, once with think forced off, once forced on.
        # Ordering matters for cold-load fairness — run think=False first since
        # that's the production setting; warm cache benefits the think=True pass.
        off = _run_single_pass(think=False, **common)
        on = _run_single_pass(think=True, **common)
        return jsonify({"compare": True, "think_off": off, "think_on": on})

    return jsonify(_run_single_pass(think=think, **common))


@app.post("/api/benchmark/concurrency")
def bench_concurrency() -> Any:
    body = request.get_json(force=True) or {}
    model: str = body["model"]
    n = max(1, min(int(body.get("n", 8)), 64))
    structured = bool(body.get("structured"))
    preset_key = body.get("preset")
    system, user, fmt = _resolve_preset(preset_key, body, structured)
    if not user:
        user = "Reply with the single word: OK."
    num_predict = int(body.get("num_predict", 64))
    think = _resolve_think(body)

    # Warmup so we measure steady state, not cold load.
    try:
        _ollama_chat(model, None, "warmup", stream=False, num_predict=4, think=think)
    except Exception:
        pass

    def _one(idx: int) -> dict[str, Any]:
        t0 = _now_ms()
        try:
            data = _ollama_chat(model, system, user, stream=False, fmt=fmt, num_predict=num_predict, think=think)
            return {
                "i": idx,
                "ok": True,
                "wall_ms": round(_now_ms() - t0, 2),
                "tokens": data.get("eval_count") or 0,
                "eval_ms": _ns_to_ms(data.get("eval_duration")),
            }
        except Exception as exc:
            return {"i": idx, "ok": False, "wall_ms": round(_now_ms() - t0, 2), "error": str(exc)}

    t0 = _now_ms()
    with ThreadPoolExecutor(max_workers=n) as ex:
        rs = list(ex.map(_one, range(n)))
    total_ms = round(_now_ms() - t0, 2)
    ok = [r for r in rs if r.get("ok")]
    walls = [r["wall_ms"] for r in ok]
    return jsonify(
        {
            "model": model,
            "concurrency": n,
            "wall_total_ms": total_ms,
            "ok": len(ok),
            "failed": n - len(ok),
            "p50_ms": round(_percentile(walls, 0.5), 2),
            "p95_ms": round(_percentile(walls, 0.95), 2),
            "p99_ms": round(_percentile(walls, 0.99), 2),
            "throughput_req_per_s": round(len(ok) / (total_ms / 1000.0), 2) if total_ms else None,
            "tokens_total": sum(r.get("tokens", 0) for r in ok),
            "results": rs,
        }
    )


@app.post("/api/benchmark/embed")
def bench_embed() -> Any:
    body = request.get_json(force=True) or {}
    model = body["model"]
    texts: list[str] = body.get("texts") or EMBED_TEXTS
    runs: list[dict[str, Any]] = []
    for i, txt in enumerate(texts):
        t0 = _now_ms()
        try:
            r = requests.post(
                f"{OLLAMA_URL}/api/embed",
                json={"model": model, "input": txt, "keep_alive": "5m"},
                timeout=HTTP_TIMEOUT,
            )
            r.raise_for_status()
            data = r.json()
            emb = (data.get("embeddings") or [[]])[0]
            runs.append(
                {
                    "i": i,
                    "ok": True,
                    "wall_ms": round(_now_ms() - t0, 2),
                    "dim": len(emb),
                    "preview": [round(x, 4) for x in emb[:4]],
                    "text": txt[:80],
                }
            )
        except Exception as exc:
            runs.append({"i": i, "ok": False, "error": str(exc), "wall_ms": round(_now_ms() - t0, 2), "text": txt[:80]})

    walls = [r["wall_ms"] for r in runs if r.get("ok")]
    return jsonify(
        {
            "model": model,
            "n": len(texts),
            "p50_ms": round(_percentile(walls, 0.5), 2) if walls else None,
            "avg_ms": round(statistics.mean(walls), 2) if walls else None,
            "results": runs,
        }
    )


@app.post("/api/chat/stream")
def chat_stream() -> Any:
    body = request.get_json(force=True) or {}
    model: str = body["model"]
    structured = bool(body.get("structured"))
    preset_key = body.get("preset")
    system, user, fmt = _resolve_preset(preset_key, body, structured)
    if not user:
        user = body.get("prompt") or ""
    think = _resolve_think(body)

    @stream_with_context
    def gen() -> Iterable[str]:
        t0 = _now_ms()
        first_tok_ms: float | None = None
        try:
            r = _ollama_chat(model, system, user, stream=True, fmt=fmt, think=think)
            for line in r.iter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except Exception:
                    continue
                msg = chunk.get("message") or {}
                # Newer Ollama emits thinking in `message.thinking` (separate
                # field from content). Surface it as its own SSE channel so the
                # UI can dim/segregate the reasoning trace.
                thinking = msg.get("thinking")
                if thinking:
                    yield f"event: thinking\ndata: {json.dumps({'t': thinking})}\n\n"
                content = msg.get("content")
                if content:
                    if first_tok_ms is None:
                        first_tok_ms = round(_now_ms() - t0, 2)
                        yield f"event: ttft\ndata: {json.dumps({'ttft_ms': first_tok_ms})}\n\n"
                    yield f"event: token\ndata: {json.dumps({'t': content})}\n\n"
                if chunk.get("done"):
                    summary: dict[str, Any] = {
                        "wall_ms": round(_now_ms() - t0, 2),
                        "ttft_ms": first_tok_ms,
                        "load_ms": _ns_to_ms(chunk.get("load_duration")),
                        "prompt_eval_ms": _ns_to_ms(chunk.get("prompt_eval_duration")),
                        "eval_ms": _ns_to_ms(chunk.get("eval_duration")),
                        "prompt_tokens": chunk.get("prompt_eval_count"),
                        "completion_tokens": chunk.get("eval_count"),
                    }
                    if summary["eval_ms"] and chunk.get("eval_count"):
                        summary["tokens_per_s"] = round(
                            chunk["eval_count"] / (summary["eval_ms"] / 1000.0), 2
                        )
                    yield f"event: done\ndata: {json.dumps(summary)}\n\n"
                    return
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"

    return Response(
        gen(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


if __name__ == "__main__":
    print(f"[test_agent] Ollama target: {OLLAMA_URL}")
    print(f"[test_agent] Open http://127.0.0.1:{APP_PORT}/")
    app.run(host="127.0.0.1", port=APP_PORT, debug=False, threaded=True)
