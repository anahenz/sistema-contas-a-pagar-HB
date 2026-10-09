from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QLabel
from app.widgets.common import button, label
from app.widgets.network import wait_for
from app.services.remote import ApiClient, RemoteFinance


class ConnectionPage(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.finance = None
        self.setWindowTitle('ContasPagar — Acesso')
        self.setMinimumWidth(510)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 28, 30, 28)
        outer.setSpacing(18)
        outer.addWidget(label('Bem-vindo ao ContasPagar', 'heading'))
        intro = label('Escolha como acessar seus dados.', 'muted')
        outer.addWidget(intro)
        form = QFormLayout()
        self.mode = QComboBox()
        self.mode.addItems(['Equipe online', 'Somente neste computador'])
        form.addRow('Modo de uso', self.mode)
        self.url = QLineEdit(db.get_setting('server_url'))
        self.url.setPlaceholderText('https://seu-servidor.onrender.com')
        self.email = QLineEdit(db.get_setting('server_email'))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        for text, field in [('Servidor', self.url), ('E-mail', self.email), ('Senha', self.password)]:
            form.addRow(text, field)
        outer.addLayout(form)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setStyleSheet('color: #B91C1C;')
        outer.addWidget(self.error)
        note = label('No modo online, todos os usuários desta empresa acessam a mesma base. A senha não é salva neste computador.', 'muted')
        note.setWordWrap(True)
        outer.addWidget(note)
        self.enter = button('Entrar', self.login, True)
        outer.addWidget(self.enter)
        self.mode.currentIndexChanged.connect(self.toggle)
        self.mode.setCurrentIndex(0 if db.get_setting('connection_mode', 'online') == 'online' else 1)
        self.toggle()
        self.password.returnPressed.connect(self.login)

    def toggle(self):
        for widget in (self.url, self.email, self.password):
            widget.setEnabled(self.mode.currentIndex() == 0)

    def login(self):
        self.error.clear()
        if self.mode.currentIndex() == 1:
            self.db.set_setting('connection_mode', 'local')
            self.accept()
            return
        self.enter.setEnabled(False)
        try:
            client = ApiClient(self.url.text())
            email, password = self.email.text().strip(), self.password.text()
            snapshot = wait_for(lambda: client.login(email, password))
            self.password.clear()
            self.finance = RemoteFinance(self.db, client, snapshot)
            self.db.set_setting('connection_mode', 'online')
            self.db.set_setting('server_url', client.url)
            self.db.set_setting('server_email', email)
            self.accept()
        except Exception as exc:
            self.error.setText(str(exc))
        finally:
            self.enter.setEnabled(True)
