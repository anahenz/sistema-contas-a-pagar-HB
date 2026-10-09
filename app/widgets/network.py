from PySide6.QtCore import QThread, Signal, QEventLoop, Qt
from PySide6.QtWidgets import QApplication


class NetworkJob(QThread):
    def __init__(self, function, parent=None):
        super().__init__(parent)
        self.function = function
        self.result = None
        self.error = None

    def run(self):
        try:
            self.result = self.function()
        except Exception as exc:
            self.error = exc


def wait_for(function):
    """Network I/O off the UI thread; user input excluded to prevent duplicate writes."""
    app = QApplication.instance()
    if app is None:
        return function()
    app.setProperty("network_busy", True)
    job = NetworkJob(function)
    loop = QEventLoop()
    job.finished.connect(loop.quit)
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    job.start()
    loop.exec(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
    job.wait()
    QApplication.restoreOverrideCursor()
    app.setProperty("network_busy", False)
    if job.error:
        raise ValueError(str(job.error))
    return job.result
