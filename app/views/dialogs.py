from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QDialogButtonBox,
    QMessageBox,
    QScrollArea,
    QWidget,
    QTabWidget,
)
from app.widgets.common import MoneyEdit, DateEdit, button, label, DataTable, confirm
from app.utils.formatting import money, fmt_date, days_text, RECURRENCES
from app.widgets.form_page import FormPage, begin_form, section, field, finish_form

FIELDS = {
    "condominios": [
        ("nome", "Nome"),
        ("cnpj", "CNPJ"),
        ("endereco", "Endereço"),
        ("cidade", "Cidade"),
        ("sindico", "Síndico"),
        ("telefone", "Telefone"),
        ("email", "E-mail"),
        ("observacoes", "Observações"),
    ],
    "fornecedores": [
        ("nome", "Nome"),
        ("cnpj_cpf", "CNPJ / CPF"),
        ("telefone", "Telefone"),
        ("email", "E-mail"),
    ],
    "categorias": [("nome", "Nome da categoria")],
}


class EntityDialog(FormPage):
    def __init__(self, finance, kind, values=None, parent=None):
        super().__init__(parent)
        finance = finance.for_form() if getattr(finance, "remote", False) else finance
        self.finance, self.kind, self.original = finance, kind, values or {}
        self.fields = {}
        noun = {
            "condominios": "condomínio",
            "fornecedores": "fornecedor",
            "categorias": "categoria",
        }[kind]
        outer, body = begin_form(
            self,
            ("Editar " if values else "Cadastrar ") + noun,
            "Preencha os dados abaixo. As informações ficam salvas no aplicativo.",
        )
        grid = section(body, "Dados do cadastro")
        for i, (key, title) in enumerate(FIELDS[kind]):
            edit = QTextEdit() if key == "observacoes" else QLineEdit()
            if key == "observacoes":
                edit.setFixedHeight(90)
                edit.setPlainText(self.original.get(key) or "")
            else:
                if key == "cnpj":
                    edit.setInputMask("00.000.000/0000-00;_")
                if key == "cnpj_cpf":
                    edit.textEdited.connect(
                        lambda text, e=edit: self.format_taxid(e, text)
                    )
                edit.setText(self.original.get(key) or "")
                edit.setMaxLength(300 if key == "endereco" else 200)
                edit.setPlaceholderText(
                    {
                        "nome": (
                            "Ex.: Residencial Aurora"
                            if kind == "condominios"
                            else "Informe o nome"
                        ),
                        "email": "nome@empresa.com.br",
                        "telefone": "(47) 99999-9999",
                        "endereco": "Rua, número e bairro",
                        "cidade": "Cidade / UF",
                        "sindico": "Nome do síndico",
                    }.get(key, "")
                )
            self.fields[key] = edit
            field(grid, title + (" *" if key == "nome" else ""), edit, i // 2, i % 2)
        body.addStretch()
        finish_form(self, outer, "Salvar cadastro", self.save)

    @staticmethod
    def format_taxid(edit, text):
        digits = "".join(c for c in text if c.isdigit())[:14]
        if len(digits) <= 11:
            formatted = (
                digits[:3]
                + ("." + digits[3:6] if len(digits) > 3 else "")
                + ("." + digits[6:9] if len(digits) > 6 else "")
                + ("-" + digits[9:] if len(digits) > 9 else "")
            )
        else:
            formatted = (
                digits[:2]
                + "."
                + digits[2:5]
                + "."
                + digits[5:8]
                + "/"
                + digits[8:12]
                + ("-" + digits[12:] if len(digits) > 12 else "")
            )
        edit.setText(formatted)

    def save(self):
        try:
            values = {
                key: (e.toPlainText() if isinstance(e, QTextEdit) else e.text()).strip()
                for key, e in self.fields.items()
            }
            for key, lengths in [("cnpj", (14,)), ("cnpj_cpf", (11, 14))]:
                if key in values:
                    digits = "".join(c for c in values[key] if c.isdigit())
                    if not digits:
                        values[key] = ""
                    elif len(digits) not in lengths:
                        raise ValueError(
                            "Informe o documento completo ou deixe-o vazio."
                        )
            self.saved_id = self.finance.save_entity(
                self.kind, values, self.original.get("id")
            )
            self.accept()
        except Exception as exc:
            self.show_error(str(exc))


class AccountDialog(FormPage):
    def __init__(
        self, finance, values=None, parent=None, duplicate=False, condo_id=None
    ):
        super().__init__(parent)
        finance = finance.for_form() if getattr(finance, "remote", False) else finance
        self.finance, self.original, self.duplicate = finance, values or {}, duplicate
        title = (
            "Duplicar conta"
            if duplicate
            else "Editar conta" if values else "Nova conta a pagar"
        )
        outer, body = begin_form(
            self, title, "Organize a despesa, o vencimento e os dados para pagamento."
        )
        self.fields = {}
        identification = section(body, "Identificação da despesa")
        payment = section(body, "Valores e vencimento")
        details = section(
            body,
            "Documentos e observações",
            "Informações complementares para localizar e conferir a conta.",
        )
        positions = {
            "condominio_id": (0, 0),
            "fornecedor_id": (1, 0),
            "categoria_id": (1, 1),
        }
        for key, kind, title in [
            ("condominio_id", "condominios", "Condomínio *"),
            ("fornecedor_id", "fornecedores", "Fornecedor"),
            ("categoria_id", "categorias", "Categoria *"),
        ]:
            combo = QComboBox()
            self.fields[key] = combo
            self.fill_combo(
                combo,
                kind,
                self.original.get(key, condo_id if key == "condominio_id" else None),
                key == "fornecedor_id",
            )
            row = QHBoxLayout()
            row.addWidget(combo, 1)
            row.addWidget(
                button(
                    "+ Novo",
                    lambda checked=False, k=kind, c=combo: self.quick_entity(k, c),
                )
            )
            r, c = positions[key]
            field(identification, title, row, r, c)
        for key, title in [
            ("nome", "Nome da despesa *"),
            ("descricao", "Descrição"),
            ("valor_centavos", "Valor da conta *"),
            ("data_emissao", "Data de emissão *"),
            ("data_vencimento", "Data de vencimento *"),
            ("forma_pagamento", "Forma de pagamento"),
            ("codigo_barras", "Código de barras"),
            ("numero_documento", "Número do documento"),
            ("observacoes", "Observações"),
        ]:
            value = self.original.get(key)
            if key == "valor_centavos":
                edit = MoneyEdit(value or 0)
            elif key.startswith("data_"):
                edit = DateEdit(value)
            elif key in ("descricao", "observacoes"):
                edit = QTextEdit()
                edit.setFixedHeight(76)
                edit.setPlainText(value or "")
            elif key == "forma_pagamento":
                edit = QComboBox()
                edit.setEditable(True)
                edit.addItems(
                    [
                        "",
                        "PIX",
                        "Boleto",
                        "Transferência",
                        "Débito automático",
                        "Dinheiro",
                        "Cartão",
                    ]
                )
                edit.setCurrentText(value or "")
            else:
                edit = QLineEdit()
                edit.setMaxLength(
                    100 if key in ("codigo_barras", "numero_documento") else 200
                )
                edit.setText(
                    ""
                    if duplicate and key in ("codigo_barras", "numero_documento")
                    else value or ""
                )
            self.fields[key] = edit
            if key == "nome":
                edit.setPlaceholderText("Ex.: Energia elétrica — outubro")
                field(identification, title, edit, 0, 1)
            elif key in (
                "valor_centavos",
                "forma_pagamento",
                "data_emissao",
                "data_vencimento",
            ):
                r, c = {
                    "valor_centavos": (0, 0),
                    "forma_pagamento": (0, 1),
                    "data_emissao": (1, 0),
                    "data_vencimento": (1, 1),
                }[key]
                field(payment, title, edit, r, c)
            else:
                r, c = {
                    "numero_documento": (0, 0),
                    "codigo_barras": (0, 1),
                    "descricao": (1, 0),
                    "observacoes": (1, 1),
                }[key]
                field(details, title, edit, r, c)
        self.recurrence = QComboBox()
        for name, months in RECURRENCES.items():
            self.recurrence.addItem(name, months)
        self.recurrence.setCurrentIndex(
            max(
                0,
                self.recurrence.findData(
                    0 if duplicate else self.original.get("meses", 0)
                ),
            )
        )
        field(payment, "Repetir esta despesa", self.recurrence, 2, 0)
        note = label(
            "O próximo lançamento é criado automaticamente. Documentos e boletos devem ser conferidos a cada vencimento.",
            "muted",
        )
        note.setWordWrap(True)
        payment.addWidget(note, 2, 1)
        body.addStretch()
        finish_form(self, outer, "Salvar conta", self.save)

    def fill_combo(self, combo, kind, selected=None, optional=False):
        combo.clear()
        if optional:
            combo.addItem("Sem fornecedor", None)
        else:
            combo.addItem("Selecione...", None)
        for row in self.finance.entities(kind):
            combo.addItem(row["nome"], row["id"])
        combo.setCurrentIndex(max(0, combo.findData(selected)))

    def quick_entity(self, kind, combo):
        page = EntityDialog(self.finance, kind)

        def finished(result):
            if result:
                if getattr(self.finance, "remote", False):
                    self.finance.snapshot = page.finance.snapshot
                self.fill_combo(combo, kind, page.saved_id, kind == "fornecedores")

        self.window().open_form(page, finished)

    def save(self):
        try:
            values = {}
            for key, e in self.fields.items():
                if isinstance(e, MoneyEdit) or isinstance(e, DateEdit):
                    values[key] = e.value()
                elif isinstance(e, QTextEdit):
                    values[key] = e.toPlainText().strip()
                elif isinstance(e, QComboBox):
                    values[key] = (
                        e.currentData() if key.endswith("_id") else e.currentText()
                    )
                else:
                    values[key] = e.text().strip()
            values["cancelada"] = (
                False if self.duplicate else self.original.get("cancelada", False)
            )
            account_id = None if self.duplicate else self.original.get("id")
            self.finance.save_account(values, account_id, self.recurrence.currentData())
            self.accept()
        except Exception as exc:
            self.show_error(str(exc))


class PaymentDialog(FormPage):
    def __init__(self, finance, account, parent=None):
        super().__init__(parent)
        finance = finance.for_form() if getattr(finance, "remote", False) else finance
        self.finance, self.account = finance, account
        outer, body = begin_form(
            self, "Registrar pagamento", account["condominio"] + " • " + account["nome"]
        )
        form = section(
            body,
            "Dados do pagamento",
            "Valor lançado: " + money(account["valor_centavos"]),
        )
        self.date = DateEdit()
        self.amount = MoneyEdit(account["valor_centavos"])
        self.method = QComboBox()
        self.method.setEditable(True)
        self.method.addItems(
            [
                "PIX",
                "Boleto",
                "Transferência",
                "Débito automático",
                "Dinheiro",
                "Cartão",
            ]
        )
        self.method.setCurrentText(account["forma_pagamento"] or "PIX")
        self.proof = QLineEdit()
        self.notes = QTextEdit()
        self.notes.setFixedHeight(90)
        for i, (title, edit) in enumerate(
            [
                ("Data do pagamento *", self.date),
                ("Valor pago *", self.amount),
                ("Forma de pagamento", self.method),
                ("Número do comprovante", self.proof),
            ]
        ):
            field(form, title, edit, i // 2, i % 2)
        field(form, "Observação", self.notes, 2, 0, 2)
        body.addStretch()
        finish_form(self, outer, "Confirmar pagamento", self.save)

    def save(self):
        try:
            cents = self.amount.value()
            if cents != self.account["valor_centavos"] and not confirm(
                self,
                "O valor pago difere do valor lançado. Confirmar a quitação integral da conta com esse valor?",
            ):
                return
            self.finance.pay(
                self.account["id"],
                {
                    "data_pagamento": self.date.value(),
                    "valor_centavos": cents,
                    "forma_pagamento": self.method.currentText(),
                    "comprovante": self.proof.text(),
                    "observacoes": self.notes.toPlainText(),
                },
            )
            self.accept()
        except Exception as exc:
            self.show_error(str(exc))


class DetailsDialog(FormPage):
    def __init__(self, account, parent=None):
        super().__init__(parent)
        layout, body = begin_form(
            self, "Detalhes da conta", account["condominio"] + " • " + account["nome"]
        )
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        contents = QWidget()
        contents.setObjectName("detailCard")
        form = QFormLayout(contents)
        form.setContentsMargins(22, 22, 22, 22)
        form.setSpacing(14)
        form.setSpacing(12)
        values = [
            ("Condomínio", account["condominio"]),
            ("Despesa", account["nome"]),
            ("Fornecedor", account["fornecedor"]),
            ("Categoria", account["categoria"]),
            ("Descrição", account["descricao"]),
            ("Valor", money(account["valor_centavos"])),
            ("Emissão", fmt_date(account["data_emissao"])),
            ("Vencimento", fmt_date(account["data_vencimento"])),
            ("Prazo", days_text(account["data_vencimento"])),
            ("Status", account["status"]),
            ("Forma de pagamento", account["forma_pagamento"]),
            ("Código de barras", account["codigo_barras"]),
            ("Documento", account["numero_documento"]),
            ("Observações", account["observacoes"]),
            (
                "Recorrência",
                next(
                    (k for k, v in RECURRENCES.items() if v == account["meses"]),
                    "Não recorrente",
                ),
            ),
        ]
        if "pagamento" in account:
            p = account["pagamento"]
            values.extend(
                [
                    ("Data do pagamento", fmt_date(p["data_pagamento"])),
                    ("Valor pago", money(p["valor_centavos"])),
                    ("Comprovante", p["comprovante"]),
                    ("Observação de pagamento", p["observacoes"]),
                ]
            )
        for title, value in values:
            l = label(value or "—")
            l.setWordWrap(True)
            l.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            form.addRow(title, l)
        scroll.setWidget(contents)
        body.addWidget(scroll)
        layout.addWidget(button("Voltar à lista", self.reject))


class CondoDetailsDialog(FormPage):
    def __init__(self, finance, condo, parent=None):
        super().__init__(parent)
        layout, body = begin_form(
            self, condo["nome"], "Cadastro e movimentação financeira do condomínio"
        )
        tabs = QTabWidget()
        body.addWidget(tabs)
        tabs.setMinimumHeight(400)
        data = QWidget()
        data.setObjectName("detailCard")
        form = QFormLayout(data)
        form.setContentsMargins(22, 22, 22, 22)
        form.setSpacing(14)
        for key, title in FIELDS["condominios"]:
            l = label(condo.get(key) or "—")
            l.setWordWrap(True)
            form.addRow(title, l)
        tabs.addTab(data, "Cadastro")
        all_rows = finance.accounts(condo_id=condo["id"])
        groups = [
            (
                "Pendentes",
                [a for a in all_rows if a["status"] not in ("Paga", "Cancelada")],
            ),
            (
                "Próximos vencimentos",
                [
                    a
                    for a in all_rows
                    if a["status"] in ("Próxima do vencimento", "Vence hoje")
                ],
            ),
            ("Vencidas", [a for a in all_rows if a["status"] == "Vencida"]),
            ("Pagas", [a for a in all_rows if a["status"] == "Paga"]),
        ]
        for title, rows in groups:
            t = DataTable(
                ["Despesa", "Categoria", "Valor", "Vencimento", "Prazo", "Status"]
            )
            t.load(
                [
                    [
                        a["nome"],
                        a["categoria"],
                        money(a["valor_centavos"]),
                        fmt_date(a["data_vencimento"]),
                        days_text(a["data_vencimento"]),
                        a["status"],
                    ]
                    for a in rows
                ]
            )
            tabs.addTab(t, f"{title} ({len(rows)})")
        history = [a for a in finance.history() if a["condominio_id"] == condo["id"]]
        t = DataTable(["Despesa", "Pago", "Pagamento", "Forma", "Situação"])
        t.load(
            [
                [
                    a["nome"],
                    money(a["payment"]["valor_centavos"]),
                    fmt_date(a["payment"]["data_pagamento"]),
                    a["payment"]["forma_pagamento"],
                    "Estornado" if a["payment"]["estornado_em"] else "Confirmado",
                ]
                for a in history
            ]
        )
        tabs.addTab(t, "Histórico financeiro")
        layout.addWidget(button("Voltar à lista", self.reject))
