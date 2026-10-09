import os
import sqlite3
from datetime import datetime, date
from pathlib import Path
from app.database.connection import SCHEMA_VERSION
from app.models.entities import Base


class BackupService:
    def __init__(self, db):
        self.db = db

    def create(self, folder):
        folder = Path(folder).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        filename = folder / f"ContasPagar_{datetime.now():%Y%m%d_%H%M%S_%f}.sqlite3"
        temporary = filename.with_suffix(".tmp")
        try:
            with sqlite3.connect(self.db.path) as source, sqlite3.connect(
                temporary
            ) as target:
                source.backup(target)
            self.validate(temporary)
            os.replace(temporary, filename)
        finally:
            temporary.unlink(missing_ok=True)
        self.db.set_setting("ultimo_backup", date.today().isoformat())
        self.db.set_setting("ultimo_backup_arquivo", str(filename))
        return filename

    def validate(self, path):
        path = Path(path)
        if not path.is_file():
            raise ValueError("Arquivo de backup não encontrado.")
        with sqlite3.connect(
            path.resolve().as_uri() + "?mode=ro", uri=True
        ) as connection:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("O backup está corrompido.")
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            required = {
                "condominios",
                "contas",
                "fornecedores",
                "categorias",
                "pagamentos",
                "notificacoes",
                "recorrencias",
                "configuracoes",
                "auditoria",
            }
            if not required.issubset(tables):
                raise ValueError("Este arquivo não é um backup do ContasPagar.")
            result = connection.execute(
                "SELECT valor FROM configuracoes WHERE chave='schema_version'"
            ).fetchone()
            if not result or result[0] != SCHEMA_VERSION:
                raise ValueError("Versão de backup incompatível.")
            if connection.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("O backup contém vínculos inválidos.")
            for table in Base.metadata.sorted_tables:
                columns = {
                    r[1] for r in connection.execute(f"PRAGMA table_info({table.name})")
                }
                if not set(table.columns.keys()).issubset(columns):
                    raise ValueError("Estrutura do backup incompatível: " + table.name)

    def restore(self, path):
        self.validate(path)
        if Path(path).resolve() == self.db.path.resolve():
            raise ValueError("Selecione um arquivo de backup diferente do banco atual.")
        safety = self.create(self.db.path.parent / "backups" / "antes_restauracao")
        # Copy into a validated temporary database, then atomically replace the live file.
        temporary = self.db.path.with_suffix(".restore")
        try:
            with sqlite3.connect(
                Path(path).resolve().as_uri() + "?mode=ro", uri=True
            ) as source, sqlite3.connect(temporary) as target:
                source.backup(target)
            self.validate(temporary)
            self.db.engine.dispose()
            with sqlite3.connect(self.db.path) as current:
                current.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            for suffix in ("-wal", "-shm"):
                Path(str(self.db.path) + suffix).unlink(missing_ok=True)
            os.replace(temporary, self.db.path)
        finally:
            temporary.unlink(missing_ok=True)
            self.db.engine.dispose()
            self.db.connect()
        return safety

    def automatic(self, today=None):
        today = today or date.today()
        mode = self.db.get_setting("backup_frequencia", "Manual")
        if mode == "Manual":
            return None
        folder = self.db.get_setting(
            "backup_pasta", str(self.db.path.parent / "backups")
        )
        last = self.db.get_setting("ultimo_backup")
        elapsed = (today - date.fromisoformat(last)).days if last else 999
        if elapsed >= (7 if mode == "Semanal" else 1):
            return self.create(folder)
        return None
