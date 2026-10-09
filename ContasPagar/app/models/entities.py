from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    DateTime,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
    text,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Condominio(Base):
    __tablename__ = "condominios"
    id = Column(Integer, primary_key=True)
    nome = Column(String(200), nullable=False)
    cnpj = Column(String(18), default="")
    endereco = Column(String(300), default="")
    cidade = Column(String(100), default="")
    sindico = Column(String(150), default="")
    telefone = Column(String(30), default="")
    email = Column(String(200), default="")
    observacoes = Column(Text, default="")


class Fornecedor(Base):
    __tablename__ = "fornecedores"
    id = Column(Integer, primary_key=True)
    nome = Column(String(200), nullable=False)
    cnpj_cpf = Column(String(18), default="")
    telefone = Column(String(30), default="")
    email = Column(String(200), default="")


class Categoria(Base):
    __tablename__ = "categorias"
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False, unique=True)


class Recorrencia(Base):
    __tablename__ = "recorrencias"
    id = Column(Integer, primary_key=True)
    meses = Column(Integer, nullable=False)
    dia_original = Column(Integer, nullable=False)
    proximo_vencimento = Column(Date, nullable=False)
    modelo = Column(Text, nullable=False)
    ativa = Column(Boolean, default=True, nullable=False)


class Conta(Base):
    __tablename__ = "contas"
    __table_args__ = (
        UniqueConstraint("recorrencia_id", "data_vencimento", name="uq_ocorrencia"),
        CheckConstraint("valor_centavos > 0", name="ck_valor_conta"),
    )
    id = Column(Integer, primary_key=True)
    condominio_id = Column(
        Integer, ForeignKey("condominios.id", ondelete="RESTRICT"), nullable=False
    )
    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id", ondelete="RESTRICT"))
    categoria_id = Column(
        Integer, ForeignKey("categorias.id", ondelete="RESTRICT"), nullable=False
    )
    nome = Column(String(200), nullable=False)
    descricao = Column(Text, default="")
    valor_centavos = Column(Integer, nullable=False)
    data_emissao = Column(Date, nullable=False)
    data_vencimento = Column(Date, nullable=False)
    forma_pagamento = Column(String(80), default="")
    codigo_barras = Column(String(100), default="")
    numero_documento = Column(String(100), default="")
    observacoes = Column(Text, default="")
    cancelada = Column(Boolean, default=False, nullable=False)
    recorrencia_id = Column(Integer, ForeignKey("recorrencias.id", ondelete="RESTRICT"))


class Pagamento(Base):
    __tablename__ = "pagamentos"
    __table_args__ = (
        Index(
            "uq_pagamento_ativo",
            "conta_id",
            unique=True,
            sqlite_where=text("estornado_em IS NULL"),
        ),
        CheckConstraint("valor_centavos > 0", name="ck_valor_pagamento"),
    )
    id = Column(Integer, primary_key=True)
    conta_id = Column(
        Integer, ForeignKey("contas.id", ondelete="RESTRICT"), nullable=False
    )
    data_pagamento = Column(Date, nullable=False)
    valor_centavos = Column(Integer, nullable=False)
    forma_pagamento = Column(String(80), default="")
    comprovante = Column(String(200), default="")
    observacoes = Column(Text, default="")
    snapshot = Column(Text, nullable=False, default="{}")
    estornado_em = Column(DateTime)
    criado_em = Column(DateTime, default=datetime.now, nullable=False)


class Notificacao(Base):
    __tablename__ = "notificacoes"
    __table_args__ = (UniqueConstraint("conta_id", "data", name="uq_alerta_diario"),)
    id = Column(Integer, primary_key=True)
    conta_id = Column(
        Integer, ForeignKey("contas.id", ondelete="CASCADE"), nullable=False
    )
    tipo = Column(String(80), nullable=False)
    data = Column(Date, nullable=False)
    visualizada = Column(Boolean, default=False, nullable=False)


class Configuracao(Base):
    __tablename__ = "configuracoes"
    chave = Column(String(100), primary_key=True)
    valor = Column(Text, nullable=False)


class Auditoria(Base):
    __tablename__ = "auditoria"
    id = Column(Integer, primary_key=True)
    data = Column(DateTime, default=datetime.now, nullable=False)
    acao = Column(String(80), nullable=False)
    detalhes = Column(Text, nullable=False)
