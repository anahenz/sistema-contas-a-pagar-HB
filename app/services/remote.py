import copy
import json
import uuid
from datetime import date, datetime
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from app.services.finance import FinanceService
from app.utils.formatting import STATUS_FILTER
from app.utils.wire import encode, decode


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class ApiClient:
    def __init__(self, url, token='', allow_local=False):
        parsed = urlsplit(url.strip())
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Informe somente o endereço HTTPS do servidor.')
        if parsed.scheme != 'https' and not (allow_local and parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost')):
            raise ValueError('O servidor deve usar HTTPS.')
        if not parsed.hostname or parsed.path not in ('', '/'):
            raise ValueError('Use a URL principal, sem caminho adicional.')
        self.url = url.strip().rstrip('/')
        self.token = token
        self.user = {}

    def request(self, path, data=None, method=None, raw=False):
        headers = {'Accept': 'application/json'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        if isinstance(data, bytes):
            body = data
            headers['Content-Type'] = 'application/octet-stream'
        elif data is not None:
            body = json.dumps(encode(data)).encode()
            headers['Content-Type'] = 'application/json'
        else:
            body = None
        req = Request(self.url + path, data=body, headers=headers, method=method)
        try:
            with build_opener(NoRedirect()).open(req, timeout=30) as response:
                content = response.read()
                return content if raw else decode(json.loads(content))
        except HTTPError as exc:
            try:
                detail = json.loads(exc.read()).get('detail', '')
                if not isinstance(detail, str):
                    detail = 'Confira os campos informados.'
            except Exception:
                detail = 'O servidor recusou a solicitação.'
            raise ValueError(detail or f'Erro HTTP {exc.code}.') from None
        except (URLError, TimeoutError, OSError):
            raise ValueError('Sem conexão com o servidor. Confira sua internet. Se estava salvando, atualize a lista antes de tentar novamente para conferir se a operação foi concluída.') from None

    def login(self, email, password):
        result = self.request('/v1/login', {'email': email, 'password': password})
        self.token = result.pop('token')
        self.user = result
        return self.request('/v1/snapshot')


class RemoteFinance(FinanceService):
    """Reads an immutable server snapshot. Every write is authenticated and versioned."""
    remote = True

    def __init__(self, db, client, snapshot):
        self.db, self.client = db, client
        self.snapshot = snapshot
        self.online = True
        self.pending = None

    def for_form(self):
        # A form keeps its starting snapshot even if another page refreshes.
        form = RemoteFinance(self.db, self.client, self.snapshot)
        form.online = self.online
        return form

    def entities(self, kind, query=''):
        return [copy.deepcopy(r) for r in self.snapshot['entities'][kind]
                if query.casefold() in ' '.join(str(v or '') for v in r.values()).casefold()]

    def accounts(self, query='', status='Todas', condo_id=None, category_id=None,
                 supplier_id=None, month=None, year=None, start=None, end=None,
                 alerts=False, today=None):
        today = today or date.today()
        result = []
        for original in self.snapshot['accounts']:
            a = copy.deepcopy(original)
            days = (a['data_vencimento'] - today).days
            a['dias'] = days
            if a['status'] not in ('Paga', 'Cancelada'):
                a['status'] = 'Vencida' if days < 0 else 'Vence hoje' if days == 0 else 'Próxima do vencimento' if days <= 7 else 'Pendente'
            if any(selected and a[key] != selected for key, selected in
                   [('condominio_id', condo_id), ('categoria_id', category_id), ('fornecedor_id', supplier_id)]):
                continue
            due = a['data_vencimento']
            if month and due.month != month or year and due.year != year:
                continue
            if start and due < start or end and due > end:
                continue
            wanted = STATUS_FILTER.get(status, status)
            if wanted != 'Todas' and a['status'] != wanted:
                continue
            if alerts and (a['status'] in ('Paga', 'Cancelada') or days > 7):
                continue
            if query.casefold() not in ' '.join(str(a.get(k) or '') for k in
                ('condominio','fornecedor','categoria','nome','numero_documento','descricao')).casefold():
                continue
            result.append(a)
        return result

    def history(self, start=None, end=None, include_reversed=True):
        return [copy.deepcopy(a) for a in self.snapshot['history']
            if (not start or a['payment']['data_pagamento'] >= start)
            and (not end or a['payment']['data_pagamento'] <= end)
            and (include_reversed or not a['payment']['estornado_em'])]

    def audit(self):
        return copy.deepcopy(self.snapshot['audit'])

    def generate_recurring(self, today=None):
        pass  # Server scheduler owns recurrence generation.

    def mutate(self, method, *args, **kwargs):
        from app.widgets.network import wait_for
        if not self.online:
            raise ValueError('Conexão indisponível. Atualize os dados antes de salvar.')
        body = {'method': method, 'args': args, 'kwargs': kwargs,
                'revision': self.snapshot['revision'], 'request_id': str(uuid.uuid4())}
        # Reuse the same key after an ambiguous response; the server receipt is atomic.
        signature = json.dumps(encode({k:v for k,v in body.items() if k != 'request_id'}), sort_keys=True)
        if self.pending and self.pending[0] == signature:
            body['request_id'] = self.pending[1]
        self.pending = (signature, body['request_id'])
        result = wait_for(lambda: self.client.request('/v1/mutate', body))
        self.pending = None
        # Do not turn a successful write into a failed form because refresh failed.
        try:
            self.snapshot = wait_for(lambda: self.client.request('/v1/snapshot'))
        except ValueError:
            self.online = False
        return result['result']

    def save_entity(self, kind, values, entity_id=None):
        return self.mutate('save_entity', kind, values, entity_id)

    def delete_entity(self, kind, entity_id):
        return self.mutate('delete_entity', kind, entity_id)

    def save_account(self, values, account_id=None, months=0):
        return self.mutate('save_account', values, account_id, months)

    def pay(self, account_id, values):
        return self.mutate('pay', account_id, values)

    def undo_payment(self, account_id):
        return self.mutate('undo_payment', account_id)

    def delete_account(self, account_id):
        return self.mutate('delete_account', account_id)

    def stop_recurrence(self, account_id):
        return self.mutate('stop_recurrence', account_id)

    def cancel_account(self, account_id):
        return self.mutate('cancel_account', account_id)
