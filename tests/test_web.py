import time
import sqlite3
from datetime import date

from starlette.testclient import TestClient

from finder.provider import ReplayProvider, scripted_call, scripted_final
from finder.web import create_app


class WebReplay(ReplayProvider):
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


def ready(client, sid, target='ready'):
    until = time.monotonic() + 12
    while time.monotonic() < until:
        result = client.get('/api/sessions/' + sid).json()
        if result['state'] == target:
            return result
        assert result['state'] != 'error', result
        time.sleep(.02)
    raise AssertionError(result)


def draft_count(directory, sid):
    with sqlite3.connect(directory / sid / "drafts.sqlite") as db:
        return db.execute("SELECT count(*) FROM drafts").fetchone()[0]


def make_client(tmp_path, script):
    return TestClient(create_app(provider_factory=lambda: WebReplay(script), directory=tmp_path,
                                as_of=date(2026, 10, 27), configured=lambda: True))


def test_web_setup_static_assets_and_key_never_exposed(tmp_path):
    with TestClient(create_app(directory=tmp_path, configured=lambda: False)) as client:
        assert client.get('/').status_code == 200
        assert '<html lang="en">' in client.get('/').text
        assert client.get('/assets/app.js').status_code == 200
        assert client.get('/assets/.env').status_code == 404
        assert client.get('/api/status').json()['configured'] is False
        assert client.post('/api/sessions', json={}).status_code == 503
        assert client.post('/api/sessions', json={}, headers={'Origin':'https://unrelated.invalid'}).status_code == 400


def test_web_browse_followup_real_mcp_and_isolated_new_session(tmp_path):
    script = [scripted_call('search_opportunities', {'field':'AI','cities':['Riyadh']}),
              scripted_call('get_opportunity_details', {'opportunity_id':'OP012'}),
              scripted_final('Synthetic candidate OP012 in Riyadh; eligibility unchecked.'),
              scripted_call('search_opportunities', {'field':'AI','cities':['Jeddah']}),
              scripted_call('get_opportunity_details', {'opportunity_id':'OP002'}),
              scripted_final('Synthetic candidate OP002 in Jeddah; eligibility unchecked.')]
    with make_client(tmp_path, script) as client:
        sid = client.post('/api/sessions', json={}).json()['id']
        state = ready(client, sid)
        assert all(v is None for v in state['academic_details'].values())
        for prompt, expected in [('I need an internship opportunity for AI in Riyadh','OP012'), ('Are there any in Jeddah?','OP002')]:
            assert client.post(f'/api/sessions/{sid}/messages', json={'message':prompt}).status_code == 200
            state = ready(client, sid)
            assert expected in state['messages'][-1]['text']
            assert state['metrics']['stopped'] == 'completed'
        assert client.app.state.sessions[sid].harness.last_search['cities'] == ['Jeddah']
        assert 'Academic details button' in client.app.state.sessions[sid].agent.system()
        other = client.post('/api/sessions', json={}).json()['id']
        assert other != sid and ready(client,other)['messages'] == []
        assert client.post(f'/api/sessions/{sid}/details', json={'id':'S001'}).status_code == 400
        assert client.post(f'/api/sessions/{sid}/messages', json={'message':' '}).status_code == 400
        assert client.post(f'/api/sessions/{sid}/close', json={}).json()['closed'] is True
        assert client.get(f'/api/sessions/{sid}').status_code == 404


def test_web_actual_approval_denial_single_use_and_duplicate(tmp_path):
    script=[]
    for answer in ['The human declined. No draft saved.','Synthetic draft saved locally.','The draft already exists.']:
        script += [scripted_call('check_eligibility', {'opportunity_id':'OP001'}),
                   scripted_call('save_application_draft', {'opportunity_id':'OP001'}), scripted_final(answer)]
    with make_client(tmp_path, script) as client:
        sid=client.post('/api/sessions',json={}).json()['id'];ready(client,sid)
        details={'major':'Artificial Intelligence','year':4,'gpa':3.6,'training_kind':'coop','required_months':6,'available_from':'2027-01-01'}
        assert client.post(f'/api/sessions/{sid}/details',json=details).status_code==200
        for approved in [False, True]:
            client.post(f'/api/sessions/{sid}/messages',json={'message':'Prepare a local draft for OP001.'})
            state=ready(client,sid,'awaiting_approval');token=state['approval']['id']
            assert state['approval']['preview']['opportunity_id']=='OP001'
            assert draft_count(tmp_path, sid)==0
            assert client.post(f'/api/sessions/{sid}/details',json={'gpa':2.0}).status_code==409
            assert client.post(f'/api/sessions/{sid}/messages',json={'message':'Another request'}).status_code==409
            assert client.post(f'/api/sessions/{sid}/approval',json={'approval_id':'wrong','approved':True}).status_code==409
            assert client.post(f'/api/sessions/{sid}/approval',json={'approval_id':token,'approved':approved}).status_code==200
            state=ready(client,sid)
            assert draft_count(tmp_path, sid)==int(approved)
            assert client.post(f'/api/sessions/{sid}/approval',json={'approval_id':token,'approved':True}).status_code==409
        client.post(f'/api/sessions/{sid}/messages',json={'message':'Save the same draft again.'})
        state=ready(client,sid)
        assert 'existing' in state['messages'][-1]['text']
        assert draft_count(tmp_path, sid)==1
