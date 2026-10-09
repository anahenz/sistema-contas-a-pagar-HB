import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import date

STATUSES = [
    "Todas",
    "Pendentes",
    "Próximas do vencimento",
    "Vencem hoje",
    "Vencidas",
    "Pagas",
    "Canceladas",
]
STATUS_FILTER = dict(
    zip(
        STATUSES[1:],
        [
            "Pendente",
            "Próxima do vencimento",
            "Vence hoje",
            "Vencida",
            "Paga",
            "Cancelada",
        ],
    )
)
RECURRENCES = {
    "Não recorrente": 0,
    "Mensal": 1,
    "Bimestral": 2,
    "Trimestral": 3,
    "Semestral": 6,
    "Anual": 12,
}


def money(cents):
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(int(cents)), 100)
    return f"R$ {sign}{whole:,}".replace(",", ".") + f",{frac:02d}"


def parse_money(value):
    raw = str(value).replace("R$", "").replace(" ", "")
    if not re.fullmatch(r"(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+)(?:,[0-9]{1,2})?", raw):
        raise ValueError(
            "Informe o valor no formato 1.250,00, com até duas casas decimais."
        )
    cleaned = raw.replace(".", "").replace(",", ".")
    try:
        amount = Decimal(cleaned)
        if not amount.is_finite() or amount < 0 or amount > Decimal("999999999.99"):
            raise ValueError("Informe um valor entre zero e R$ 999.999.999,99.")
        return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except InvalidOperation as exc:
        raise ValueError("Informe o valor no formato 1.250,00.") from exc


def fmt_date(value):
    return value.strftime("%d/%m/%Y") if value else "—"


def days_text(due, today=None):
    days = (due - (today or date.today())).days
    return (
        "Hoje"
        if days == 0
        else f"{days} dia(s)" if days > 0 else f"Atrasada há {-days} dia(s)"
    )


def account_status(account, paid=False, today=None):
    if paid:
        return "Paga"
    if account.cancelada:
        return "Cancelada"
    days = (account.data_vencimento - (today or date.today())).days
    if days < 0:
        return "Vencida"
    if days == 0:
        return "Vence hoje"
    if days <= 7:
        return "Próxima do vencimento"
    return "Pendente"
