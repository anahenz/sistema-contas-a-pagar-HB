import uuid
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from server.api import create_app
from app.utils.wire import encode, decode
from app.database.connection import Database
from app.services.remote import RemoteFinance, ApiClient

PASSWORD = 'Senha-teste-segura-123'


@pytest.fixture
def api(tmp_path):
    app = create_app(tmp_path / 'server', 'admin@example.com', PASSWORD, run_scheduler=False)
    with TestClient(app) as client:
        result = client.post('/v1/login', json={'email': 'admin@example.com', 'password': PASSWORD})
        assert result.status_code == 200, result.text
        headers = {'Authorization': 'Bearer ' + result.json()['token']}
        yield client, headers, app


def snap(c, h):
    r = c.get('/v1/snapshot', headers=h)
    assert r.status_code == 200, r.text
    return decode(r.json())


def mutate(c, h, method, *args, revision=None, request_id=None):
    return c.post('/v1/mutate', headers=h, json=encode({
        'method': method, 'args': args, 'revision': revision or snap(c, h)['revision'],
        'request_id': request_id or str(uuid.uuid4())}))


def account(c, h):
    r = mutate(c, h, 'save_entity', 'condominios', {'nome': 'Aurora'})
    assert r.status_code == 200, r.text
    values = dict(condominio_id=r.json()['result'], categoria_id=snap(c,h)['entities']['categorias'][0]['id'],
        nome='Energia', valor_centavos=125000, data_emissao=date.today(), data_vencimento=date.today()+timedelta(days=7))
    r = mutate(c,h,'save_account',values)
    assert r.status_code == 200, r.text
    return r.json()['result'], values


def test_shared_crud_payment_conflict_and_permissions(api):
    c,h,app=api
    assert c.get('/v1/snapshot').status_code == 401
    assert c.post('/v1/users', headers=h, json={'email':'editor@example.com','password':PASSWORD}).status_code == 200
    login=c.post('/v1/login',json={'email':'editor@example.com','password':PASSWORD}).json()
    other={'Authorization':'Bearer '+login['token']}
    assert c.get('/v1/backup',headers=other).status_code == 403
    assert c.get('/v1/users',headers=other).status_code == 403
    aid, values=account(c,h)
    assert snap(c,other)['accounts'][0]['nome']=='Energia'
    stale=snap(c,other)['revision']
    r=mutate(c,h,'save_account',dict(values,nome='Energia editada'),aid)
    assert r.status_code==200
    assert mutate(c,other,'save_account',dict(values,nome='Sobrescrita'),aid,revision=stale).status_code==409
    payment={'data_pagamento':date.today(),'valor_centavos':125000,'forma_pagamento':'PIX'}
    assert mutate(c,other,'pay',aid,payment).status_code==200
    assert snap(c,h)['accounts'][0]['status']=='Paga'
    assert len(snap(c,h)['history'])==1
    assert mutate(c,h,'pay',aid,payment).status_code==400
    assert mutate(c,h,'undo_payment',aid).status_code==200
    assert snap(c,other)['history'][0]['payment']['estornado_em']
    assert mutate(c,h,'delete_account',aid).status_code==400
    assert mutate(c,h,'cancel_account',aid).status_code==200
    assert snap(c,other)['accounts'][0]['status']=='Cancelada'
    assert any('editor@example.com' in x['detalhes'] for x in snap(c,h)['audit'])
    editor=next(x for x in c.get('/v1/users',headers=h).json() if x['email']=='editor@example.com')
    assert c.patch('/v1/users/'+str(editor['id']),headers=h,json={'active':False}).status_code==200
    assert c.get('/v1/snapshot',headers=other).status_code==401


def test_idempotency_and_no_mass_assignment(api):
    c,h,_=api
    rid=str(uuid.uuid4()); rev=snap(c,h)['revision']
    r=mutate(c,h,'save_entity','condominios',{'nome':'Único'},revision=rev,request_id=rid)
    assert r.status_code==200
    repeat=mutate(c,h,'save_entity','condominios',{'nome':'Único'},revision=rev,request_id=rid)
    assert repeat.json()==r.json()
    assert len(snap(c,h)['entities']['condominios'])==1
    assert mutate(c,h,'save_entity','condominios',{'nome':'Ruim','id':99}).status_code==400
    assert mutate(c,h,'__getattribute__','db').status_code==400
    assert mutate(c,h,'save_entity','nao_existe',{'nome':'X'}).status_code==400


def test_backup_migration_and_restart(api,tmp_path):
    c,h,app=api
    aid,values=account(c,h)
    result=c.get('/v1/backup',headers=h)
    assert result.status_code==200
    content=result.content
    assert content.startswith(b'SQLite format 3')
    # No credentials in exported financial backup.
    assert PASSWORD.encode() not in content
    assert c.post('/v1/import',headers=h,content=content).status_code==409
    dest=tmp_path/'migrated'
    for iteration in range(2):
        with TestClient(create_app(dest,'owner@example.com',PASSWORD,run_scheduler=False)) as fresh:
            token=fresh.post('/v1/login',json={'email':'owner@example.com','password':PASSWORD}).json()['token']
            fh={'Authorization':'Bearer '+token}
            if iteration==0:
                invalid=fresh.post('/v1/import',headers=fh,content=b'not a database')
                assert invalid.status_code==400,invalid.text
                r=fresh.post('/v1/import',headers=fh,content=content)
                assert r.status_code==200,r.text
            assert snap(fresh,fh)['accounts'][0]['nome']=='Energia'


def test_client_snapshot_and_form_isolation(api,tmp_path):
    c,h,app=api
    aid,values=account(c,h)
    class Adapter:
        user={'email':'admin@example.com','role':'admin'}
        url='https://test.example'
        def request(self,path,data=None,method=None,raw=False):
            r=c.request(method or ('POST' if data is not None else 'GET'),path,headers=h,json=encode(data) if data is not None else None)
            if r.status_code>=400: raise ValueError(r.json()['detail'])
            return decode(r.json())
    db=Database(tmp_path/'client.sqlite3')
    remote=RemoteFinance(db,Adapter(),snap(c,h))
    assert remote.accounts(alerts=True)[0]['id']==aid
    assert remote.dashboard()['a_pagar']==125000
    form=remote.for_form()
    mutate(c,h,'save_account',dict(values,nome='Outra pessoa'),aid)
    remote.snapshot=snap(c,h)
    with pytest.raises(ValueError,match='Outra pessoa'):
        form.save_account(dict(values,nome='Antiga'),aid)
    assert remote.accounts(query='Outra pessoa')
    assert remote.accounts(status='Pagas')==[]
    db.engine.dispose()


def test_https_and_wire_validation():
    with pytest.raises(ValueError): ApiClient('http://example.com')
    with pytest.raises(ValueError): ApiClient('https://user:secret@example.com')
    value={'date':date.today(),'notes':'2026-01-01'}
    assert decode(encode(value))==value


def test_login_limits(api):
    c,h,_=api
    for _ in range(8):
        assert c.post('/v1/login',json={'email':'bad@example.com','password':'wrong'}).status_code==401
    r=c.post('/v1/login',json={'email':'bad@example.com','password':PASSWORD})
    assert '15 minutos' in r.json()['detail']


def test_online_desktop_widgets(api,tmp_path,qapp):
    from app.views.main_window import MainWindow
    from app.views.connection_page import ConnectionPage
    import shiboken6
    c,h,_=api
    db=Database(tmp_path/'ui.sqlite3')
    client=ApiClient('https://example.com')
    client.user={'email':'admin@example.com','role':'admin'}
    remote=RemoteFinance(db,client,snap(c,h))
    window=MainWindow(db,remote)
    window.notifications.timer.stop(); window.startup_timer.stop(); window.sync_timer.stop()
    assert window.remote
    assert window.nav[9].text()=='Equipe e backup'
    assert 'online' in window.statusBar().currentMessage()
    connection=ConnectionPage(db)
    connection.mode.setCurrentIndex(1)
    connection.login()
    assert connection.finance is None
    window.quitting=True
    window.close()
    shiboken6.delete(connection); shiboken6.delete(window)
    db.engine.dispose()


def test_two_simultaneous_writes_only_one_wins(api):
    from concurrent.futures import ThreadPoolExecutor
    c,h,_=api
    rev=snap(c,h)['revision']
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(mutate,c,h,'save_entity','condominios',{'nome':name},revision=rev)
                 for name in ('Primeiro','Segundo')]
        codes=sorted(f.result().status_code for f in futures)
    assert codes==[200,409]
    assert len(snap(c,h)['entities']['condominios'])==1


def test_failed_transaction_does_not_change_revision(api):
    c,h,_=api
    before=snap(c,h)
    bad={'nome':'Inválida','valor_centavos':123,'condominio_id':999,'categoria_id':1,
         'data_emissao':date.today(),'data_vencimento':date.today()}
    assert mutate(c,h,'save_account',bad).status_code==400
    after=snap(c,h)
    assert before['revision']==after['revision']
    assert after['accounts']==[]


def test_scheduler_creates_daily_backup(tmp_path):
    import time
    location=tmp_path/'scheduled'
    app=create_app(location,'admin@example.com',PASSWORD,run_scheduler=True)
    with TestClient(app) as c:
        for _ in range(100):
            if list((location/'backups').glob('*.sqlite3')):
                break
            time.sleep(.01)
        assert list((location/'backups').glob('*.sqlite3'))
        assert app.state.services['db'].get_setting('online_day')==date.today().isoformat()
