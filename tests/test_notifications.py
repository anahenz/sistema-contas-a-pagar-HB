from datetime import date, timedelta
from app.services.notifications import NotificationService
from app.services.backup import BackupService
from PySide6.QtWidgets import QSystemTrayIcon
from sqlalchemy import select
from app.models.entities import Notificacao


class Tray:
    def __init__(self):
        self.messages = []

    def isVisible(self):
        return True

    def showMessage(self, *args):
        self.messages.append(args)


def test_summary_daily_persistent_and_start_at_seven_days(finance, qapp, monkeypatch):
    monkeypatch.setattr(QSystemTrayIcon, "supportsMessages", lambda: True)
    tray = Tray()
    service = NotificationService(finance, BackupService(finance.db), tray)
    service.timer.stop()
    aid = finance.save_account(
        finance.sample | {"data_vencimento": date.today() + timedelta(days=8)}
    )
    service.check()
    assert tray.messages == []
    finance.save_account(finance.sample, aid)
    service.check()
    service.check()
    assert len(tray.messages) == 1
    assert "1 conta(s) nos próximos 7 dias" in tray.messages[0][1]
    restarted = NotificationService(finance, BackupService(finance.db), tray)
    restarted.timer.stop()
    restarted.check()
    assert len(tray.messages) == 1
    finance.db.set_setting(
        "ultimo_resumo", (date.today() - timedelta(days=1)).isoformat()
    )
    restarted.check()
    assert len(tray.messages) == 2
    with finance.db.session() as s:
        assert len(s.scalars(select(Notificacao)).all()) == 1
    finance.pay(aid, {"data_pagamento": date.today(), "valor_centavos": 125000})
    finance.db.set_setting("ultimo_resumo", "")
    restarted.check()
    assert len(tray.messages) == 2
