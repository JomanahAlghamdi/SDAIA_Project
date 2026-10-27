from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError

from finder.agent import Agent
from finder.catalog import Catalog, ROOT, load_student
from finder.harness import Harness, Trace
from finder.intake import CITIES, MAJORS, collect_details, new_student
from finder.mcp_client import CatalogBridge
from finder.models import Student
from finder.provider import OpenRouter, ProviderError, ReplayProvider, free_tool_models, scripted_call, scripted_final
from finder.storage import DraftStore


def approve_cli(preview):
    print("\nLOCAL DRAFT PREVIEW - no application will be sent to an employer.")
    print(json.dumps({k: v for k, v in preview.items() if k != "profile_fingerprint"}, ensure_ascii=False, indent=2))
    reply = input("Save this exact local draft? Type YES to approve; anything else declines: ").strip()
    return reply == "YES"


def session_input(args):
    major, city = getattr(args, "major", None), getattr(args, "city", None)
    if args.student:
        if major or city:
            raise ValueError("Use either an explicit --student test fixture or --major and --city, not both.")
        student = load_student(args.student)
        print(f"EXPLICIT TEST FIXTURE: {args.student}. These are fictional preset details, not your personal profile.")
        return student, None
    # Ordinary chat starts empty. The user's own message supplies search preferences;
    # an interest in AI is not a declaration of an academic major.
    return new_student(major), city


async def demo(allow_interactive=False):
    """A real four-tool/MCP/write demo driven by explicit scripted calls, not an LLM."""
    import tempfile
    with tempfile.TemporaryDirectory(prefix="internship-demo-") as tmp:
        (ROOT / "results/local").mkdir(parents=True, exist_ok=True)
        (ROOT / "results/local/demo_trace.jsonl").write_text("", encoding="utf-8")
        trace = Trace(ROOT / "results/local/demo_trace.jsonl")
        store = DraftStore(Path(tmp) / "demo.sqlite")
        try:
            async with CatalogBridge(date(2026, 10, 27)) as bridge:
                harness = Harness(load_student("S001"), Catalog(), bridge, store,
                                  approve=approve_cli if allow_interactive else lambda _: False,
                                  today=date(2026, 10, 27), trace=trace)
                provider = ReplayProvider([
                    scripted_call("search_opportunities", {"field": "Data", "cities": ["Riyadh"], "kind": "coop"}, "d1"),
                    scripted_call("get_opportunity_details", {"opportunity_id": "OP001"}, "d2"),
                    scripted_call("check_eligibility", {"opportunity_id": "OP001"}, "d3"),
                    scripted_call("save_application_draft", {"opportunity_id": "OP001"}, "d4"),
                    scripted_final("Offline scripted tool demonstration finished. See the actual save result below; no LLM was called.")])
                run = await Agent(harness, provider).run("Scripted demo; please show the save preview.")
                save_results = [e["result"] for e in run.events if e["event"] == "tool_result" and e["tool"] == "save_application_draft"]
                print(json.dumps({"mode": "offline_scripted_not_llm", "stopped": run.stopped,
                                  "mcp_tools": bridge.tools, "mcp_calls": bridge.calls,
                                  "save_results": save_results, "draft_count": store.count()}, ensure_ascii=False, indent=2))
        finally:
            store.close()


async def chat(args):
    connection = OpenRouter()  # Fail clearly on missing credentials before starting MCP.
    fixed_date = date.fromisoformat(args.as_of) if args.as_of else None
    print("Internship Finder | English | SYNTHETIC OPPORTUNITIES ONLY")
    student, city = session_input(args)
    # Anonymous sessions never reuse another session's drafts or academic details.
    runtime = ROOT / "runtime" / ("fixtures" if args.student else "sessions") / (args.student or uuid.uuid4().hex)
    store = DraftStore(runtime / "drafts.sqlite")
    try:
        async with connection as provider, CatalogBridge(fixed_date) as bridge:
            harness = Harness(student, Catalog(), bridge, store, approve_cli, fixed_date,
                              Trace(runtime / "audit.jsonl"))
            agent = Agent(harness, provider, args.config)
            print("Hi! Tell me what kind of internship you are looking for.")
            print('For example: "I need an internship opportunity for AI in Riyadh."')
            print("/help: optional commands | /reset: new conversation | /quit: exit")
            print(f"Demo catalog date: {harness.today().isoformat()}. Opportunities are fictional. No employer submissions.")
            preferences = "; ".join(value for value in (
                f"Academic major={student.major}" if getattr(args, "major", None) else "",
                f"Preferred city={city}" if city else "") if value)
            while True:
                if args.command == "ask":
                    text = args.prompt
                else:
                    text = input("\nYou: ").strip()
                if not text:
                    continue
                if text in {"/quit", "/exit"}:
                    break
                if text == "/help":
                    print("Ask in English, for example: What are the requirements? Are there any in Jeddah?")
                    print("Browsing needs no personal or academic record.")
                    print("Optional eligibility demo: /details enters fictional academic values; /facts shows them.")
                    print("/set FIELD VALUE edits one value. Only a separate YES prompt can approve a local draft.")
                    print("/reset clears conversation and entered facts; saved drafts remain. /quit exits.")
                    continue
                if text in {"/facts", "/profile"}:
                    print("Optional academic facts entered in this session (null means unknown):")
                    print(harness.student.model_dump_json(indent=2))
                    continue
                if text == "/details":
                    harness.student = collect_details(harness.student)
                    agent.history.clear()
                    print("Session details updated. Ask me to check an opportunity, for example: Check OP001.")
                    continue
                if text == "/reset":
                    agent.history.clear()
                    harness.last_search.clear()
                    harness.student = new_student() if not args.student else load_student(args.student)
                    preferences = ""
                    print("New conversation started; saved drafts remain.")
                    continue
                if text.startswith("/set "):
                    try:
                        _, field, value = text.split(" ", 2)
                        if field not in {"major", "year", "gpa", "training_kind", "required_months", "available_from"}:
                            raise ValueError("Field is not editable")
                        raw = harness.student.model_dump(mode="json")
                        raw[field] = None if value == "null" else value
                        harness.student = Student.model_validate(raw)
                        agent.history.clear()
                        print("Academic fact updated; conversation history cleared. /facts to inspect.")
                    except (ValueError, ValidationError) as exc:
                        print("Invalid academic value:", str(exc)[:250])
                    continue
                if preferences:
                    text = f"Optional preferences supplied at launch: {preferences}.\n{text}"
                    preferences = ""
                run = await agent.run(text)
                print("\nAssistant:", run.final.answer if run.final else f"Stopped safely: {run.stopped}. No successful answer was produced.")
                if any(event.get("tool") == "save_application_draft" for event in run.events):
                    print("Local drafts only; no application sent.")
                if getattr(args, "verbose", False):
                    print(f"[{run.stopped}; requests={run.requests}; tokens={run.prompt_tokens + run.completion_tokens}; cost=${run.cost_usd:.6f}]")
                if args.command == "ask":
                    return 0 if run.stopped == "completed" else 2
    finally:
        store.close()


async def main():
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Internship Finder — synthetic-data capstone")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("chat", "ask"):
        p = sub.add_parser(command)
        p.add_argument("--student", choices=[f"S{i:03}" for i in range(1, 7)], help="Explicit test fixture only; omitted by default")
        p.add_argument("--major", choices=MAJORS, help="Optional academic major; ordinary chat needs no form")
        p.add_argument("--city", choices=CITIES, help="Optional city; you can state it in your message instead")
        p.add_argument("--verbose", action="store_true", help="Show request/token/cost diagnostics")
        p.add_argument("--config", choices=["A", "B"], default="B")
        p.add_argument("--as-of", help="Explicit demo clock; normal chat uses today's date")
        if command == "ask":
            p.add_argument("prompt")
    sub.add_parser("models")
    demo_parser = sub.add_parser("demo")
    demo_parser.add_argument("--interactive", action="store_true", help="Ask a real human for the scripted demo's approval")
    sub.add_parser("doctor")
    args = parser.parse_args()
    if args.command == "models":
        for model in await free_tool_models():
            print(model["id"])
    elif args.command == "demo":
        await demo(args.interactive)
    elif args.command == "doctor":
        import os
        async with CatalogBridge(date(2026, 10, 27)) as bridge:
            result = await bridge.call("search_opportunities", {"limit": 1})
            print(json.dumps({"catalog_records": len(Catalog().items), "mcp_tools": bridge.tools,
                              "mcp_protocol": bridge.initialized.protocolVersion,
                              "mcp_search_ok": result["total"] > 0,
                              "key_present": bool(os.getenv("OPENROUTER_API_KEY")),
                              "model_configured": bool(os.getenv("OPENROUTER_MODEL"))}, indent=2))
    else:
        return await chat(args)


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()) or 0)
    except (ProviderError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
    except (EOFError, KeyboardInterrupt):
        print("\nStopped. No automatic approval.")
