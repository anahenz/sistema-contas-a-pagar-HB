import calendar
from datetime import date
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QFileDialog,
    QMessageBox,
    QCheckBox,
    QFrame,
)
from app.widgets.common import DateEdit, DataTable, label, button
from app.utils.formatting import money, fmt_date


class HistoryPage(QWidget):
    def __init__(self, finance):
        super().__init__()
        self.finance = finance
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label("Histórico de pagamentos", "heading"))
        layout.setSpacing(16)
        layout.addWidget(
            label(
                "Consulte pagamentos confirmados, estornos e alterações nos registros.",
                "muted",
            )
        )
        filter_card = QFrame()
        filter_card.setObjectName("filterCard")
        row = QHBoxLayout(filter_card)
        row.setContentsMargins(18, 14, 18, 14)
        row.setSpacing(18)
        self.start = DateEdit(date(date.today().year, 1, 1))
        self.end = DateEdit()
        self.start.setFixedWidth(150)
        self.end.setFixedWidth(150)
        for title, edit in [("Data inicial", self.start), ("Data final", self.end)]:
            block = QVBoxLayout()
            block.setSpacing(6)
            block.addWidget(label(title, "fieldLabel"))
            block.addWidget(edit)
            row.addLayout(block)
        self.all = QCheckBox("Todos os períodos")
        self.all.setChecked(True)
        row.addWidget(self.all)
        row.addStretch()
        row.addWidget(button("Aplicar período", self.refresh, True))
        layout.addWidget(filter_card)
        self.tabs = QTabWidget()
        self.table = DataTable(
            [
                "Condomínio",
                "Conta",
                "Categoria",
                "Fornecedor",
                "Valor pago",
                "Vencimento",
                "Pagamento",
                "Forma",
                "Comprovante",
                "Situação",
            ]
        )
        self.tabs.addTab(self.table, "Pagamentos")
        self.audit_table = DataTable(["Data/hora", "Ação", "Detalhes"])
        self.audit_table.setColumnWidth(2, 650)
        self.tabs.addTab(self.audit_table, "Registro de alterações")
        layout.addWidget(self.tabs, 1)
        self.footer = label("", "muted")
        layout.addWidget(self.footer)
        self.all.toggled.connect(self.enable_dates)
        self.enable_dates()

    def enable_dates(self):
        self.start.setEnabled(not self.all.isChecked())
        self.end.setEnabled(not self.all.isChecked())

    def refresh(self):
        if not self.all.isChecked() and self.start.value() > self.end.value():
            QMessageBox.warning(
                self, "Período inválido", "A data inicial deve ser anterior à final."
            )
            return
        rows = self.finance.history(
            None if self.all.isChecked() else self.start.value(),
            None if self.all.isChecked() else self.end.value(),
        )
        self.table.load(
            [
                [
                    a["condominio"],
                    a["nome"],
                    a["categoria"],
                    a["fornecedor"],
                    money(a["payment"]["valor_centavos"]),
                    fmt_date(a["data_vencimento"]),
                    fmt_date(a["payment"]["data_pagamento"]),
                    a["payment"]["forma_pagamento"],
                    a["payment"]["comprovante"],
                    "Estornado" if a["payment"]["estornado_em"] else "Confirmado",
                ]
                for a in rows
            ]
        )
        self.audit_table.load(
            [
                [r["data"].strftime("%d/%m/%Y %H:%M:%S"), r["acao"], r["detalhes"]]
                for r in self.finance.audit()
            ]
        )
        self.footer.setText(
            f'{len(rows)} pagamento(s) • Total confirmado: {money(sum(a["payment"]["valor_centavos"] for a in rows if not a["payment"]["estornado_em"]))} • Registro de alterações: últimos 1.000 eventos'
        )


class ReportsPage(QWidget):
    def __init__(self, reports):
        super().__init__()
        self.reports = reports
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(label("Relatórios financeiros", "heading"))
        layout.addWidget(
            label(
                "Lançamentos por data de vencimento. Pagamentos por data de pagamento, excluindo estornos.",
                "muted",
            )
        )
        today = date.today()
        row = QHBoxLayout()
        self.start = DateEdit(date(today.year, today.month, 1))
        self.end = DateEdit(
            date(
                today.year, today.month, calendar.monthrange(today.year, today.month)[1]
            )
        )
        for w in (
            label("De"),
            self.start,
            label("Até"),
            self.end,
            button("Gerar relatório", self.refresh, True),
        ):
            row.addWidget(w)
        row.addStretch()
        row.addWidget(button("Exportar Excel", lambda: self.export("excel")))
        row.addWidget(button("Exportar PDF", lambda: self.export("pdf")))
        layout.addLayout(row)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

    def refresh(self):
        try:
            data = self.reports.report(self.start.value(), self.end.value())
            self.tabs.clear()
            for title, rows in data.items():
                table = DataTable(rows[0])
                table.load(rows[1:])
                table.setColumnWidth(0, 280)
                self.tabs.addTab(table, title)
        except Exception as exc:
            QMessageBox.warning(self, "Relatório não gerado", str(exc))

    def export(self, kind):
        extension = "xlsx" if kind == "excel" else "pdf"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar relatório",
            f"Relatorio_{self.start.value():%Y%m%d}_{self.end.value():%Y%m%d}.{extension}",
            f"Arquivo {extension.upper()} (*.{extension})",
        )
        if not path:
            return
        if not path.lower().endswith("." + extension):
            path += "." + extension
        try:
            getattr(self.reports, kind)(path, self.start.value(), self.end.value())
            QMessageBox.information(
                self, "Relatório exportado", f"Arquivo salvo em:\n{path}"
            )
        except Exception as exc:
            QMessageBox.warning(self, "Falha ao exportar", str(exc))
