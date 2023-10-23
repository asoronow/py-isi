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
    def __init__(self, exposure_time=10e-3):
        super(CameraThread, self).__init__()
        self.exposure_time = exposure_time

    def set_exposure_time(self, value):
        # Assuming slider's value range is from 0 to 100
        # converting that to a range of 1e-6 to 100e-3
        self.exposure_time = value * 1e-3

    def run(self):
        camera = pco.Camera()
        with camera as cam:
            while True:
                cam.configuration = {
                    "exposure time": self.exposure_time,
                    "roi": (1, 1, 2048, 2048),
                }
                cam.record(mode="sequence")
                image, meta = cam.image()

                if image.dtype == np.uint16:
                    image = (image / 256).astype(np.uint8)
                self.image_signal.emit(image)

class CameraPreviewWindow(QtWidgets.QWidget):
    def __init__(self):
        super(CameraPreviewWindow, self).__init__()

        self.setWindowTitle("PCO Camera Live Preview")
        self.resize(1024, 720)

        self.image_label = QtWidgets.QLabel(self)
        self.image_label.setFixedSize(1024, 700)

        self.start_button = QtWidgets.QPushButton("Start Preview", self)
        self.start_button.clicked.connect(self.live_preview)

        self.exposure_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        self.exposure_slider.setRange(0, 100)  # Assuming a range from 0 to 100 for simplicity
        self.exposure_slider.setValue(10)  # Default value
        self.exposure_slider.valueChanged.connect(self.update_exposure_time)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.image_label)
        layout.addWidget(self.exposure_slider)
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

    def update_exposure_time(self, value):
        self.camera_thread.set_exposure_time(value)

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = CameraPreviewWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
