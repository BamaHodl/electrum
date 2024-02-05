from typing import Optional

import qrcode
import qrcode.exceptions

from PyQt5.QtGui import QColor, QPen
import PyQt5.QtGui as QtGui
from PyQt5.QtCore import Qt, QRect, QTimer
from PyQt5.QtWidgets import (
    QApplication, QVBoxLayout, QTextEdit, QHBoxLayout, QPushButton, QWidget,
    QFileDialog, QTabWidget
)

from electrum.i18n import _
from electrum.simple_config import SimpleConfig

from .util import WindowModalDialog, WWLabel, getSaveFileName


class QrCodeDataOverflow(qrcode.exceptions.DataOverflowError):
    pass


class QRCodeWidget(QWidget):

    def __init__(self, data=None, *, manual_size: bool = False):
        QWidget.__init__(self)
        self.data = None
        self.qr = None
        self._framesize = None  # type: Optional[int]
        self._manual_size = manual_size
        self.setData(data)

    def setData(self, data):
        if data:
            qr = qrcode.QRCode(
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=0,
            )
            try:
                qr.add_data(data)
                qr_matrix = qr.get_matrix()  # test that data fits in QR code
            except (ValueError, qrcode.exceptions.DataOverflowError) as e:
                raise QrCodeDataOverflow() from e
            self.qr = qr
            self.data = data
            if not self._manual_size:
                k = len(qr_matrix)
                self.setMinimumSize(k * 5, k * 5)
        else:
            self.qr = None
            self.data = None

        self.update()


    def paintEvent(self, e):
        if not self.data:
            return

        black = QColor(0, 0, 0, 255)
        grey  = QColor(196, 196, 196, 255)
        white = QColor(255, 255, 255, 255)
        black_pen = QPen(black) if self.isEnabled() else QPen(grey)
        black_pen.setJoinStyle(Qt.MiterJoin)

        if not self.qr:
            qp = QtGui.QPainter()
            qp.begin(self)
            qp.setBrush(white)
            qp.setPen(white)
            r = qp.viewport()
            qp.drawRect(0, 0, r.width(), r.height())
            qp.end()
            return

        matrix = self.qr.get_matrix()
        k = len(matrix)
        qp = QtGui.QPainter()
        qp.begin(self)
        r = qp.viewport()
        framesize = min(r.width(), r.height())
        self._framesize = framesize
        boxsize = int(framesize/(k + 2))
        if boxsize < 2:
            qp.drawText(0, 20, 'Cannot draw QR code:')
            qp.drawText(0, 40, 'Boxsize too small')
            qp.end()
            return
        size = k*boxsize
        left = (framesize - size)/2
        top = (framesize - size)/2
        # Draw white background with margin
        qp.setBrush(white)
        qp.setPen(white)
        qp.drawRect(0, 0, framesize, framesize)
        # Draw qr code
        qp.setBrush(black if self.isEnabled() else grey)
        qp.setPen(black_pen)
        for r in range(k):
            for c in range(k):
                if matrix[r][c]:
                    qp.drawRect(
                        int(left+c*boxsize), int(top+r*boxsize),
                        boxsize - 1, boxsize - 1)
        qp.end()

    def grab(self) -> QtGui.QPixmap:
        """Overrides QWidget.grab to only include the QR code itself,
        excluding horizontal/vertical stretch.
        """
        fsize = self._framesize
        if fsize is None:
            fsize = -1
        rect = QRect(0, 0, fsize, fsize)
        return QWidget.grab(self, rect)

class SpecterQREncoder:
    def __init__(self, data):
        if data[-1:] == b"\n":
            data = data[:-1]
        #data = data.decode('utf-8')
        self.data = data
        self.qr_max_fragment_size = 65
        self.part_num_sent = 0
        self.sent_complete = False
        self._create_parts()


    def _create_parts(self):
        self.parts = []

        start = 0
        stop = self.qr_max_fragment_size
        qr_cnt = ((len(self.data)-1) // self.qr_max_fragment_size) + 1

        if qr_cnt == 1:
            self.parts.append(self.data[start:stop])

        cnt = 0
        while cnt < qr_cnt and qr_cnt != 1:
            part = "p" + str(cnt+1) + "of" + str(qr_cnt) + " " + self.data[start:stop]
            self.parts.append(part)

            start = start + self.qr_max_fragment_size
            stop = stop + self.qr_max_fragment_size
            if stop > len(self.data):
                stop = len(self.data)
            cnt += 1


    def next_part(self) -> str:
        # if part num sent is gt number of parts, start at 0
        if self.part_num_sent > (len(self.parts) - 1):
            self.part_num_sent = 0

        part = self.parts[self.part_num_sent]

        # when parts sent eq num of parts in list
        if self.part_num_sent == (len(self.parts) - 1):
            self.sent_complete = True

        # increment to next part
        self.part_num_sent += 1

        return part



class QRDialog(WindowModalDialog):

    #specter_qrw : QRCodeWidget = None
    #specter_encoder : SpecterQREncoder = None

    def __init__(
            self,
            *,
            data,
            parent=None,
            title="",
            show_text=False,
            help_text=None,
            show_copy_text_btn=False,
            base64_data=[],
            config: SimpleConfig,
    ):
        WindowModalDialog.__init__(self, parent, title)
        self.config = config

        vbox = QVBoxLayout()

        qrw = QRCodeWidget(data, manual_size=True)
        qrw.setMinimumSize(250, 250)
        vbox.addWidget(qrw, 1)

        help_text = data if show_text else help_text
        if help_text:
            text_label = WWLabel()
            text_label.setText(help_text)
            vbox.addWidget(text_label)
        hbox = QHBoxLayout()
        hbox.addStretch(1)

        def print_qr():
            filename = getSaveFileName(
                parent=self,
                title=_("Select where to save file"),
                filename="qrcode.png",
                config=self.config,
            )
            if not filename:
                return
            p = qrw.grab()
            p.save(filename, 'png')
            self.show_message(_("QR code saved to file") + " " + filename)

        def copy_image_to_clipboard():
            p = qrw.grab()
            QApplication.clipboard().setPixmap(p)
            self.show_message(_("QR code copied to clipboard"))

        def copy_text_to_clipboard():
            QApplication.clipboard().setText(data)
            self.show_message(_("Text copied to clipboard"))

        b = QPushButton(_("Copy Image"))
        hbox.addWidget(b)
        b.clicked.connect(copy_image_to_clipboard)

        if show_copy_text_btn:
            b = QPushButton(_("Copy Text"))
            hbox.addWidget(b)
            b.clicked.connect(copy_text_to_clipboard)

        b = QPushButton(_("Save"))
        hbox.addWidget(b)
        b.clicked.connect(print_qr)

        b = QPushButton(_("Close"))
        hbox.addWidget(b)
        b.clicked.connect(self.accept)
        b.setDefault(True)

        vbox.addLayout(hbox)

        main_widget = vbox

        if base64_data:

            self.defaultqr_tab = QWidget()
            self.defaultqr_tab.setLayout(vbox)
            self.defaultqr_tab.setMinimumSize(self.defaultqr_tab.sizeHint())

            self.specter_encoder = SpecterQREncoder(data=base64_data)
            self.specter_tab = self.create_specter_tab()
            self.tabs = QTabWidget(self)
            self.tabs.addTab(self.defaultqr_tab, 'Default (HD)')
            self.tabs.addTab(self.specter_tab, 'SeedSigner/Specter')
            main_widget = self.tabs

            self.timer = QTimer(self)

            if len(self.specter_encoder.parts) > 1:
                self.timer.timeout.connect(self.nextSpecterData)
                self.timer.start(300)
        else:
            self.setLayout(vbox)

        # note: the word-wrap on the text_label is causing layout sizing issues.
        #       see https://stackoverflow.com/a/25661985 and https://bugreports.qt.io/browse/QTBUG-37673
        #       workaround:
        self.setMinimumSize(main_widget.sizeHint())


    def nextSpecterData(self):
        self.specter_qrw.setData(self.specter_encoder.next_part())

    def create_specter_tab(self):
        w = QWidget()
        vbox = QVBoxLayout()

        self.specter_qrw = QRCodeWidget(self.specter_encoder.next_part(), manual_size=True)
        self.specter_qrw.setMinimumSize(250, 250)
        vbox.addWidget(self.specter_qrw, 1)

        hbox = QHBoxLayout()
        hbox.addStretch(1)

        b = QPushButton(_("Close"))
        hbox.addWidget(b)
        b.clicked.connect(self.accept)
        b.setDefault(True)

        vbox.addLayout(hbox)
        w.setLayout(vbox)
        w.setMinimumSize(w.sizeHint())
        return w




