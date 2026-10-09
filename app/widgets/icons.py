from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPainterPath


def line_icon(name, color="#65758B"):
    pix = QPixmap(24, 24)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(
        QPen(
            QColor(color),
            1.6,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
    )
    p.setBrush(Qt.BrushStyle.NoBrush)
    if name == "dashboard":
        for x, y in [(4, 4), (14, 4), (4, 14), (14, 14)]:
            p.drawRoundedRect(QRectF(x, y, 6, 6), 1, 1)
    elif name == "building":
        p.drawRoundedRect(QRectF(5, 3, 14, 18), 1, 1)
        for x in (9, 15):
            for y in (7, 11, 15):
                p.drawPoint(x, y)
        p.drawLine(10, 21, 10, 18)
        p.drawLine(14, 21, 14, 18)
    elif name == "accounts":
        p.drawRoundedRect(QRectF(5, 3, 14, 18), 1, 1)
        for y in (8, 12, 16):
            p.drawLine(8, y, 16, y)
    elif name == "calendar":
        p.drawRoundedRect(QRectF(3, 5, 18, 16), 2, 2)
        p.drawLine(3, 10, 21, 10)
        p.drawLine(8, 3, 8, 7)
        p.drawLine(16, 3, 16, 7)
        for x, y in [(8, 14), (13, 14), (8, 18), (13, 18)]:
            p.drawPoint(x, y)
    elif name == "history":
        p.drawArc(QRectF(4, 4, 16, 16), 40 * 16, 290 * 16)
        p.drawLine(12, 7, 12, 12)
        p.drawLine(12, 12, 16, 14)
        p.drawLine(3, 8, 4, 3)
        p.drawLine(4, 3, 8, 5)
    elif name == "reports":
        p.drawLine(4, 3, 4, 21)
        p.drawLine(4, 21, 22, 21)
        for x, y in [(8, 13), (13, 8), (18, 4)]:
            p.drawRoundedRect(QRectF(x, y, 2, 18 - y), 0.5, 0.5)
    elif name == "suppliers":
        p.drawRoundedRect(QRectF(3, 7, 18, 13), 2, 2)
        p.drawRoundedRect(QRectF(8, 3, 8, 4), 1, 1)
        p.drawLine(3, 12, 21, 12)
        p.drawLine(10, 12, 14, 12)
    elif name == "categories":
        path = QPainterPath(QPointF(3, 4))
        path.lineTo(12, 4)
        path.lineTo(21, 13)
        path.lineTo(13, 21)
        path.lineTo(3, 11)
        path.closeSubpath()
        p.drawPath(path)
        p.drawEllipse(QRectF(6, 7, 2, 2))
    elif name == "settings":
        for x, y in [(6, 8), (12, 16), (18, 10)]:
            p.drawLine(x, 3, x, y - 2)
            p.drawLine(x, y + 2, x, 21)
            p.drawEllipse(QRectF(x - 2, y - 2, 4, 4))
    elif name == "backup":
        p.drawEllipse(QRectF(4, 3, 16, 6))
        p.drawLine(4, 6, 4, 18)
        p.drawLine(20, 6, 20, 18)
        p.drawArc(QRectF(4, 15, 16, 6), 180 * 16, 180 * 16)
        p.drawArc(QRectF(4, 9, 16, 6), 180 * 16, 180 * 16)
    p.end()
    return QIcon(pix)
