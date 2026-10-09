from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem, QScrollArea
from app.widgets.common import label, button, confirm
from app.widgets.network import wait_for


class OnlinePage(QWidget):
    def __init__(self, finance, refresh):
        super().__init__()
        self.finance, self.on_refresh = finance, refresh
        self.client = finance.client
        self.users = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        layout = QVBoxLayout(content)
        layout.setSpacing(16)
        layout.addWidget(label('Equipe e segurança', 'heading'))
        layout.addWidget(label(self.client.user['email'] + ' • ' + self.client.user['role'], 'muted'))
        note = label('Os dados são compartilhados com toda a equipe. Atualização automática a cada 30 segundos fora dos formulários. Para trocar de usuário, saia pelo menu da bandeja e abra novamente.', 'muted')
        note.setWordWrap(True)
        layout.addWidget(note)
        if self.client.user['role'] != 'admin':
            layout.addWidget(label('Solicite ao administrador a inclusão de usuários e as cópias de segurança.', 'muted'))
            layout.addStretch()
            return
        layout.addWidget(label('Usuários da empresa', 'heading'))
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(['E-mail', 'Perfil', 'Acesso'])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setMaximumHeight(180)
        layout.addWidget(self.table)
        layout.addWidget(button('Ativar / desativar usuário selecionado', self.toggle_user))
        form = QFormLayout()
        self.email, self.password = QLineEdit(), QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText('Pelo menos 12 caracteres')
        self.role = QComboBox()
        self.role.addItem('Operador', 'editor')
        self.role.addItem('Administrador', 'admin')
        form.addRow('E-mail', self.email)
        form.addRow('Senha', self.password)
        form.addRow('Perfil', self.role)
        layout.addLayout(form)
        layout.addWidget(button('Cadastrar usuário', self.add_user, True))
        layout.addWidget(button('Redefinir senha do usuário selecionado', self.reset_password))
        layout.addWidget(label('Backup e migração', 'heading'))
        note = label('O servidor gera uma cópia diária no disco persistente. Baixe também cópias para guardar fora do servidor. A importação inicial só funciona enquanto a base online estiver vazia.', 'muted')
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addWidget(button('Baixar backup da base online', self.download))
        layout.addWidget(button('Importar backup local para a base online vazia', self.import_initial))
        self.feedback = label('', 'muted')
        self.feedback.setWordWrap(True)
        layout.addWidget(self.feedback)
        layout.addStretch()

    def call(self, path, data=None, method=None, raw=False):
        return wait_for(lambda: self.client.request(path, data, method, raw))

    def refresh(self):
        if self.client.user['role'] != 'admin':
            return
        try:
            self.users = self.call('/v1/users')
            self.table.setRowCount(len(self.users))
            for row, user in enumerate(self.users):
                for col, text in enumerate([user['email'], user['role'], 'Ativo' if user['active'] else 'Desativado']):
                    self.table.setItem(row, col, QTableWidgetItem(text))
            self.table.resizeColumnsToContents()
        except Exception as exc:
            self.feedback.setText(str(exc))

    def selected(self):
        row = self.table.currentRow()
        if row < 0:
            raise ValueError('Selecione um usuário na tabela.')
        return self.users[row]

    def add_user(self):
        try:
            self.call('/v1/users', {'email': self.email.text().strip(), 'password': self.password.text(), 'role': self.role.currentData()})
            self.password.clear()
            self.email.clear()
            self.refresh()
            self.feedback.setText('Usuário cadastrado. Ele pode entrar no aplicativo com o mesmo endereço de servidor.')
        except Exception as exc:
            self.feedback.setText(str(exc))

    def toggle_user(self):
        try:
            user = self.selected()
            if not confirm(self, 'Alterar o acesso de ' + user['email'] + '?'):
                return
            self.call('/v1/users/' + str(user['id']), {'active': not bool(user['active'])}, 'PATCH')
            self.refresh()
        except Exception as exc:
            self.feedback.setText(str(exc))

    def reset_password(self):
        try:
            user = self.selected()
            if not confirm(self, 'Usar a senha digitada acima como nova senha de ' + user['email'] + '? As sessões atuais serão encerradas.'):
                return
            self.call('/v1/users/' + str(user['id']), {'password': self.password.text()}, 'PATCH')
            self.password.clear()
            self.feedback.setText('Senha alterada. O usuário precisa entrar novamente.')
        except Exception as exc:
            self.feedback.setText(str(exc))

    def download(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Salvar backup online', f'ContasPagar_online_{datetime.now():%Y%m%d_%H%M}.sqlite3', 'Backup SQLite (*.sqlite3)')
        if path:
            try:
                content = self.call('/v1/backup', raw=True)
                Path(path).write_bytes(content)
                self.feedback.setText('Backup salvo em ' + path)
            except Exception as exc:
                self.feedback.setText(str(exc))

    def import_initial(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Selecionar backup local', '', 'Backup SQLite (*.sqlite3 *.db)')
        if not path or not confirm(self, 'Importar todos os cadastros deste backup para a empresa online? Todos os usuários terão acesso a esses dados.'):
            return
        try:
            if Path(path).stat().st_size > 25 * 1024 * 1024:
                raise ValueError('Limite de importação: 25 MB.')
            self.call('/v1/import', Path(path).read_bytes())
            self.on_refresh()
            self.feedback.setText('Importação concluída. Os dados locais originais foram preservados.')
        except Exception as exc:
            self.feedback.setText(str(exc))
