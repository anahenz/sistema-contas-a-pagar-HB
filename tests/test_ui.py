from datetime import date, timedelta
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QDate
from app.views.main_window import MainWindow
from app.views.dialogs import (
    AccountDialog,
    EntityDialog,
    DetailsDialog,
    PaymentDialog,
    CondoDetailsDialog,
)
from app.services.notifications import NotificationService
from sqlalchemy import select
from app.models.entities import Notificacao


def test_all_pages_and_dialogs(finance, qapp):
    app = qapp
    aid = finance.save_account(finance.sample)
    window = MainWindow(finance.db)
    window.resize(1440, 900)
    window.show()
    for i in range(10):
        window.navigate(i)
        app.processEvents()
    window.open_alerts()
    assert len(window.pages[2].table.rows) == 1
    window.search.setText("not found")
    window.global_search()
    assert not window.pages[2].table.rows
    window.search.setText("Aurora")
    window.global_search()
    assert len(window.pages[2].table.rows) == 1
    window.navigate(3)
    window.pages[3].calendar.setSelectedDate(QDate(finance.sample["data_vencimento"]))
    app.processEvents()
    assert len(window.pages[3].table.rows) == 1
    account = finance.account(aid)
    dialogs = [
        AccountDialog(finance, account),
        EntityDialog(finance, "condominios"),
        PaymentDialog(finance, account),
        DetailsDialog(account),
        CondoDetailsDialog(finance, finance.entities("condominios")[0]),
    ]
    for dialog in dialogs:
        window.open_form(dialog)
        app.processEvents()
        assert dialog.window() is window
        assert not dialog.isWindow()
        dialog.reject()
    window.notifications.check()
    window.notifications.check()
    with finance.db.session() as session:
        assert len(session.scalars(select(Notificacao)).all()) == 1
    window.notifications.mark_seen()
    with finance.db.session() as session:
        assert session.scalar(select(Notificacao)).visualizada
    window.notifications.timer.stop()
    window.quitting = True
    window.close()
    import shiboken6

    shiboken6.delete(window)


def test_forms_save_real_records(finance, qapp):
    app = qapp
    entity = EntityDialog(finance, "condominios")
    entity.fields["nome"].setText("Condomínio via formulário")
    entity.save()
    assert entity.result() == 1
    condo = next(
        r
        for r in finance.entities("condominios")
        if r["nome"] == "Condomínio via formulário"
    )
    dialog = AccountDialog(finance, condo_id=condo["id"])
    dialog.fields["categoria_id"].setCurrentIndex(
        dialog.fields["categoria_id"].findData(finance.sample["categoria_id"])
    )
    dialog.fields["nome"].setText("Conta via formulário")
    dialog.fields["valor_centavos"].setText("10,01")
    dialog.save()
    assert dialog.result() == 1
    a = next(a for a in finance.accounts() if a["nome"] == "Conta via formulário")
    payment = PaymentDialog(finance, a)
    payment.save()
    assert payment.result() == 1
    assert finance.account(a["id"])["status"] == "Paga"
    assert finance.history()[0]["payment"]["valor_centavos"] == 1001
