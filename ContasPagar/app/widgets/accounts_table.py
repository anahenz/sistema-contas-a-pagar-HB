from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu
from app.widgets.common import DataTable, button
from app.utils.formatting import money, fmt_date, days_text


class AccountsTable(DataTable):
    def __init__(self, actions, show_category=False):
        self.show_category = show_category
        super().__init__(
            [
                "Condomínio",
                "Despesa",
                "Categoria" if show_category else "Fornecedor",
                "Valor",
                "Vencimento",
                "Faltam",
                "Status",
                "Ações",
            ]
        )
        self.actions = actions
        self.rows = []
        self.cellDoubleClicked.connect(self.open_row)
        self.setColumnWidth(0, 170)
        self.setColumnWidth(1, 160)
        self.setColumnWidth(2, 130)
        self.setColumnWidth(3, 105)
        self.setColumnWidth(4, 105)
        self.setColumnWidth(5, 135)
        self.setColumnWidth(6, 175)
        self.setColumnWidth(7, 65)

    def set_accounts(self, rows):
        self.rows = rows
        self.load(
            [
                [
                    a["condominio"],
                    a["nome"],
                    a["categoria"] if self.show_category else a["fornecedor"],
                    money(a["valor_centavos"]),
                    fmt_date(a["data_vencimento"]),
                    (
                        "—"
                        if a["status"] in ("Paga", "Cancelada")
                        else (
                            f"Há {-a['dias']} dia(s)"
                            if a["dias"] < 0
                            else days_text(a["data_vencimento"])
                        )
                    ),
                    a["status"],
                    "",
                ]
                for a in rows
            ]
        )
        for i, a in enumerate(rows):
            self.item(i, 0).setData(Qt.ItemDataRole.UserRole, a["id"])
            b = button("⋯")
            b.setMaximumWidth(60)
            b.clicked.connect(
                lambda checked=False, account=a, widget=b: self.open_menu(
                    account, widget
                )
            )
            self.setCellWidget(i, 7, b)

    def open_menu(self, a, b):
        menu = QMenu(self)
        options = ["Visualizar", "Editar", "Duplicar"]
        if a["status"] == "Paga":
            options += ["Desfazer pagamento"]
        elif a["status"] == "Cancelada":
            options += ["Reativar conta"]
        else:
            options += ["Marcar como pago", "Cancelar conta"]
        if a.get("meses"):
            options += ["Encerrar recorrência"]
        options += ["Excluir"]
        for title in options:
            act = menu.addAction(title)
            act.triggered.connect(
                lambda checked=False, t=title, aid=a["id"]: self.actions.run(t, aid)
            )
        menu.exec(b.mapToGlobal(b.rect().bottomLeft()))

    def open_row(self, row, column):
        if self.item(row, 0):
            self.actions.run(
                "Visualizar", self.item(row, 0).data(Qt.ItemDataRole.UserRole)
            )
