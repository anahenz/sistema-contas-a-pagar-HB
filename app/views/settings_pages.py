import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QCheckBox,
    QLineEdit,
    QComboBox,
    QFileDialog,
    QMessageBox,
    QFrame,
)
from app.widgets.common import label, button, confirm
from app.services.startup import set_windows_startup


class SettingsPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        layout.addWidget(label("Configurações", "heading"))
        frame = QFrame()
        frame.setObjectName("card")
        form = QVBoxLayout(frame)
        form.setContentsMargins(24, 24, 24, 24)
        form.setSpacing(20)
        self.notifications = QCheckBox("Receber resumo diário de vencimentos")
        self.tray = QCheckBox("Ao fechar a janela, continuar na área de notificações")
        self.startup = QCheckBox("Iniciar com o Windows, em segundo plano")
        self.startup.setEnabled(sys.platform == "win32")
        for w in (self.notifications, self.tray, self.startup):
            form.addWidget(w)
        note = label(
            "As verificações acontecem ao abrir e a cada minuto enquanto o aplicativo está em execução. O resumo é emitido no máximo uma vez por dia. Para receber ao ligar o computador, ative o início com o Windows.",
            "muted",
        )
        note.setWordWrap(True)
        form.addWidget(note)
        note = label(
            "Se o aplicativo for encerrado pelo menu “Sair”, a verificação será retomada na próxima abertura. O Windows pode silenciar notificações no modo Não perturbe.",
            "muted",
        )
        note.setWordWrap(True)
        form.addWidget(note)
        form.addWidget(button("Salvar configurações", self.save, True))
        layout.addWidget(frame)
        self.path = label("", "muted")
        self.path.setWordWrap(True)
        layout.addWidget(self.path)
        layout.addStretch()

    def refresh(self):
        self.notifications.setChecked(self.db.get_setting("notificacoes", "1") == "1")
        self.tray.setChecked(self.db.get_setting("fechar_bandeja", "1") == "1")
        self.startup.setChecked(self.db.get_setting("inicio_windows", "0") == "1")
        self.path.setText(
            (f"Servidor: {self.db.get_setting('server_url')}\nPreferências salvas neste computador • Versão 2.0.0" if self.db.get_setting("connection_mode") == "online" else f"Banco de dados local: {self.db.path}\nVersão do aplicativo: 2.0.0")
        )

    def save(self):
        try:
            if sys.platform == "win32":
                set_windows_startup(self.startup.isChecked())
            for key, value in [
                ("notificacoes", self.notifications.isChecked()),
                ("fechar_bandeja", self.tray.isChecked()),
                ("inicio_windows", self.startup.isChecked()),
            ]:
                self.db.set_setting(key, "1" if value else "0")
            QMessageBox.information(self, "Configurações", "Configurações salvas.")
        except Exception as exc:
            QMessageBox.warning(self, "Não foi possível salvar", str(exc))


class BackupPage(QWidget):
    def __init__(self, db, backup, on_change):
        super().__init__()
        self.db = db
        self.backup = backup
        self.on_change = on_change
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        layout.addWidget(label("Backup e Segurança", "heading"))
        frame = QFrame()
        frame.setObjectName("card")
        content = QVBoxLayout(frame)
        content.setContentsMargins(24, 24, 24, 24)
        content.setSpacing(18)
        content.addWidget(label("Cópias de segurança", "heading"))
        self.folder = QLineEdit()
        row = QHBoxLayout()
        row.addWidget(self.folder, 1)
        row.addWidget(button("Selecionar pasta", self.choose_folder))
        content.addLayout(row)
        form = QFormLayout()
        self.frequency = QComboBox()
        self.frequency.addItems(["Manual", "Diário", "Semanal"])
        form.addRow("Backup automático", self.frequency)
        content.addLayout(form)
        row = QHBoxLayout()
        row.addWidget(button("Salvar configuração", self.save))
        row.addWidget(button("Fazer backup agora", self.create, True))
        row.addStretch()
        content.addLayout(row)
        self.last = label("", "muted")
        self.last.setWordWrap(True)
        content.addWidget(self.last)
        layout.addWidget(frame)
        frame2 = QFrame()
        frame2.setObjectName("card")
        content2 = QVBoxLayout(frame2)
        content2.setContentsMargins(24, 24, 24, 24)
        content2.addWidget(label("Restaurar dados", "heading"))
        note = label(
            "A restauração substitui os dados atuais pelo conteúdo do backup. Antes da troca, o sistema cria uma cópia de segurança do banco atual.",
            "muted",
        )
        note.setWordWrap(True)
        content2.addWidget(note)
        content2.addWidget(button("Selecionar e restaurar backup", self.restore))
        layout.addWidget(frame2)
        note = label(
            "Backups automáticos são feitos enquanto o aplicativo está aberto ou na bandeja. Guarde uma cópia em outra unidade ou pasta protegida. Os arquivos contêm todos os cadastros e registros financeiros.",
            "muted",
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()

    def refresh(self):
        self.folder.setText(
            self.db.get_setting("backup_pasta", str(self.db.path.parent / "backups"))
        )
        self.frequency.setCurrentText(
            self.db.get_setting("backup_frequencia", "Manual")
        )
        self.last.setText(
            "Último backup: "
            + (
                self.db.get_setting("ultimo_backup_arquivo")
                or "Nenhum backup realizado"
            )
        )

    def choose_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, "Selecionar pasta", self.folder.text()
        )
        if path:
            self.folder.setText(path)

    def save(self, notify=True):
        if not self.folder.text().strip():
            raise ValueError("Selecione uma pasta para backup.")
        self.db.set_setting("backup_pasta", self.folder.text().strip())
        self.db.set_setting("backup_frequencia", self.frequency.currentText())
        if notify:
            QMessageBox.information(self, "Backup", "Configuração salva.")

    def create(self):
        try:
            self.save(False)
            path = self.backup.create(self.folder.text())
            self.refresh()
            QMessageBox.information(
                self, "Backup concluído", f"Cópia criada em:\n{path}"
            )
        except Exception as exc:
            QMessageBox.warning(self, "Backup não concluído", str(exc))

    def restore(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar backup",
            self.folder.text(),
            "Backup SQLite (*.sqlite3 *.db)",
        )
        if not path:
            return
        if not confirm(
            self,
            "Restaurar este backup e substituir os dados atuais? Uma cópia dos dados atuais será criada antes da restauração.",
        ):
            return
        try:
            safety = self.backup.restore(path)
            self.on_change()
            self.refresh()
            QMessageBox.information(
                self,
                "Restauração concluída",
                f"Dados restaurados. Cópia anterior preservada em:\n{safety}",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Restauração não concluída", str(exc))
