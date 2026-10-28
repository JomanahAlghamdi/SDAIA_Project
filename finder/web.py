"""Local HTML client for the same agent/MCP/consent boundary as the CLI."""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route

from .agent import Agent
from .catalog import Catalog, ROOT
from .harness import Harness, Trace
from .intake import new_student
from .models import Student
from .provider import OpenRouter, ProviderError
from .storage import DraftStore
from .mcp_client import CatalogBridge

ACADEMIC_FIELDS = {"major", "year", "gpa", "training_kind", "required_months", "available_from"}


class WebSession:
    def __init__(self, directory, provider_factory, as_of, config):
        self.id = uuid.uuid4().hex
        self.directory = Path(directory) / self.id
        self.directory.mkdir(parents=True)
        self.provider_factory, self.as_of, self.config = provider_factory, as_of, config
        self.state = "starting"
        self.messages = []
        self.pending = None
        self.decision = None
        self.error = ""
        self.metrics = None
        self.harness = self.agent = None
        self.queue = asyncio.Queue()
        self.last_active = time.monotonic()
        self.task = asyncio.create_task(self.worker())

    async def approve(self, preview):
        self.decision = asyncio.get_running_loop().create_future()
        self.pending = {"id": uuid.uuid4().hex,
                        "preview": {k: v for k, v in preview.items() if k != "profile_fingerprint"}}
        self.state = "awaiting_approval"
        try:
            return await asyncio.wait_for(self.decision, timeout=300)
        except asyncio.TimeoutError:
            return False
        finally:
            self.pending = self.decision = None
            self.state = "running"

    async def worker(self):
        store = DraftStore(self.directory / "drafts.sqlite")
        try:
            # The MCP client and its task groups enter/exit in this SAME task.
            async with self.provider_factory() as provider, CatalogBridge(self.as_of) as bridge:
                self.harness = Harness(new_student(), Catalog(), bridge, store, self.approve,
                                       self.as_of, Trace(self.directory / "audit.jsonl"))
                self.agent = Agent(self.harness, provider, self.config, interface="web")
                self.state = "ready"
                while True:
                    prompt = await self.queue.get()
                    if prompt is None:
                        break
                    run = await self.agent.run(prompt)
                    if run.final:
                        answer = run.final.answer
                    else:
                        answer = (run.error if run.stopped == "provider_error" and run.error else
                                  "I could not finish this request. Please try a shorter question.")
                    self.messages.append({"role": "assistant", "text": answer, "stopped": run.stopped})
                    for e in run.events:
                        if e.get("event") == "tool_result" and e.get("tool") == "save_application_draft":
                            r = e["result"]
                            self.messages.append({"role": "notice", "text": "Local draft result: "
                                + str(r.get("status", r.get("error", "unknown")))
                                + (" · " + r["draft_id"] if r.get("draft_id") else "")
                                + ". No application sent to an employer."})
                    self.metrics = {"stopped": run.stopped, "requests": run.requests,
                                    "tokens": run.prompt_tokens + run.completion_tokens, "cost_usd": run.cost_usd}
                    self.messages = self.messages[-40:]
                    self.last_active = time.monotonic()
                    self.state = "ready"
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.error = str(exc)[:180] if isinstance(exc, ProviderError) else "The session could not start. Check the local server and start a new chat."
            self.state = "error"
        finally:
            store.close()

    def snapshot(self):
        self.last_active = time.monotonic()
        return {"id": self.id, "state": self.state, "messages": self.messages,
                "approval": self.pending, "error": self.error, "metrics": self.metrics,
                "academic_details": ({k: v for k, v in self.harness.student.model_dump(mode="json").items()
                                      if k in ACADEMIC_FIELDS} if self.harness else {})}

    async def close(self):
        if self.decision and not self.decision.done():
            self.decision.set_result(False)
        self.task.cancel()
        await asyncio.gather(self.task, return_exceptions=True)


def create_app(*, provider_factory=OpenRouter, directory=None, as_of=None, config="B", configured=None):
    sessions = {}
    directory = Path(directory or ROOT / "runtime/web")
    configured = configured or (lambda: bool(os.getenv("OPENROUTER_API_KEY")) and bool(os.getenv("OPENROUTER_MODEL")))

    @asynccontextmanager
    async def lifespan(app):
        yield
        await asyncio.gather(*(s.close() for s in sessions.values()))

    async def index(request):
        return FileResponse(ROOT / "web/index.html")

    async def asset(request):
        name = request.path_params["name"]
        if name not in {"app.js", "style.css"}:
            return JSONResponse({"error": "Not found"}, status_code=404)
        return FileResponse(ROOT / "web" / name)

    async def status(request):
        return JSONResponse({"configured": configured(), "config": config,
                             "as_of": (as_of or date.today()).isoformat(), "synthetic": True})

    async def payload(request):
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            raise ValueError("This local action must come from the same page.")
        if len(raw := await request.body()) > 16000:
            raise ValueError("Request is too large.")
        result = json.loads(raw or b"{}")
        if not isinstance(result, dict):
            raise ValueError("Expected a JSON object.")
        return result

    async def new_session(request):
        try:
            await payload(request)
        except (ValueError, json.JSONDecodeError):
            return JSONResponse({"error": "Invalid request."}, status_code=400)
        if not configured():
            return JSONResponse({"error": "Add your OpenRouter key and model to .env, then restart the server."}, status_code=503)
        for sid, old in list(sessions.items()):
            if time.monotonic() - old.last_active > 3600:
                await old.close()
                del sessions[sid]
        if len(sessions) >= 16:
            return JSONResponse({"error": "Close an existing chat or restart the local server."}, status_code=429)
        s = WebSession(directory, provider_factory, as_of, config)
        sessions[s.id] = s
        return JSONResponse(s.snapshot(), status_code=201)

    async def session_route(request: Request):
        session = sessions.get(request.path_params["sid"])
        if not session:
            return JSONResponse({"error": "Chat not found. Start a new chat."}, status_code=404)
        if request.method == "GET":
            return JSONResponse(session.snapshot())
        try:
            body = await payload(request)
            action = request.path_params.get("action", "")
            if action == "approval":
                if (session.state != "awaiting_approval" or not session.pending
                        or body.get("approval_id") != session.pending["id"]
                        or type(body.get("approved")) is not bool or session.decision.done()):
                    return JSONResponse({"error": "This approval is no longer available."}, status_code=409)
                session.decision.set_result(body["approved"])
                return JSONResponse({"accepted": True})
            if session.state != "ready":
                return JSONResponse({"error": "Wait for this request to finish."}, status_code=409)
            if action == "messages":
                prompt = body.get("message")
                if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 4000:
                    raise ValueError("Enter a message between 1 and 4,000 characters.")
                session.state = "running"
                session.messages.append({"role": "user", "text": prompt.strip()})
                session.queue.put_nowait(prompt.strip())
            elif action == "details":
                if set(body) - ACADEMIC_FIELDS:
                    raise ValueError("Only the displayed academic fields can be changed.")
                raw = session.harness.student.model_dump(mode="json")
                session.harness.student = Student.model_validate({**raw, **body})
                session.agent.history.clear()
                session.messages.append({"role": "notice", "text": "Optional academic details updated. You can now ask for a personal eligibility check."})
            elif action == "close":
                await session.close()
                del sessions[session.id]
                return JSONResponse({"closed": True})
            else:
                return JSONResponse({"error": "Unknown action."}, status_code=404)
            return JSONResponse(session.snapshot())
        except (ValueError, ValidationError) as exc:
            message = "Use valid academic values in the displayed ranges." if isinstance(exc, ValidationError) else str(exc)
            return JSONResponse({"error": message}, status_code=400)

    app = Starlette(lifespan=lifespan, routes=[
        Route("/", index), Route("/assets/{name}", asset), Route("/api/status", status),
        Route("/api/sessions", new_session, methods=["POST"]),
        Route("/api/sessions/{sid}", session_route),
        Route("/api/sessions/{sid}/{action}", session_route, methods=["POST"]),
    ])
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
    app.state.sessions = sessions
    return app


async def serve(args):
    import uvicorn
    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    app = create_app(as_of=as_of, config=args.config)
    print(f"Open http://127.0.0.1:{args.port} in your browser. Keep this terminal open.")
    await uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=args.port, log_level="warning")).serve()
