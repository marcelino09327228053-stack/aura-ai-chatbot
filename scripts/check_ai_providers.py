"""Opt-in live provider smoke check; prints no prompts, replies, or credentials."""
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import ai_service
from app.services.ai_provider_router import route_candidates

async def main():
    results = []
    for candidate in route_candidates("smoke-test"):
        try:
            answer = await asyncio.to_thread(
                ai_service.generate_reply,
                "Reply with exactly: OK",
                candidate.provider,
                candidate.model,
                None,
            )
            results.append({
                "provider": candidate.provider,
                "model": candidate.model,
                "status": "ok",
                "input_tokens": int(getattr(answer, "input_tokens", 0) or 0),
                "output_tokens": int(getattr(answer, "output_tokens", 0) or 0),
            })
        except Exception as exc:
            results.append({
                "provider": candidate.provider,
                "model": candidate.model,
                "status": "failed",
                "error_type": type(exc).__name__,
                "http_status": getattr(exc, "status_code", None),
            })
    print(json.dumps(results, indent=2))
    raise SystemExit(0 if results and all(item["status"] == "ok" for item in results) else 1)

if __name__ == "__main__": asyncio.run(main())
