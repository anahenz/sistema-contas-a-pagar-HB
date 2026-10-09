import os
from pathlib import Path
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.models.entities import Base, Categoria, Configuracao

CATEGORIES = [
    "Água",
    "Energia",
    "Gás",
    "Internet",
    "Elevador",
    "Limpeza",
    "Jardinagem",
    "Manutenção",
    "Seguro",
    "Administração",
    "Contabilidade",
    "Prestador de serviço",
    "Obras",
    "Impostos",
    "Taxas",
    "Outros",
]
SCHEMA_VERSION = "1"


def data_dir():
    override = os.getenv("CONTASPAGAR_DATA_DIR")
    path = (
        Path(override)
        if override
        else Path(os.getenv("LOCALAPPDATA", Path.home() / ".local" / "share"))
        / "ContasPagar"
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


class Database:
    def __init__(self, path=None):
        self.path = Path(path) if path else data_dir() / "contas_pagar.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connect()
        Base.metadata.create_all(self.engine)
        with self.session() as session:
            version = session.get(Configuracao, "schema_version")
            if version and version.valor != SCHEMA_VERSION:
                raise ValueError("Versão de banco incompatível com este aplicativo.")
            if not version:
                session.add(Configuracao(chave="schema_version", valor=SCHEMA_VERSION))
                for name in CATEGORIES:
                    session.add(Categoria(nome=name))

    def connect(self):
        self.engine = create_engine(
            "sqlite:///" + str(self.path), connect_args={"timeout": 30}
        )

        @event.listens_for(self.engine, "connect")
        def pragmas(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA busy_timeout=30000")

        self.factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    @contextmanager
    def session(self):
        with self.factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def get_setting(self, key, default=""):
        with self.session() as s:
            obj = s.get(Configuracao, key)
            return obj.valor if obj else default

    def set_setting(self, key, value):
        with self.session() as s:
            obj = s.get(Configuracao, key)
            if obj:
                obj.valor = str(value)
            else:
                s.add(Configuracao(chave=key, valor=str(value)))
