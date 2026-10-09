from datetime import date, timedelta
import pytest
from sqlalchemy import select
from app.database.connection import Database
from app.services.finance import FinanceService, add_months
from app.utils.formatting import parse_money, money
from app.models.entities import Notificacao, Conta, Recorrencia


@pytest.mark.parametrize(
    "days,status",
    [
        (-1, "Vencida"),
        (0, "Vence hoje"),
        (1, "Próxima do vencimento"),
        (7, "Próxima do vencimento"),
        (8, "Pendente"),
    ],
)
def test_status_and_alert_boundaries(finance, days, status):
    aid = finance.save_account(
        finance.sample | {"data_vencimento": date.today() + timedelta(days=days)}
    )
    assert finance.account(aid)["status"] == status
    assert bool(finance.accounts(alerts=True)) == (days <= 7)


def test_crud_persists_and_filters(finance):
    aid = finance.save_account(finance.sample)
    other = FinanceService(Database(finance.db.path))
    assert other.account(aid)["valor_centavos"] == 125000
    finance.save_account(finance.sample | {"nome": "Energia alterada"}, aid)
    assert finance.accounts(query="alterada")[0]["id"] == aid
    for query in ("Aurora", "Energia Sul", "Energia", "NF-100"):
        assert finance.accounts(query=query)
    assert not finance.accounts(query="inexistente")
    assert finance.accounts(
        condo_id=finance.sample["condominio_id"],
        category_id=finance.sample["categoria_id"],
        supplier_id=finance.sample["fornecedor_id"],
        month=finance.sample["data_vencimento"].month,
        year=finance.sample["data_vencimento"].year,
    )
    finance.delete_account(aid)
    assert finance.account(aid) is None
    other.db.engine.dispose()


def test_payment_undo_preserves_history_snapshot(finance):
    aid = finance.save_account(finance.sample)
    values = {
        "data_pagamento": date.today(),
        "valor_centavos": 124900,
        "forma_pagamento": "PIX",
        "comprovante": "ABC",
        "observacoes": "Desconto",
    }
    finance.pay(aid, values)
    assert finance.account(aid)["status"] == "Paga"
    assert not finance.accounts(alerts=True)
    with pytest.raises(ValueError):
        finance.pay(aid, values)
    with pytest.raises(ValueError):
        finance.save_account(finance.sample, aid)
    with pytest.raises(ValueError):
        finance.delete_account(aid)
    finance.undo_payment(aid)
    finance.save_account(finance.sample | {"nome": "Novo nome"}, aid)
    assert finance.history()[0]["nome"] == "Energia elétrica"
    assert finance.history()[0]["payment"]["estornado_em"]
    finance.pay(aid, values)
    assert len(finance.history()) == 2
    assert (
        sum(
            a["payment"]["valor_centavos"]
            for a in finance.history(include_reversed=False)
        )
        == 124900
    )
    assert finance.dashboard()["pago"] == 124900


def test_cancel_and_reactivate(finance):
    aid = finance.save_account(finance.sample)
    finance.cancel_account(aid)
    assert finance.account(aid)["status"] == "Cancelada"
    assert not finance.accounts(alerts=True)
    finance.cancel_account(aid)
    assert finance.account(aid)["status"] == "Próxima do vencimento"


def test_referenced_entity_cannot_be_deleted(finance):
    finance.save_account(finance.sample)
    with pytest.raises(ValueError):
        finance.delete_entity("condominios", finance.sample["condominio_id"])


def test_month_end_recurrence_is_idempotent(finance):
    aid = finance.save_account(
        finance.sample
        | {"data_emissao": date(2026, 1, 1), "data_vencimento": date(2026, 1, 31)},
        months=1,
    )
    finance.generate_recurring(date(2026, 3, 1))
    rows = finance.accounts()
    assert [a["data_vencimento"] for a in rows] == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
    ]
    finance.generate_recurring(date(2026, 3, 1))
    assert len(finance.accounts()) == 3
    assert finance.accounts()[1]["codigo_barras"] == ""
    feb = finance.accounts()[1]
    finance.save_account(
        {k: v for k, v in feb.items() if k in finance.sample}, feb["id"], months=1
    )
    finance.generate_recurring(date(2026, 5, 1))
    assert date(2026, 5, 31) in [a["data_vencimento"] for a in finance.accounts()]
    finance.stop_recurrence(aid)
    count = len(finance.accounts())
    finance.generate_recurring(date(2030, 1, 1))
    assert len(finance.accounts()) == count


@pytest.mark.parametrize("months", [1, 2, 3, 6, 12])
def test_recurrence_intervals(finance, months):
    due = date(2028, 2, 29)
    finance.save_account(
        finance.sample | {"data_emissao": date(2028, 2, 1), "data_vencimento": due},
        months=months,
    )
    assert finance.accounts()[1]["data_vencimento"] == add_months(due, months)


def test_category_deleted_is_not_reseeded(finance):
    category = next(c for c in finance.entities("categorias") if c["nome"] == "Água")
    finance.delete_entity("categorias", category["id"])
    db2 = Database(finance.db.path)
    assert len(FinanceService(db2).entities("categorias")) == 15
    db2.engine.dispose()


@pytest.mark.parametrize(
    "value,cents", [("1.250,00", 125000), ("0,01", 1), ("R$ 99,99", 9999), ("12", 1200)]
)
def test_money_roundtrip(value, cents):
    assert parse_money(value) == cents
    assert parse_money(money(cents)) == cents


def test_invalid_values(finance):
    for value in ("abc", "NaN", "-1", "Infinity"):
        with pytest.raises(ValueError):
            parse_money(value)
    with pytest.raises(ValueError):
        finance.save_account(finance.sample | {"valor_centavos": 0})
    with pytest.raises(ValueError):
        finance.save_account(finance.sample | {"data_emissao": date(2099, 1, 1)})


def test_malformed_money_is_rejected():
    for value in ("1.25", "1,234", "1.23.456", "1e3"):
        with pytest.raises(ValueError):
            parse_money(value)
