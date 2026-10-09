from datetime import date
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QLineEdit,
    QSystemTrayIcon,
    QMenu,
    QApplication,
    QStyle,
    QMessageBox,
)
from app.controllers.actions import AccountActions
from app.services.finance import FinanceService
from app.services.backup import BackupService
from app.services.reports import ReportService
from app.services.notifications import NotificationService
from app.widgets.common import label, button, app_icon, confirm
from app.widgets.icons import line_icon
from app.views.account_pages import DashboardPage, AccountsPage, CalendarPage
from app.views.management_pages import ManagementPage
from app.views.report_pages import HistoryPage, ReportsPage
from app.views.settings_pages import SettingsPage, BackupPage


def bell_icon():
    pix = QPixmap(24, 24)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#526076"), 1.7))
    p.drawArc(6, 4, 12, 14, 0, 180 * 16)
    p.drawLine(6, 11, 6, 16)
    p.drawLine(18, 11, 18, 16)
    p.drawLine(4, 18, 20, 18)
    p.drawLine(6, 16, 4, 18)
    p.drawLine(18, 16, 20, 18)
    p.drawArc(10, 18, 4, 4, 180 * 16, 180 * 16)
    p.end()
    return QIcon(pix)


class MainWindow(QMainWindow):
    def __init__(self, db, finance=None):
        super().__init__()
        self.db = db
        self.finance = finance or FinanceService(db)
        self.remote = getattr(self.finance, "remote", False)
        self.sync_job = None
        self.backup = BackupService(db)
        self.reports = ReportService(self.finance)
        self.quitting = False
        self.form_stack = []
        self.setWindowTitle("ContasPagar | Gestão de condomínios")
        self.setWindowIcon(app_icon())
        self.resize(1440, 900)
        self.setMinimumSize(1080, 700)
        root = QWidget()
        row = QHBoxLayout(root)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self.setCentralWidget(root)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(218)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(16, 28, 16, 20)
        side.setSpacing(6)
        side.addWidget(label("ContasPagar", "brand"))
        side.addWidget(label("GESTÃO DE CONDOMÍNIOS", "subtitle"))
        side.addSpacing(26)
        row.addWidget(sidebar)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(28, 20, 28, 20)
        body_layout.setSpacing(24)
        row.addWidget(body, 1)
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(
            "Pesquisar contas, condomínios, fornecedores ou documentos…"
        )
        self.search.setMinimumWidth(390)
        self.search.returnPressed.connect(self.global_search)
        top.addWidget(self.search, 1)
        top.addWidget(button("Pesquisar", self.global_search))
        top.addSpacing(16)
        self.alert_button = button("0", self.open_alerts)
        self.alert_button.setIcon(bell_icon())
        self.alert_button.setToolTip("Central de alertas")
        top.addWidget(self.alert_button)
        body_layout.addLayout(top)
        self.stack = QStackedWidget()
        body_layout.addWidget(self.stack, 1)
        self.actions = AccountActions(self.finance, self, self.data_changed)
        self.pages = [
            DashboardPage(self.finance, self.actions, self.data_changed),
            ManagementPage(self.finance, "condominios", self.data_changed),
            AccountsPage(self.finance, self.actions, self.data_changed),
            CalendarPage(self.finance, self.actions),
            HistoryPage(self.finance),
            ReportsPage(self.reports),
            ManagementPage(self.finance, "fornecedores", self.data_changed),
            ManagementPage(self.finance, "categorias", self.data_changed),
            SettingsPage(db),
            (self.online_page() if self.remote else BackupPage(db, self.backup, self.data_changed)),
        ]
        names = [
            "Dashboard",
            "Condomínios",
            "Contas a Pagar",
            "Calendário",
            "Histórico",
            "Relatórios",
            "Fornecedores",
            "Categorias",
            "Configurações",
            "Equipe e backup" if self.remote else "Backup",
        ]
        icons = [
            "dashboard",
            "building",
            "accounts",
            "calendar",
            "history",
            "reports",
            "suppliers",
            "categories",
            "settings",
            "backup",
        ]
        self.nav = []
        for i, (name, page, icon) in enumerate(zip(names, self.pages, icons)):
            self.stack.addWidget(page)
            b = button(name)
            b.setObjectName("nav")
            b.setCheckable(True)
            b.setIcon(line_icon(icon))
            b.setIconSize(QSize(16, 16))
            b.clicked.connect(lambda checked=False, index=i: self.navigate(index))
            side.addWidget(b)
            self.nav.append(b)
        side.addStretch()
        side.addWidget(label("Financeiro organizado.\nTodos os dias.", "muted"))
        side.addSpacing(12)
        side.addWidget(label("Versão 2.0.0", "muted"))
        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip("ContasPagar")
        tray_menu = QMenu()
        tray_menu.addAction("Abrir ContasPagar").triggered.connect(self.bring_to_front)
        tray_menu.addAction("Central de alertas").triggered.connect(self.open_alerts)
        tray_menu.addSeparator()
        tray_menu.addAction("Sair").triggered.connect(self.quit_app)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self.tray_activated)
        self.tray.messageClicked.connect(self.open_alerts)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        self.notifications = NotificationService(
            self.finance, self.backup, self.tray, self
        )
        self.notifications.changed.connect(self.refresh_current)
        self.sync_timer = QTimer(self)
        if self.remote:
            self.sync_timer.timeout.connect(self.sync_online)
            self.sync_timer.start(30_000)
            top.addWidget(button("Atualizar", self.sync_online))
        self.notifications.failed.connect(self.background_error)
        self.navigate(0)
        self.startup_timer = QTimer(self)
        self.startup_timer.setSingleShot(True)
        self.startup_timer.timeout.connect(self.notifications.check)
        self.startup_timer.start(800)
        self.statusBar().showMessage(
            ("Equipe online • " + self.finance.client.user["email"] if self.remote else "Dados salvos localmente • Verificação automática de vencimentos ativa")
        )

    def online_page(self):
        from app.views.online_page import OnlinePage
        return OnlinePage(self.finance, self.sync_online)

    def sync_online(self):
        from app.widgets.network import NetworkJob
        if not self.remote or self.form_stack or self.sync_job is not None or QApplication.instance().property("network_busy"):
            return
        self.sync_job = NetworkJob(lambda: self.finance.client.request('/v1/snapshot'), self)
        self.sync_job.finished.connect(self.sync_finished)
        self.sync_job.start()

    def sync_finished(self):
        job = self.sync_job
        self.sync_job = None
        if job.error:
            self.finance.online = False
            self.statusBar().showMessage("Sem conexão • dados exibidos podem estar desatualizados. " + str(job.error))
        elif not self.form_stack:
            self.finance.snapshot = job.result
            self.finance.online = True
            self.refresh_current()
            self.statusBar().showMessage("Equipe online • Dados atualizados agora")
        job.deleteLater()

    def navigate(self, index):
        if not self.leave_forms():
            # QPushButton já alternou seu estado: restaure o item da página base.
            base = (
                self.form_stack[0][1] if self.form_stack else self.stack.currentWidget()
            )
            for i, b in enumerate(self.nav):
                b.setChecked(self.pages[i] is base)
            return False
        self.stack.setCurrentIndex(index)
        for i, b in enumerate(self.nav):
            b.setChecked(i == index)
        if index == 2 and self.pages[2].only_alerts:
            self.pages[2].only_alerts = False
        self.refresh_current()
        return True

    def open_form(self, page, on_done=None):
        previous = self.stack.currentWidget()
        self.form_stack.append((page, previous, on_done))
        self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)
        page.watch_changes()
        page.completed.connect(lambda result, p=page: self.finish_form(p, result))

    def finish_form(self, page, result):
        if not self.form_stack or self.form_stack[-1][0] is not page:
            return
        if (
            not result
            and page.dirty
            and not confirm(self, "Descartar as alterações não salvas e voltar?")
        ):
            return
        _, previous, callback = self.form_stack.pop()
        self.stack.setCurrentWidget(previous)
        self.stack.removeWidget(page)
        if callback:
            callback(result)
        if result:
            self.data_changed()
        else:
            self.refresh_current()
        page.deleteLater()

    def leave_forms(self):
        if not self.form_stack:
            return True
        if any(p.dirty for p, _, _ in self.form_stack) and not confirm(
            self, "Descartar as alterações não salvas e sair do formulário?"
        ):
            return False
        while self.form_stack:
            page, previous, _ = self.form_stack.pop()
            self.stack.setCurrentWidget(previous)
            self.stack.removeWidget(page)
            page.deleteLater()
        return True

    def refresh_current(self):
        try:
            self.stack.currentWidget().refresh()
            count = len(self.finance.accounts(alerts=True))
            self.alert_button.setText(str(count))
            self.alert_button.setAccessibleName(f"Central de alertas: {count} contas")
        except Exception as exc:
            self.background_error(str(exc))

    def data_changed(self):
        if self.remote:
            self.sync_online()
        self.notifications.check()
        self.refresh_current()

    def global_search(self):
        if not self.navigate(2):
            return
        self.pages[2].clear_filters()
        self.pages[2].search.setText(self.search.text())
        self.pages[2].reload()

    def open_alerts(self):
        self.bring_to_front()
        if not self.navigate(2):
            return
        self.pages[2].show_alerts()
        self.notifications.mark_seen()

    def bring_to_front(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.bring_to_front()

    def background_error(self, message):
        self.statusBar().showMessage("Atenção: " + message)

    def quit_app(self):
        self.quitting = True
        self.sync_timer.stop()
        if self.sync_job:
            self.sync_job.wait()
        self.notifications.timer.stop()
        self.startup_timer.stop()
        self.tray.hide()
        QApplication.instance().quit()

    def closeEvent(self, event):
        if (
            not self.quitting
            and self.db.get_setting("fechar_bandeja", "1") == "1"
            and self.tray.isVisible()
        ):
            self.hide()
            event.ignore()
        else:
            self.quitting = True
            self.sync_timer.stop()
            if self.sync_job:
                self.sync_job.wait()
            self.notifications.timer.stop()
            self.startup_timer.stop()
            self.tray.hide()
            event.accept()
            QApplication.instance().quit()
