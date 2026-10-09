from datetime import date
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QColor, QPainter, QTextCharFormat
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFrame,
    QComboBox,
    QLineEdit,
    QCalendarWidget,
    QSpinBox,
    QSizePolicy,
)
from app.widgets.common import label, button
from app.widgets.accounts_table import AccountsTable
from app.views.dialogs import AccountDialog
from app.utils.formatting import STATUSES, money


class DashboardPage(QWidget):
    def __init__(self, finance, actions, on_change):
        super().__init__()
        self.finance = finance
        self.on_change = on_change
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        heading = QHBoxLayout()
        text = QVBoxLayout()
        text.addWidget(label("Visão geral", "heading"))
        self.subtitle = label("", "muted")
        text.addWidget(self.subtitle)
        heading.addLayout(text)
        heading.addStretch()
        heading.addWidget(button("Nova conta", self.new_account, True))
        layout.addLayout(heading)
        cards = QGridLayout()
        cards.setSpacing(12)
        self.metrics = {}
        for i, (key, title) in enumerate(
            [
                ("contas_mes", "Contas com vencimento no mês"),
                ("a_pagar", "A pagar no mês"),
                ("pago", "Pago neste mês"),
                ("condominios", "Condomínios"),
                ("pendentes", "Pendentes • todos os períodos"),
                ("vencidas", "Vencidas"),
                ("hoje", "Vencem hoje"),
                ("proximas", "Vencem em até 7 dias"),
            ]
        ):
            frame = QFrame()
            frame.setObjectName("card")
            frame.setMaximumHeight(102)
            box = QVBoxLayout(frame)
            box.setContentsMargins(16, 12, 16, 12)
            box.addWidget(label(title, "muted"))
            metric = label("0", "metric")
            box.addWidget(metric)
            self.metrics[key] = metric
            cards.addWidget(frame, i // 4, i % 4)
        layout.addLayout(cards)
        row = QHBoxLayout()
        row.addWidget(label("Próximos vencimentos", "heading"))
        row.addStretch()
        row.addWidget(label("Inclui contas em atraso • até 30 dias à frente", "muted"))
        layout.addLayout(row)
        self.table = AccountsTable(actions, True)
        layout.addWidget(self.table, 1)
        self.empty = label(
            "Cadastre um condomínio e adicione a primeira conta para começar.", "muted"
        )
        layout.addWidget(self.empty)

    def new_account(self):
        self.window().open_form(AccountDialog(self.finance))

    def refresh(self):
        today = date.today()
        self.subtitle.setText(f"Acompanhamento financeiro • {today:%d/%m/%Y}")
        data = self.finance.dashboard()
        for key, val in data.items():
            self.metrics[key].setText(
                money(val) if key in ("a_pagar", "pago") else str(val)
            )
        rows = [
            a
            for a in self.finance.accounts()
            if a["status"] not in ("Paga", "Cancelada") and a["dias"] <= 30
        ]
        self.table.set_accounts(rows)
        self.empty.setVisible(not rows)


class AccountsPage(QWidget):
    def __init__(self, finance, actions, on_change):
        super().__init__()
        self.finance = finance
        self.on_change = on_change
        self.only_alerts = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        row = QHBoxLayout()
        self.title = label("Contas a Pagar", "heading")
        row.addWidget(self.title)
        row.addStretch()
        row.addWidget(button("Limpar filtros", self.clear_filters))
        row.addWidget(button("Nova conta", self.new_account, True))
        layout.addLayout(row)
        self.search = QLineEdit()
        self.search.setPlaceholderText(
            "Pesquisar condomínio, fornecedor, despesa, categoria ou documento"
        )
        layout.addWidget(self.search)
        self.delay = QTimer(self)
        self.delay.setSingleShot(True)
        self.delay.setInterval(180)
        self.delay.timeout.connect(self.reload)
        self.search.textChanged.connect(lambda: self.delay.start())
        filters = QGridLayout()
        self.status = QComboBox()
        self.status.addItems(STATUSES)
        self.condo = QComboBox()
        self.category = QComboBox()
        self.supplier = QComboBox()
        self.month = QComboBox()
        self.year = QComboBox()
        self.month.addItem("Todos os meses", None)
        for i, name in enumerate(
            [
                "Janeiro",
                "Fevereiro",
                "Março",
                "Abril",
                "Maio",
                "Junho",
                "Julho",
                "Agosto",
                "Setembro",
                "Outubro",
                "Novembro",
                "Dezembro",
            ],
            1,
        ):
            self.month.addItem(name, i)
        for i, (name, combo) in enumerate(
            [
                ("Situação", self.status),
                ("Condomínio", self.condo),
                ("Categoria", self.category),
                ("Fornecedor", self.supplier),
                ("Mês", self.month),
                ("Ano", self.year),
            ]
        ):
            box = QVBoxLayout()
            box.addWidget(label(name, "muted"))
            box.addWidget(combo)
            filters.addLayout(box, i // 3, i % 3)
            combo.currentIndexChanged.connect(self.reload)
        layout.addLayout(filters)
        self.table = AccountsTable(actions)
        layout.addWidget(self.table, 1)
        self.footer = label("", "muted")
        layout.addWidget(self.footer)

    def new_account(self):
        self.window().open_form(
            AccountDialog(self.finance, condo_id=self.condo.currentData())
        )

    def fill(self, combo, kind, first):
        selected = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(first, None)
        for e in self.finance.entities(kind):
            combo.addItem(e["nome"], e["id"])
        combo.setCurrentIndex(max(0, combo.findData(selected)))
        combo.blockSignals(False)

    def refresh(self):
        self.fill(self.condo, "condominios", "Todos os condomínios")
        self.fill(self.category, "categorias", "Todas as categorias")
        self.fill(self.supplier, "fornecedores", "Todos os fornecedores")
        selected = self.year.currentData()
        years = {date.today().year}
        years.update(a["data_vencimento"].year for a in self.finance.accounts())
        self.year.blockSignals(True)
        self.year.clear()
        self.year.addItem("Todos os anos", None)
        for y in sorted(years):
            self.year.addItem(str(y), y)
        self.year.setCurrentIndex(max(0, self.year.findData(selected)))
        self.year.blockSignals(False)
        self.reload()

    def reload(self):
        rows = self.finance.accounts(
            query=self.search.text(),
            status=self.status.currentText() or "Todas",
            condo_id=self.condo.currentData(),
            category_id=self.category.currentData(),
            supplier_id=self.supplier.currentData(),
            month=self.month.currentData(),
            year=self.year.currentData(),
            alerts=self.only_alerts,
        )
        self.table.set_accounts(rows)
        pending = sum(
            a["valor_centavos"]
            for a in rows
            if a["status"] not in ("Paga", "Cancelada")
        )
        self.footer.setText(
            f"{len(rows)} conta(s) • Pendente no resultado: {money(pending)}"
            + (" • Nenhuma conta encontrada" if not rows else "")
        )
        self.title.setText(
            "Central de alertas" if self.only_alerts else "Contas a Pagar"
        )

    def clear_filters(self):
        self.only_alerts = False
        self.search.clear()
        for c in (
            self.status,
            self.condo,
            self.category,
            self.supplier,
            self.month,
            self.year,
        ):
            c.blockSignals(True)
            c.setCurrentIndex(0)
            c.blockSignals(False)
        self.reload()

    def show_alerts(self):
        self.clear_filters()
        self.only_alerts = True
        self.reload()


class DueCalendar(QCalendarWidget):
    def __init__(self):
        super().__init__()
        self.indicators = {}
        self.setGridVisible(False)
        self.setNavigationBarVisible(False)
        self.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        weekday = QTextCharFormat()
        weekday.setForeground(QColor("#64748B"))
        weekday.setBackground(QColor("#F8FAFC"))
        self.setHeaderTextFormat(weekday)
        for day in (Qt.DayOfWeek.Saturday, Qt.DayOfWeek.Sunday):
            weekend = QTextCharFormat()
            weekend.setForeground(QColor("#64748B"))
            self.setWeekdayTextFormat(day, weekend)
        self.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )

    def paintCell(self, painter, rect, day):
        super().paintCell(painter, rect, day)
        key = day.toPython()
        if key in self.indicators:
            colors = self.indicators[key]
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            for i, color in enumerate(colors[:3]):
                painter.setBrush(QColor(color))
                painter.drawEllipse(
                    rect.center().x() - 4 + (i - (min(3, len(colors)) - 1) / 2) * 10,
                    rect.bottom() - 10,
                    5,
                    5,
                )
            painter.restore()


class CalendarPage(QWidget):
    def __init__(self, finance, actions):
        super().__init__()
        self.finance = finance
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label("Calendário de vencimentos", "heading"))
        layout.addWidget(
            label(
                "Azul: pendente • Laranja: próximo/hoje • Vermelho: vencida • Verde: paga • Cinza: cancelada",
                "muted",
            )
        )
        self.calendar = DueCalendar()
        navigation = QHBoxLayout()
        self.month_picker = QComboBox()
        self.month_picker.addItems(
            [
                "Janeiro",
                "Fevereiro",
                "Março",
                "Abril",
                "Maio",
                "Junho",
                "Julho",
                "Agosto",
                "Setembro",
                "Outubro",
                "Novembro",
                "Dezembro",
            ]
        )
        self.year_picker = QSpinBox()
        self.year_picker.setRange(1900, 9999)
        self.month_picker.setCurrentIndex(date.today().month - 1)
        self.year_picker.setValue(date.today().year)
        navigation.addWidget(self.month_picker)
        navigation.addWidget(self.year_picker)
        navigation.addStretch()
        navigation.addWidget(
            button("Hoje", lambda: self.calendar.setSelectedDate(QDate.currentDate()))
        )
        previous = button("‹", self.calendar.showPreviousMonth)
        previous.setToolTip("Mês anterior")
        following = button("›", self.calendar.showNextMonth)
        following.setToolTip("Próximo mês")
        navigation.addWidget(previous)
        navigation.addWidget(following)
        layout.addLayout(navigation)
        self.month_picker.currentIndexChanged.connect(self.choose_month)
        self.year_picker.valueChanged.connect(self.choose_month)
        self.calendar.setMaximumHeight(330)
        self.calendar.setMinimumHeight(260)
        layout.addWidget(self.calendar)
        self.calendar.selectionChanged.connect(self.reload)
        self.calendar.currentPageChanged.connect(self.update_month)
        self.date_label = label("", "heading")
        layout.addWidget(self.date_label)
        self.table = AccountsTable(actions, True)
        layout.addWidget(self.table, 1)

    def refresh(self):
        self.rows = self.finance.accounts()
        self.calendar.indicators = {}
        for a in self.rows:
            color = {
                "Paga": "#15803D",
                "Cancelada": "#9CA3AF",
                "Vencida": "#B91C1C",
                "Vence hoje": "#B45309",
                "Próxima do vencimento": "#B45309",
            }.get(a["status"], "#2563EB")
            colors = self.calendar.indicators.setdefault(a["data_vencimento"], [])
            if color not in colors:
                colors.append(color)
        self.calendar.updateCells()
        self.reload()

    def choose_month(self, *args):
        self.calendar.setCurrentPage(
            self.year_picker.value(), self.month_picker.currentIndex() + 1
        )

    def update_month(self, year, month):
        self.month_picker.blockSignals(True)
        self.year_picker.blockSignals(True)
        self.month_picker.setCurrentIndex(month - 1)
        self.year_picker.setValue(year)
        self.month_picker.blockSignals(False)
        self.year_picker.blockSignals(False)
        current = self.calendar.selectedDate()
        if current.year() != year or current.month() != month:
            self.calendar.setSelectedDate(QDate(year, month, 1))

    def reload(self):
        selected = self.calendar.selectedDate().toPython()
        self.date_label.setText(f"Vencimentos em {selected:%d/%m/%Y}")
        self.table.set_accounts(
            [a for a in getattr(self, "rows", []) if a["data_vencimento"] == selected]
        )
