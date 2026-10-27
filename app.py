from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError

from finder.agent import Agent
from finder.catalog import Catalog, ROOT, load_student
from finder.harness import Harness, Trace
from finder.mcp_client import CatalogBridge
from finder.models import Student
from finder.provider import OpenRouter, ProviderError, ReplayProvider, free_tool_models, scripted_call, scripted_final
from finder.storage import DraftStore


def approve_cli(preview):
    print("\nمراجعة مسودة محلية — لم يتم إرسال أي طلب / LOCAL DRAFT PREVIEW")
    print(json.dumps({k: v for k, v in preview.items() if k != "profile_fingerprint"}, ensure_ascii=False, indent=2))
    reply = input("حفظ هذه المسودة؟ اكتب YES أو نعم / Approve this exact draft? [no]: ").strip()
    return reply in {"YES", "نعم"}


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
    runtime = ROOT / "runtime"
    store = DraftStore(runtime / "drafts.sqlite")
    try:
        async with connection as provider, CatalogBridge(fixed_date) as bridge:
            harness = Harness(load_student(args.student), Catalog(), bridge, store, approve_cli, fixed_date,
                              Trace(runtime / "audit.jsonl"))
            agent = Agent(harness, provider, args.config)
            print("Internship Finder | فرص وطلاب اصطناعيون / SYNTHETIC DATA ONLY")
            print("/profile | /set FIELD VALUE | /reset | /quit. All drafts stay local.")
            print("Profile edits are trusted UI input, never model/tool arguments. GPA scale: 4.")
            while True:
                text = args.prompt if args.command == "ask" else input("\nYou / أنت: ").strip()
                if text in {"/quit", "/exit"}:
                    break
                if text == "/profile":
                    print(harness.student.model_dump_json(indent=2))
                    continue
                if text == "/reset":
                    agent.history.clear()
                    harness.last_search.clear()
                    print("Conversation memory cleared; saved drafts remain.")
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
                        print("Profile updated; conversation history cleared. /profile to inspect.")
                    except (ValueError, ValidationError) as exc:
                        print("Invalid profile update:", str(exc)[:250])
                    continue
                run = await agent.run(text)
                print("\nAssistant:", run.final.answer if run.final else f"Stopped safely: {run.stopped}. No successful answer was produced.")
                print("مسودات محلية فقط؛ لم يتم إرسال أي طلب / Local drafts only; no application sent.")
                print(f"[{run.stopped}; requests={run.requests}; tokens={run.prompt_tokens + run.completion_tokens}; cost=${run.cost_usd:.6f}]")
                if args.command == "ask":
                    break
    finally:
        store.close()


async def main():
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Internship Finder — synthetic-data capstone")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("chat", "ask"):
        p = sub.add_parser(command)
        p.add_argument("--student", default="S001")
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
        await chat(args)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (ProviderError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
    except (EOFError, KeyboardInterrupt):
        print("\nStopped. No automatic approval.")
