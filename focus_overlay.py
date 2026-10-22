"""Select a physical-pixel crop of the primary display, without uploading it."""
import io
from PySide6.QtCore import Qt, QRect, Signal
from PySide6.QtGui import QPainter, QColor, QPixmap
from PySide6.QtWidgets import QWidget


class FocusOverlay(QWidget):
    selected = Signal(object)

    def __init__(self, image, geometry):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowTitle('Sleepy · Select focus area')
        self.setGeometry(geometry)
        self.setCursor(Qt.CrossCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.origin = None
        self.selection = QRect()
        self.image_size = image.size
        data = io.BytesIO()
        image.save(data, format='PNG')
        self.picture = QPixmap()
        self.picture.loadFromData(data.getvalue())

    def paintEvent(self, event):
        p = QPainter(self)
        p.drawPixmap(self.rect(), self.picture)
        p.fillRect(self.rect(), QColor(0, 0, 0, 110))
        if not self.selection.isEmpty():
            p.save()
            p.setClipRect(self.selection)
            p.drawPixmap(self.rect(), self.picture)
            p.restore()
            p.setPen(QColor('#8d9bff'))
            p.drawRect(self.selection)
        p.fillRect(20, 20, 480, 44, QColor('#161820'))
        p.setPen(Qt.white)
        p.drawText(35, 48, 'Drag around the problem · Escape to cancel')

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.origin = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if self.origin is not None:
            self.selection = QRect(self.origin, event.position().toPoint()).normalized().intersected(self.rect())
            self.update()

    def pixel_box(self):
        r = self.selection
        sx, sy = self.image_size[0] / self.width(), self.image_size[1] / self.height()
        return (round(r.x()*sx), round(r.y()*sy), round((r.x()+r.width())*sx), round((r.y()+r.height())*sy))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.selection.width() >= 10 and self.selection.height() >= 10:
            self.selected.emit((self.pixel_box(), self.image_size))
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.selected.emit(None)
            self.close()
