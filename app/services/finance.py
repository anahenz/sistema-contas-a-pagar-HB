import calendar
import json
from datetime import date, datetime, timedelta
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from app.models.entities import (
    Condominio,
    Fornecedor,
    Categoria,
    Conta,
    Pagamento,
    Recorrencia,
    Auditoria,
    Notificacao,
)
from app.utils.formatting import account_status, STATUS_FILTER

ENTITY_MODELS = {
    "condominios": Condominio,
    "fornecedores": Fornecedor,
    "categorias": Categoria,
}
ACCOUNT_FIELDS = [
    "condominio_id",
    "fornecedor_id",
    "categoria_id",
    "nome",
    "descricao",
    "valor_centavos",
    "data_emissao",
    "data_vencimento",
    "forma_pagamento",
    "codigo_barras",
    "numero_documento",
    "observacoes",
    "cancelada",
]


def record(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def add_months(day, months, anchor=None):
    total = day.year * 12 + day.month - 1 + months
    year, month0 = divmod(total, 12)
    month = month0 + 1
    return date(
        year, month, min(anchor or day.day, calendar.monthrange(year, month)[1])
    )


class FinanceService:
    def __init__(self, db):
        self.db = db

    def entities(self, kind, query=""):
        model = ENTITY_MODELS[kind]
        with self.db.session() as s:
            rows = s.scalars(select(model).order_by(model.nome)).all()
            return [
                record(r)
                for r in rows
                if query.casefold()
                in " ".join(str(v or "") for v in record(r).values()).casefold()
            ]

    def save_entity(self, kind, values, entity_id=None):
        model = ENTITY_MODELS[kind]
        if not values.get("nome", "").strip():
            raise ValueError("O nome é obrigatório.")
        values["nome"] = values["nome"].strip()
        if values.get("email") and (
            "@" not in values["email"] or "." not in values["email"].split("@")[-1]
        ):
            raise ValueError("Informe um e-mail válido.")
        try:
            with self.db.session() as s:
                obj = s.get(model, entity_id) if entity_id else model()
                if obj is None:
                    raise ValueError("Cadastro não encontrado.")
                for key, val in values.items():
                    setattr(obj, key, val)
                s.add(obj)
                s.flush()
                s.add(
                    Auditoria(
                        acao="Editar cadastro" if entity_id else "Criar cadastro",
                        detalhes=f"{kind} #{obj.id}: {obj.nome}",
                    )
                )
                return obj.id
        except IntegrityError as exc:
            raise ValueError("Já existe uma categoria com este nome.") from exc

    def delete_entity(self, kind, entity_id):
        model = ENTITY_MODELS[kind]
        column = {
            "condominios": Conta.condominio_id,
            "fornecedores": Conta.fornecedor_id,
            "categorias": Conta.categoria_id,
        }[kind]
        with self.db.session() as s:
            obj = s.get(model, entity_id)
            if not obj:
                raise ValueError("Cadastro não encontrado.")
            if s.scalar(select(Conta.id).where(column == entity_id).limit(1)):
                raise ValueError(
                    "Este cadastro possui contas vinculadas. Reatribua ou exclua as contas sem histórico primeiro."
                )
            # Rules also reference entity identifiers in their saved template.
            for rule in s.scalars(select(Recorrencia)).all():
                key = {
                    "condominios": "condominio_id",
                    "fornecedores": "fornecedor_id",
                    "categorias": "categoria_id",
                }[kind]
                if json.loads(rule.modelo).get(key) == entity_id:
                    raise ValueError(
                        "Este cadastro está vinculado a uma série recorrente."
                    )
            s.add(
                Auditoria(
                    acao="Excluir cadastro", detalhes=f"{kind} #{obj.id}: {obj.nome}"
                )
            )
            s.delete(obj)

    def accounts(
        self,
        query="",
        status="Todas",
        condo_id=None,
        category_id=None,
        supplier_id=None,
        month=None,
        year=None,
        start=None,
        end=None,
        alerts=False,
        today=None,
    ):
        today = today or date.today()
        with self.db.session() as s:
            statement = (
                select(Conta, Condominio.nome, Fornecedor.nome, Categoria.nome)
                .join(Condominio, Conta.condominio_id == Condominio.id)
                .outerjoin(Fornecedor, Conta.fornecedor_id == Fornecedor.id)
                .join(Categoria, Conta.categoria_id == Categoria.id)
                .order_by(Conta.data_vencimento, Conta.id)
            )
            if condo_id:
                statement = statement.where(Conta.condominio_id == condo_id)
            if category_id:
                statement = statement.where(Conta.categoria_id == category_id)
            if supplier_id:
                statement = statement.where(Conta.fornecedor_id == supplier_id)
            if start:
                statement = statement.where(Conta.data_vencimento >= start)
            if end:
                statement = statement.where(Conta.data_vencimento <= end)
            payments = {
                p.conta_id: p
                for p in s.scalars(
                    select(Pagamento).where(Pagamento.estornado_em.is_(None))
                ).all()
            }
            rules = {r.id: r for r in s.scalars(select(Recorrencia)).all()}
            result = []
            for a, condo, supplier, category in s.execute(statement).all():
                data = record(a)
                data.update(
                    condominio=condo,
                    fornecedor=supplier or "—",
                    categoria=category,
                    status=account_status(a, a.id in payments, today),
                    dias=(a.data_vencimento - today).days,
                )
                rule = rules.get(a.recorrencia_id)
                data["meses"] = rule.meses if rule and rule.ativa else 0
                if a.id in payments:
                    data["pagamento"] = record(payments[a.id])
                wanted = STATUS_FILTER.get(status, status)
                if wanted != "Todas" and data["status"] != wanted:
                    continue
                if alerts and (
                    data["status"] in ("Paga", "Cancelada") or data["dias"] > 7
                ):
                    continue
                if month and a.data_vencimento.month != month:
                    continue
                if year and a.data_vencimento.year != year:
                    continue
                searchable = f"{condo} {supplier} {category} {a.nome} {a.numero_documento} {a.descricao}".casefold()
                if query.casefold() not in searchable:
                    continue
                result.append(data)
            return result

    def account(self, account_id):
        return next((a for a in self.accounts() if a["id"] == account_id), None)

    def save_account(self, values, account_id=None, months=0):
        if not values.get("nome", "").strip():
            raise ValueError("Informe o nome da despesa.")
        if values.get("valor_centavos", 0) <= 0:
            raise ValueError("O valor da conta deve ser maior que zero.")
        if values["data_emissao"] > values["data_vencimento"]:
            raise ValueError("A emissão não pode ser posterior ao vencimento.")
        if months not in (0, 1, 2, 3, 6, 12):
            raise ValueError("Recorrência inválida.")
        with self.db.session() as s:
            a = s.get(Conta, account_id) if account_id else Conta()
            if not a:
                raise ValueError("Conta não encontrada.")
            if account_id and s.scalar(
                select(Pagamento.id).where(
                    Pagamento.conta_id == account_id, Pagamento.estornado_em.is_(None)
                )
            ):
                raise ValueError("Desfaça o pagamento antes de editar a conta.")
            previous_due = a.data_vencimento
            for key in ACCOUNT_FIELDS:
                if key in values:
                    setattr(a, key, values[key])
            if not s.get(Condominio, a.condominio_id) or not s.get(
                Categoria, a.categoria_id
            ):
                raise ValueError("Selecione condomínio e categoria válidos.")
            if a.fornecedor_id and not s.get(Fornecedor, a.fornecedor_id):
                raise ValueError("Fornecedor inválido.")
            s.add(a)
            s.flush()
            template = {key: getattr(a, key) for key in ACCOUNT_FIELDS}
            template["cancelada"] = False
            template["data_emissao"] = a.data_emissao.isoformat()
            template["data_vencimento"] = a.data_vencimento.isoformat()
            rule = s.get(Recorrencia, a.recorrencia_id) if a.recorrencia_id else None
            if rule:
                rule.ativa = bool(months)
                if months:
                    rule.modelo = json.dumps(template, ensure_ascii=False)
                    if previous_due != a.data_vencimento:
                        rule.dia_original = a.data_vencimento.day
                    if rule.meses != months or previous_due != a.data_vencimento:
                        last_due = max(
                            s.scalars(
                                select(Conta.data_vencimento).where(
                                    Conta.recorrencia_id == rule.id
                                )
                            ).all()
                        )
                        rule.proximo_vencimento = add_months(
                            last_due, months, rule.dia_original
                        )
                    rule.meses = months
            elif months:
                rule = Recorrencia(
                    meses=months,
                    dia_original=a.data_vencimento.day,
                    proximo_vencimento=add_months(a.data_vencimento, months),
                    modelo=json.dumps(template, ensure_ascii=False),
                )
                s.add(rule)
                s.flush()
                a.recorrencia_id = rule.id
                self._generate_one(s, rule)  # The next launch is created immediately.
            s.add(
                Auditoria(
                    acao="Editar conta" if account_id else "Criar conta",
                    detalhes=f"Conta #{a.id}: {a.nome}",
                )
            )
            return a.id

    def _generate_one(self, s, rule):
        due = rule.proximo_vencimento
        found = s.scalar(
            select(Conta.id).where(
                Conta.recorrencia_id == rule.id, Conta.data_vencimento == due
            )
        )
        if not found:
            data = json.loads(rule.modelo)
            original_due = date.fromisoformat(data["data_vencimento"])
            original_issue = date.fromisoformat(data["data_emissao"])
            data["data_vencimento"] = due
            data["data_emissao"] = due - (original_due - original_issue)
            data["numero_documento"] = ""
            data["codigo_barras"] = ""
            s.add(Conta(**data, recorrencia_id=rule.id))
            s.add(
                Auditoria(
                    acao="Gerar recorrência",
                    detalhes=f"Série #{rule.id}: {due.isoformat()}",
                )
            )
        rule.proximo_vencimento = add_months(due, rule.meses, rule.dia_original)

    def generate_recurring(self, today=None):
        horizon = (today or date.today()) + timedelta(days=31)
        with self.db.session() as s:
            for rule in s.scalars(
                select(Recorrencia).where(Recorrencia.ativa.is_(True))
            ).all():
                while rule.proximo_vencimento <= horizon:
                    self._generate_one(s, rule)
                    s.flush()

    def pay(self, account_id, values):
        if values.get("valor_centavos", 0) <= 0:
            raise ValueError("O valor pago deve ser maior que zero.")
        if values["data_pagamento"] > date.today():
            raise ValueError("O pagamento não pode estar no futuro.")
        with self.db.session() as s:
            a = s.get(Conta, account_id)
            if not a or a.cancelada:
                raise ValueError("Conta inexistente ou cancelada.")
            if s.scalar(
                select(Pagamento.id).where(
                    Pagamento.conta_id == account_id, Pagamento.estornado_em.is_(None)
                )
            ):
                raise ValueError("Esta conta já está paga.")
            snapshot = {
                "condominio": s.get(Condominio, a.condominio_id).nome,
                "categoria": s.get(Categoria, a.categoria_id).nome,
                "fornecedor": (
                    s.get(Fornecedor, a.fornecedor_id).nome if a.fornecedor_id else "—"
                ),
                "nome": a.nome,
                "data_vencimento": a.data_vencimento.isoformat(),
            }
            s.add(
                Pagamento(
                    conta_id=account_id,
                    snapshot=json.dumps(snapshot, ensure_ascii=False),
                    **values,
                )
            )
            s.add(
                Auditoria(
                    acao="Registrar pagamento",
                    detalhes=f'Conta #{account_id}, {values["valor_centavos"]} centavos',
                )
            )

    def undo_payment(self, account_id):
        with self.db.session() as s:
            payment = s.scalar(
                select(Pagamento).where(
                    Pagamento.conta_id == account_id, Pagamento.estornado_em.is_(None)
                )
            )
            if not payment:
                raise ValueError("Não há pagamento ativo para desfazer.")
            payment.estornado_em = datetime.now()
            s.add(
                Auditoria(
                    acao="Desfazer pagamento",
                    detalhes=f"Conta #{account_id}, pagamento #{payment.id}",
                )
            )

    def delete_account(self, account_id):
        with self.db.session() as s:
            a = s.get(Conta, account_id)
            if not a:
                raise ValueError("Conta não encontrada.")
            if s.scalar(
                select(Pagamento.id).where(Pagamento.conta_id == account_id).limit(1)
            ):
                raise ValueError(
                    "Contas com histórico de pagamento são preservadas. Desfaça o pagamento e cancele a conta."
                )
            s.add(
                Auditoria(
                    acao="Excluir conta",
                    detalhes=json.dumps(record(a), default=str, ensure_ascii=False),
                )
            )
            s.delete(a)

    def stop_recurrence(self, account_id):
        with self.db.session() as s:
            a = s.get(Conta, account_id)
            rule = (
                s.get(Recorrencia, a.recorrencia_id) if a and a.recorrencia_id else None
            )
            if not rule:
                raise ValueError("Esta conta não possui série recorrente.")
            rule.ativa = False
            s.add(
                Auditoria(
                    acao="Encerrar recorrência",
                    detalhes=f"Série #{rule.id}; lançamentos existentes preservados",
                )
            )

    def cancel_account(self, account_id):
        with self.db.session() as s:
            a = s.get(Conta, account_id)
            if not a:
                raise ValueError("Conta não encontrada.")
            if s.scalar(
                select(Pagamento.id).where(
                    Pagamento.conta_id == account_id, Pagamento.estornado_em.is_(None)
                )
            ):
                raise ValueError("Desfaça o pagamento antes de cancelar.")
            a.cancelada = not a.cancelada
            s.add(
                Auditoria(
                    acao="Cancelar/reativar conta",
                    detalhes=f"Conta #{account_id}: cancelada={a.cancelada}",
                )
            )

    def history(self, start=None, end=None, include_reversed=True):
        accounts = {a["id"]: a for a in self.accounts()}
        with self.db.session() as s:
            statement = select(Pagamento).order_by(
                Pagamento.data_pagamento.desc(), Pagamento.id.desc()
            )
            if start:
                statement = statement.where(Pagamento.data_pagamento >= start)
            if end:
                statement = statement.where(Pagamento.data_pagamento <= end)
            if not include_reversed:
                statement = statement.where(Pagamento.estornado_em.is_(None))
            result = []
            for p in s.scalars(statement).all():
                saved = json.loads(p.snapshot)
                if saved.get("data_vencimento"):
                    saved["data_vencimento"] = date.fromisoformat(
                        saved["data_vencimento"]
                    )
                result.append(
                    dict(accounts[p.conta_id], **{"payment": record(p)}) | saved
                )
            return result

    def dashboard(self, today=None):
        today = today or date.today()
        rows = self.accounts(today=today)
        month = [
            a
            for a in rows
            if a["data_vencimento"].month == today.month
            and a["data_vencimento"].year == today.year
            and a["status"] != "Cancelada"
        ]
        pending = [a for a in rows if a["status"] not in ("Paga", "Cancelada")]
        paid = self.history(
            date(today.year, today.month, 1),
            date(
                today.year, today.month, calendar.monthrange(today.year, today.month)[1]
            ),
            False,
        )
        return {
            "contas_mes": len(month),
            "a_pagar": sum(a["valor_centavos"] for a in month if a["status"] != "Paga"),
            "pago": sum(a["payment"]["valor_centavos"] for a in paid),
            "pendentes": len(pending),
            "vencidas": sum(a["dias"] < 0 for a in pending),
            "hoje": sum(a["dias"] == 0 for a in pending),
            "proximas": sum(0 <= a["dias"] <= 7 for a in pending),
            "condominios": len(self.entities("condominios")),
        }

    def audit(self):
        with self.db.session() as s:
            return [
                record(r)
                for r in s.scalars(
                    select(Auditoria).order_by(Auditoria.id.desc()).limit(1000)
                ).all()
            ]
