import hashlib
import logging
import sys
from pathlib import Path
from PySide6.QtCore import QLocale, QTimer, QEvent
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon
from app.database.connection import Database, data_dir
from app.views.main_window import MainWindow
from app.utils.theme import apply_light_theme, load_stylesheet


def main():
    app = QApplication(sys.argv)
    apply_light_theme(app)
    app.setApplicationName("ContasPagar")
    app.setOrganizationName("ContasPagar")
    app.setQuitOnLastWindowClosed(False)
    QLocale.setDefault(QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil))
    from PySide6.QtCore import QTranslator, QLibraryInfo

    translator = QTranslator(app)
    translator.load(
        "qtbase_pt", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    )
    app.installTranslator(translator)
    directory = data_dir()
    logging.basicConfig(
        filename=str(directory / "contaspagar.log"),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )
    name = (
        "ContasPagar_"
        + hashlib.sha256(str(directory.resolve()).encode()).hexdigest()[:20]
    )
    socket = QLocalSocket()
    socket.connectToServer(name)
    if socket.waitForConnected(350):
        socket.write(b"open")
        socket.flush()
        socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        return 0
    QLocalServer.removeServer(name)
    server = QLocalServer(app)
    if not server.listen(name):
        QMessageBox.critical(
            None, "ContasPagar", "Não foi possível iniciar a instância do aplicativo."
        )
        return 1
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "ContasPagar.Desktop.1"
        )
    style = Path(__file__).resolve().parent / "app" / "assets" / "style.qss"
    app.setStyleSheet(load_stylesheet())
    try:
        db = Database()
        from app.views.connection_page import ConnectionPage
        connection = ConnectionPage(db)
        if not connection.exec():
            db.engine.dispose()
            server.close()
            return 0
        window = MainWindow(db, connection.finance)
    except Exception as exc:
        logging.exception("Falha ao iniciar")
        QMessageBox.critical(
            None,
            "Não foi possível iniciar",
            f"{exc}\n\nConsulte o arquivo contaspagar.log na pasta de dados.",
        )
        return 1

    def activate():
        peer = server.nextPendingConnection()
        if peer:
            peer.disconnectFromServer()
            peer.deleteLater()
        window.bring_to_front()

    server.newConnection.connect(activate)

    def exception_hook(typ, value, tb):
        logging.error("Erro não tratado", exc_info=(typ, value, tb))
        QMessageBox.warning(window, "Operação não concluída", str(value))

    sys.excepthook = exception_hook
    if "--tray" not in sys.argv or not QSystemTrayIcon.isSystemTrayAvailable():
        window.show()
    result = app.exec()
    window.quitting = True
    window.close()
    window.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    server.close()
    db.engine.dispose()
    return result


if __name__ == "__main__":
    sys.exit(main())
