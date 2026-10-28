"""Actual browser + HTTP + live model smoke test. No scripted model responses."""
from __future__ import annotations
import asyncio
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evals.run import hashes
from dotenv import load_dotenv
import httpx
from playwright.async_api import async_playwright


async def main():
    load_dotenv(ROOT / '.env')
    out = ROOT / 'results/web_live'
    out.mkdir(parents=True, exist_ok=True)
    report = {'status':'running','llm_used':True,'hashes':hashes(),
              'started_at':datetime.now(timezone.utc).isoformat(),'checks':{},'turns':[]}
    def save():
        (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    save()
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    server = subprocess.Popen([sys.executable,'app.py','web','--port',str(port),'--as-of','2026-10-27'],cwd=ROOT,
                               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    base=f'http://127.0.0.1:{port}'
    try:
        async with httpx.AsyncClient() as client:
            for _ in range(100):
                try:
                    response=await client.get(base+'/api/status')
                    if response.status_code==200:break
                except httpx.HTTPError: pass
                await asyncio.sleep(.1)
            else:raise RuntimeError('Web server did not start')
            if not response.json()['configured']:raise RuntimeError('Model key/model missing; no live browser test performed')
        async with async_playwright() as p:
            browser=await p.chromium.launch(headless=True)
            page=await browser.new_page(viewport={'width':1365,'height':900})
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            await page.goto(base)
            await page.wait_for_function("document.querySelector('#connection').textContent === 'Ready to explore'",timeout=90000)
            await page.screenshot(path=str(out/'welcome.png'),full_page=True)
            async def turn(prompt, decision=None):
                previous=await page.locator('.message.assistant').count()
                await page.locator('#message').fill(prompt)
                await page.locator('#send').click()
                if decision is not None:
                    await page.locator('#approval').wait_for(state='visible',timeout=180000)
                    await page.screenshot(path=str(out/('approval-'+str(decision).lower()+'.png')),full_page=True)
                    await page.locator('#approve' if decision else '#decline').click()
                await page.wait_for_function("n => document.querySelectorAll('.message.assistant').length > n && document.querySelector('#connection').textContent === 'Ready to explore'",arg=previous,timeout=240000)
                answer=await page.locator('.message.assistant .bubble').last.inner_text()
                # Read the same session snapshot served to the UI; no direct harness access.
                snapshot=await page.evaluate("fetch('/api/sessions/'+session.id).then(r=>r.json())")
                report['turns'].append({'prompt':prompt,'answer':answer,'decision':decision,'metrics':snapshot['metrics']})
                save()
                if snapshot['metrics']['stopped']!='completed':raise RuntimeError('Model did not complete browser turn')
                return answer,snapshot
            answer,state=await turn('I need an internship opportunity for AI in Riyadh')
            assert 'OP012' in answer or 'OP017' in answer
            assert all(v is None for v in state['academic_details'].values())
            report['checks']['browse_without_profile']=True
            answer,_=await turn('What are the requirements?')
            assert 'GPA' in answer.upper() and ('OP012' in answer or 'OP017' in answer)
            report['checks']['published_requirements']=True
            answer,_=await turn('Are there any in Jeddah?')
            assert 'OP002' in answer
            report['checks']['city_followup']=True
            await page.screenshot(path=str(out/'conversation.png'),full_page=True)
            await page.locator('#detailsButton').click()
            await page.locator('[name=major]').select_option('Artificial Intelligence')
            for field,value in {'year':'4','gpa':'3.6','required_months':'6','available_from':'2027-01-01'}.items():
                await page.locator(f'[name={field}]').fill(value)
            await page.locator('[name=training_kind]').select_option('coop')
            await page.locator('#detailsForm button[type=submit]').click()
            await page.locator('#detailsDialog').wait_for(state='hidden')
            _,state=await turn('Prepare a local draft for OP001 and show me the approval preview.',False)
            assert any('Local draft result: denied' in m['text'] for m in state['messages'])
            report['checks']['decline_no_save']=True
            _,state=await turn('Please prepare the OP001 local draft again and show its preview.',True)
            assert any('Local draft result: Draft' in m['text'] for m in state['messages'])
            report['checks']['explicit_approval_save']=True
            _,state=await turn('Save the same OP001 draft again, without creating a duplicate.')
            assert any('Local draft result: existing' in m['text'] for m in state['messages'])
            report['checks']['duplicate_prevented']=True
            await page.screenshot(path=str(out/'saved.png'),full_page=True)
            sid=state['id']
            trace=ROOT/'runtime/web'/sid/'audit.jsonl'
            (out/'audit.jsonl').write_bytes(trace.read_bytes())
            import sqlite3
            with sqlite3.connect(ROOT/'runtime/web'/sid/'drafts.sqlite') as db:
                assert db.execute('SELECT count(*) FROM drafts').fetchone()[0]==1
            report['checks']['one_actual_draft']=True
            assert not errors,errors
            report['checks']['no_browser_errors']=True
            report['status']='complete'
            await browser.close()
    except Exception as exc:
        report['status']='failed'
        report['reason']=type(exc).__name__+': '+str(exc)[:300]
        raise
    finally:
        save();server.terminate()
        try:server.wait(timeout=10)
        except subprocess.TimeoutExpired:server.kill();server.wait()
    print(json.dumps({'status':report['status'],'checks':report['checks']}))


if __name__=='__main__':
    asyncio.run(main())
