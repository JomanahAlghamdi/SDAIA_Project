from __future__ import annotations

import inspect
import json
import time
import uuid
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from .catalog import Catalog, check_eligibility
from .models import Student, TOOL_MODELS
from .storage import DraftStore, fingerprint


class Trace:
    def __init__(self, path: Path | None = None):
        self.path = path
        self.events: list[dict] = []

    def add(self, event: str, **values):
        row = {"time": time.time(), "event": event, **values}
        self.events.append(row)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


class Harness:
    def __init__(self, student: Student, catalog: Catalog, bridge, store: DraftStore,
                 approve=None, today: date | None = None, trace: Trace | None = None):
        self.student, self.catalog, self.bridge, self.store = student, catalog, bridge, store
        self.approve = approve or (lambda preview: False)
        self.fixed_date = today
        self.trace = trace or Trace()
        self.session_id = uuid.uuid4().hex
        self.last_search: dict = {}
        self.denied_this_turn: set[str] = set()

    def today(self):
        return self.fixed_date or date.today()

    def begin_turn(self):
        self.denied_this_turn.clear()

    def preview(self, opportunity_id: str) -> dict:
        item = self.catalog.get(opportunity_id)
        return {"student_id": self.student.id, "opportunity_id": item.id,
                "company": item.company, "title": item.title,
                "training_kind": item.kind, "duration_months": item.duration_months,
                "start_date": item.start_date.isoformat(), "status": "Draft",
                "synthetic": True, "sent_to_employer": False,
                "profile_fingerprint": fingerprint(self.student.model_dump(mode="json"))}

    async def dispatch(self, name: str, arguments: dict) -> dict:
        if name not in TOOL_MODELS:
            self.trace.add("guard_block", reason="unknown_tool", tool=name)
            return {"error": "unknown_tool"}
        try:
            args = TOOL_MODELS[name].model_validate(arguments)
        except ValidationError as exc:
            self.trace.add("guard_block", reason="invalid_arguments", tool=name)
            return {"error": "invalid_arguments", "fields": [".".join(map(str, e["loc"])) for e in exc.errors()]}
        params = args.model_dump(mode="json", exclude_none=True)
        self.trace.add("tool_call", tool=name, arguments=params,
                       transport="mcp_stdio" if name in {"search_opportunities", "get_opportunity_details"} else "local")
        try:
            if name in {"search_opportunities", "get_opportunity_details"}:
                result = await self.bridge.call(name, params)
                if name == "search_opportunities":
                    self.last_search = params
            elif name == "check_eligibility":
                result = check_eligibility(self.student, self.catalog.get(args.opportunity_id), self.today())
            else:
                result = await self._save(args.opportunity_id)
        except (ValueError, PermissionError) as exc:
            result = {"error": type(exc).__name__, "message": str(exc)[:200]}
        self.trace.add("tool_result", tool=name, result=result)
        return result

    async def _save(self, opportunity_id: str) -> dict:
        if opportunity_id in self.denied_this_turn:
            return {"status": "denied", "reason": "Already denied this turn; no repeat approval prompt."}
        eligibility = check_eligibility(self.student, self.catalog.get(opportunity_id), self.today())
        if eligibility["status"] != "eligible":
            self.trace.add("guard_block", reason="eligibility", opportunity_id=opportunity_id)
            return {"status": "blocked", "eligibility": eligibility}
        existing = self.store.existing(self.student.id, opportunity_id)
        if existing:
            return {**existing, "status": "existing", "sent_to_employer": False}
        preview = self.preview(opportunity_id)
        self.trace.add("approval_requested", preview=preview)
        approved = self.approve(dict(preview))
        if inspect.isawaitable(approved):
            approved = await approved
        if approved is not True:
            self.denied_this_turn.add(opportunity_id)
            self.trace.add("guard_block", reason="human_denied", opportunity_id=opportunity_id)
            return {"status": "denied", "saved": False}
        # Human reviewed this exact object. Recheck owner/content/eligibility after the callback.
        if preview != self.preview(opportunity_id) or check_eligibility(self.student, self.catalog.get(opportunity_id), self.today())["status"] != "eligible":
            self.trace.add("guard_block", reason="stale_approval", opportunity_id=opportunity_id)
            return {"status": "blocked", "reason": "Details changed; a new approval is required."}
        token = self.store.issue_approval(self.session_id, self.student.id, preview)
        result = self.store.commit(token, self.session_id, self.student.id, preview)
        self.trace.add("approval_consumed", opportunity_id=opportunity_id, draft_id=result["draft_id"])
        return result
