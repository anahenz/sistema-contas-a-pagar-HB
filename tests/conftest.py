import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from datetime import date, timedelta
import pytest
from app.database.connection import Database
from app.services.finance import FinanceService


@pytest.fixture
def finance(tmp_path):
    db = Database(tmp_path / "test.sqlite3")
    service = FinanceService(db)
    condo = service.save_entity("condominios", {"nome": "Residencial Aurora"})
    supplier = service.save_entity("fornecedores", {"nome": "Energia Sul"})
    category = next(
        c["id"] for c in service.entities("categorias") if c["nome"] == "Energia"
    )
    service.sample = {
        "condominio_id": condo,
        "fornecedor_id": supplier,
        "categoria_id": category,
        "nome": "Energia elétrica",
        "descricao": "Fatura de energia",
        "valor_centavos": 125000,
        "data_emissao": date.today() - timedelta(days=30),
        "data_vencimento": date.today() + timedelta(days=7),
        "forma_pagamento": "Boleto",
        "codigo_barras": "12345",
        "numero_documento": "NF-100",
        "observacoes": "",
    }
    yield service
    db.engine.dispose()


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app
    # Destroy C++ widgets before QApplication leaves scope. Signal callbacks can
    # otherwise retain Python wrappers until interpreter shutdown in offscreen Qt.
    import shiboken6
    import gc

    for widget in app.topLevelWidgets():
        if shiboken6.isValid(widget):
            shiboken6.delete(widget)
    app.processEvents()
    gc.collect()
