from datetime import date
from sqlalchemy import select
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QSystemTrayIcon, QApplication
from app.models.entities import Notificacao


class NotificationService(QObject):
    changed = Signal()
    failed = Signal(str)

    def __init__(self, finance, backup, tray, parent=None):
        super().__init__(parent)
        self.finance = finance
        self.db = finance.db
        self.backup = backup
        self.tray = tray
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check)
        self.timer.start(60_000)
        self.last_day = None

    def check(self):
        if QApplication.instance().property("network_busy"):
            return
        if getattr(self.finance, "remote", False) and not self.finance.online:
            return
        today = date.today()
        try:
            self.finance.generate_recurring(today)
            if not getattr(self.finance, "remote", False):
                self.backup.automatic(today)
            alerts = self.finance.accounts(alerts=True, today=today)
            if not getattr(self.finance, "remote", False):
                with self.db.session() as s:
                    existing = {
                        n.conta_id
                        for n in s.scalars(
                            select(Notificacao).where(Notificacao.data == today)
                        ).all()
                    }
                    for a in alerts:
                        if a["id"] not in existing:
                            s.add(
                                Notificacao(conta_id=a["id"], tipo=a["status"], data=today)
                            )
            if (
                alerts
                and self.db.get_setting("notificacoes", "1") == "1"
                and self.db.get_setting("ultimo_resumo") != today.isoformat()
            ):
                if self.tray.isVisible() and QSystemTrayIcon.supportsMessages():
                    overdue = sum(a["dias"] < 0 for a in alerts)
                    due = sum(a["dias"] == 0 for a in alerts)
                    upcoming = sum(1 <= a["dias"] <= 7 for a in alerts)
                    text = f"{upcoming} conta(s) nos próximos 7 dias, {due} vencendo hoje e {overdue} vencida(s). Clique para consultar."
                    self.tray.showMessage(
                        "Contas a pagar",
                        text,
                        QSystemTrayIcon.MessageIcon.Information,
                        12000,
                    )
                    self.db.set_setting("ultimo_resumo", today.isoformat())
            if self.last_day != today:
                self.last_day = today
                self.changed.emit()
        except Exception as exc:
            import logging

            logging.exception("Falha na verificação automática")
            self.failed.emit(str(exc))

    def mark_seen(self):
        if getattr(self.finance, "remote", False):
            return
        with self.db.session() as s:
            for n in s.scalars(
                select(Notificacao).where(Notificacao.visualizada.is_(False))
            ).all():
                n.visualizada = True
