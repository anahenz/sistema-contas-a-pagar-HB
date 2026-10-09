from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QMenu,
)
from app.widgets.common import label, button, DataTable, confirm
from app.views.dialogs import EntityDialog, CondoDetailsDialog, FIELDS


class ManagementPage(QWidget):
    def __init__(self, finance, kind, on_change):
        super().__init__()
        self.finance = finance
        self.kind = kind
        self.on_change = on_change
        self.rows = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        row = QHBoxLayout()
        row.addWidget(
            label(
                {
                    "condominios": "Condomínios",
                    "fornecedores": "Fornecedores",
                    "categorias": "Categorias",
                }[kind],
                "heading",
            )
        )
        row.addStretch()
        row.addWidget(button("Adicionar", self.add, True))
        layout.addLayout(row)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Pesquisar cadastros...")
        self.search.textChanged.connect(self.refresh)
        layout.addWidget(self.search)
        self.columns = (
            FIELDS[kind]
            if kind != "condominios"
            else FIELDS[kind][:2]
            + [
                ("cidade", "Cidade"),
                ("sindico", "Síndico"),
                ("telefone", "Telefone"),
                ("email", "E-mail"),
            ]
        )
        self.table = DataTable([title for key, title in self.columns] + ["Ações"])
        self.table.setColumnWidth(0, 245)
        self.table.cellDoubleClicked.connect(self.view)
        layout.addWidget(self.table, 1)
        self.footer = label("", "muted")
        layout.addWidget(self.footer)

    def refresh(self):
        self.rows = self.finance.entities(self.kind, self.search.text())
        self.table.load(
            [[a.get(key, "") for key, title in self.columns] + [""] for a in self.rows]
        )
        for i, a in enumerate(self.rows):
            self.table.item(i, 0).setData(Qt.ItemDataRole.UserRole, a["id"])
            b = button("⋯")
            self.table.setCellWidget(i, len(self.columns), b)
            b.clicked.connect(lambda checked=False, v=a, w=b: self.menu(v, w))
        self.footer.setText(
            f"{len(self.rows)} cadastro(s)"
            + (" • Nenhum resultado" if not self.rows else "")
        )

    def add(self):
        self.window().open_form(EntityDialog(self.finance, self.kind))

    def edit(self, a):
        self.window().open_form(EntityDialog(self.finance, self.kind, a))

    def view(self, row, column):
        if row >= len(self.rows):
            return
        a = self.rows[row]
        if self.kind == "condominios":
            self.window().open_form(CondoDetailsDialog(self.finance, a))
        else:
            self.edit(a)

    def menu(self, a, b):
        menu = QMenu(self)
        if self.kind == "condominios":
            menu.addAction("Visualizar").triggered.connect(lambda: self.view_record(a))
        menu.addAction("Editar").triggered.connect(lambda: self.edit(a))
        menu.addAction("Excluir").triggered.connect(lambda: self.delete(a))
        menu.exec(b.mapToGlobal(b.rect().bottomLeft()))

    def view_record(self, a):
        self.window().open_form(CondoDetailsDialog(self.finance, a))

    def delete(self, a):
        if not confirm(self, f'Tem certeza que deseja excluir “{a["nome"]}”?'):
            return
        try:
            self.finance.delete_entity(self.kind, a["id"])
            self.on_change()
        except Exception as exc:
            QMessageBox.warning(self, "Cadastro não excluído", str(exc))
