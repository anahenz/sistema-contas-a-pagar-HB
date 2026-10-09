"""Formulários internos: nunca criam uma janela de cadastro separada."""

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QScrollArea,
    QGridLayout,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QDateEdit,
)
from app.widgets.common import label, button


class FormPage(QWidget):
    completed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("formPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._result = 0
        self.dirty = False
        self.saved_id = None
        self.error_label = None

    def accept(self):
        self._result = 1
        self.dirty = False
        self.completed.emit(1)

    def reject(self):
        self.completed.emit(0)

    def result(self):
        return self._result

    def refresh(self):
        # A atualização diária não deve apagar um formulário em preenchimento.
        pass

    def show_error(self, text):
        if self.error_label:
            self.error_label.setText(text)
            self.error_label.show()

    def watch_changes(self):
        def changed(*args):
            self.dirty = True

        for edit in self.findChildren(QLineEdit):
            edit.textEdited.connect(changed)
        for edit in self.findChildren(QTextEdit):
            edit.textChanged.connect(changed)
        for edit in self.findChildren(QComboBox):
            edit.currentIndexChanged.connect(changed)
        for edit in self.findChildren(QDateEdit):
            edit.dateChanged.connect(changed)


def begin_form(page, title, description):
    page.setWindowTitle(title)
    outer = QVBoxLayout(page)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(14)
    header = QHBoxLayout()
    header.addWidget(button("← Voltar", page.reject))
    text = QVBoxLayout()
    text.addWidget(label(title, "heading"))
    subtitle = label(description, "muted")
    subtitle.setWordWrap(True)
    text.addWidget(subtitle)
    header.addLayout(text, 1)
    outer.addLayout(header)
    page.error_label = label("", "formError")
    page.error_label.setWordWrap(True)
    page.error_label.hide()
    outer.addWidget(page.error_label)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setObjectName("formScroll")
    contents = QWidget()
    contents.setObjectName("formCanvas")
    body = QVBoxLayout(contents)
    body.setContentsMargins(0, 0, 8, 0)
    body.setSpacing(16)
    scroll.setWidget(contents)
    outer.addWidget(scroll, 1)
    return outer, body


def section(body, title, subtitle=""):
    card = QFrame()
    card.setObjectName("formCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(22, 18, 22, 20)
    layout.setSpacing(14)
    layout.addWidget(label(title, "sectionTitle"))
    if subtitle:
        text = label(subtitle, "muted")
        text.setWordWrap(True)
        layout.addWidget(text)
    grid = QGridLayout()
    grid.setHorizontalSpacing(22)
    grid.setVerticalSpacing(16)
    grid.setColumnStretch(0, 1)
    grid.setColumnStretch(1, 1)
    layout.addLayout(grid)
    body.addWidget(card)
    return grid


def field(grid, title, widget, row, column=0, span=1):
    block = QVBoxLayout()
    block.setSpacing(6)
    block.addWidget(label(title, "fieldLabel"))
    if isinstance(widget, QWidget):
        block.addWidget(widget)
    else:
        block.addLayout(widget)
    grid.addLayout(block, row, column, 1, span, Qt.AlignmentFlag.AlignTop)


def finish_form(page, outer, text, callback):
    footer = QFrame()
    footer.setObjectName("formFooter")
    row = QHBoxLayout(footer)
    row.setContentsMargins(16, 12, 16, 12)
    row.addWidget(label("* Campos obrigatórios", "muted"))
    row.addStretch()
    row.addWidget(button("Cancelar", page.reject))
    row.addWidget(button(text, callback, True))
    outer.addWidget(footer)
