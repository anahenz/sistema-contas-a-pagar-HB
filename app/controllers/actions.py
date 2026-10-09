from PySide6.QtWidgets import QMessageBox
from app.views.dialogs import AccountDialog, DetailsDialog, PaymentDialog
from app.widgets.common import confirm


class AccountActions:
    def __init__(self, finance, parent, on_change):
        self.finance = finance
        self.parent = parent
        self.on_change = on_change

    def run(self, action, account_id):
        try:
            account = self.finance.account(account_id)
            if not account:
                raise ValueError("Conta não encontrada.")
            changed = False
            if action == "Visualizar":
                self.parent.open_form(DetailsDialog(account))
            elif action == "Editar":
                self.parent.open_form(AccountDialog(self.finance, account))
            elif action == "Duplicar":
                self.parent.open_form(
                    AccountDialog(self.finance, account, duplicate=True)
                )
            elif action == "Marcar como pago":
                self.parent.open_form(PaymentDialog(self.finance, account))
            elif action == "Desfazer pagamento":
                if confirm(
                    self.parent,
                    "Desfazer este pagamento? O registro será mantido como estornado no histórico.",
                ):
                    self.finance.undo_payment(account_id)
                    changed = True
            elif action in ("Cancelar conta", "Reativar conta"):
                if confirm(self.parent, f"{action}?"):
                    self.finance.cancel_account(account_id)
                    changed = True
            elif action == "Encerrar recorrência":
                if confirm(
                    self.parent,
                    "Encerrar a série recorrente? Os lançamentos já criados serão mantidos e poderão ser cancelados individualmente.",
                ):
                    self.finance.stop_recurrence(account_id)
                    changed = True
            elif action == "Excluir":
                if confirm(
                    self.parent,
                    "Tem certeza que deseja excluir esta conta? A exclusão não pode ser desfeita. Excluir um lançamento não encerra sua série recorrente.",
                ):
                    self.finance.delete_account(account_id)
                    changed = True
            if changed:
                self.on_change()
        except Exception as exc:
            QMessageBox.warning(self.parent, "Ação não concluída", str(exc))
