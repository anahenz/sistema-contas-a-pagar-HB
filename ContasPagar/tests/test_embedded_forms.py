import shiboken6
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor
from PySide6.QtTest import QTest
from app.views.main_window import MainWindow
from app.views.dialogs import AccountDialog, EntityDialog, PaymentDialog
from app.utils.theme import apply_light_theme, load_stylesheet


def close_window(window):
    window.quitting = True
    window.close()
    shiboken6.delete(window)


def test_nested_registration_preserves_account_and_saves(finance, qapp):
    window = MainWindow(finance.db)
    window.show()
    window.navigate(2)
    window.pages[2].new_account()
    account = window.stack.currentWidget()
    assert isinstance(account, AccountDialog)
    assert not account.isWindow()
    account.fields["nome"].setText("Conta preenchida antes do cadastro")
    account.fields["valor_centavos"].setText("89,90")
    account.fields["categoria_id"].setCurrentIndex(
        account.fields["categoria_id"].findData(finance.sample["categoria_id"])
    )
    account.quick_entity("condominios", account.fields["condominio_id"])
    entity = window.stack.currentWidget()
    assert isinstance(entity, EntityDialog)
    assert entity.window() is window
    entity.fields["nome"].setText("Condomínio criado dentro da conta")
    entity.save()
    assert window.stack.currentWidget() is account
    assert account.fields["nome"].text() == "Conta preenchida antes do cadastro"
    assert account.fields["valor_centavos"].value() == 8990
    assert (
        account.fields["condominio_id"].currentText()
        == "Condomínio criado dentro da conta"
    )
    account.save()
    assert window.stack.currentWidget() is window.pages[2]
    row = finance.accounts(query="Conta preenchida")[0]
    assert row["valor_centavos"] == 8990
    window.actions.run("Marcar como pago", row["id"])
    payment = window.stack.currentWidget()
    assert isinstance(payment, PaymentDialog)
    assert payment.window() is window
    payment.save()
    assert finance.account(row["id"])["status"] == "Paga"
    assert not window.form_stack
    close_window(window)


def test_unsaved_form_navigation_and_inline_error(finance, qapp, monkeypatch):
    window = MainWindow(finance.db)
    window.show()
    window.navigate(1)
    window.pages[1].add()
    entity = window.stack.currentWidget()
    entity.save()
    assert entity.error_label.isVisible()
    assert window.stack.currentWidget() is entity
    QTest.keyClicks(entity.fields["nome"], "Ainda nao salvo")
    assert entity.dirty
    monkeypatch.setattr("app.views.main_window.confirm", lambda *args: False)
    assert not window.navigate(0)
    assert window.stack.currentWidget() is entity
    monkeypatch.setattr("app.views.main_window.confirm", lambda *args: True)
    assert window.navigate(0)
    assert not finance.entities("condominios", query="Ainda nao salvo")
    close_window(window)


def test_light_theme_overrides_dark_palette(finance, qapp):
    palette = QPalette()
    for role in (QPalette.ColorRole.Base, QPalette.ColorRole.Window):
        palette.setColor(role, QColor("#111111"))
    qapp.setPalette(palette)
    apply_light_theme(qapp)
    qapp.setStyleSheet(load_stylesheet())
    assert qapp.palette().color(QPalette.ColorRole.Base).name() == "#ffffff"
    window = MainWindow(finance.db)
    window.show()
    window.navigate(3)
    qapp.processEvents()
    calendar = window.pages[3].calendar
    assert calendar.palette().color(QPalette.ColorRole.Base).lightness() > 220
    window.navigate(2)
    window.pages[2].new_account()
    form = window.stack.currentWidget()
    assert form.window() is window
    assert form.palette().color(QPalette.ColorRole.Window).lightness() > 220
    close_window(window)
