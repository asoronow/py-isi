import sys
import pco
import numpy as np
from PyQt5 import QtGui, QtWidgets, QtCore

CONFIGURATION = {
    'exposure time': 10e-3,
    'delay time': 0,
    'roi': (0, 0, 2048, 2048),
    'timestamp': 'ascii',
    'pixel rate': 100_000_000,
    'trigger': 'auto sequence',
    'acquire': 'auto',
    'noise filter': 'on',
    'metadata': 'on',
    'binning': (1, 1)
}


class CameraThread(QtCore.QThread):
    image_signal = QtCore.pyqtSignal(np.ndarray)

    def run(self):
        camera = pco.Camera()
        with camera as cam:
            while True:
                cam.configuration = {
                    "exposure time": 10 * 1e-3,
                    "roi": (1, 1, 2048, 2048),
                }
                cam.record(mode="sequence")
                image, meta = cam.image()

                # Convert to 8-bit if the image is 16-bit
                if image.dtype == np.uint16:
                    image = (image / 256).astype(np.uint8)
                    
                # Emit the processed image
                self.image_signal.emit(image)


class CameraPreviewWindow(QtWidgets.QWidget):
    def __init__(self):
        super(CameraPreviewWindow, self).__init__()

        # Set window title and initial size
        self.setWindowTitle("PCO Camera Live Preview")
        self.resize(1024, 720)

        self.image_label = QtWidgets.QLabel(self)
        self.image_label.setFixedSize(1024, 700)

        self.start_button = QtWidgets.QPushButton("Start Preview", self)
        self.start_button.clicked.connect(self.live_preview)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.image_label)
        layout.addWidget(self.start_button)
        self.setLayout(layout)

        self.camera_thread = CameraThread()
        self.camera_thread.image_signal.connect(self.update_image)

    def update_image(self, image):
        q_image = QtGui.QImage(image.data, image.shape[1], image.shape[0], image.strides[0], QtGui.QImage.Format_Grayscale8)
        pixmap = QtGui.QPixmap.fromImage(q_image).scaled(self.image_label.width(), self.image_label.height(), QtCore.Qt.KeepAspectRatio)
        self.image_label.setPixmap(pixmap)

    @QtCore.pyqtSlot()
    def live_preview(self):
        if not self.camera_thread.isRunning():
            self.camera_thread.start()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = CameraPreviewWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
