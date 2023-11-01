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
        self.roi = (1, 1, 2048, 2048)  # default ROI value

    def run(self):
        camera = pco.Camera()
        with camera as cam:
            while True:
                cam.configuration = {
                    "exposure time": self.exposure_time,
                    "roi": self.roi,  # Use the updated ROI value
                }
                cam.record(mode="sequence")
                image, meta = cam.image()

                # Convert to 8-bit if the image is 16-bit
                if image.dtype == np.uint16:
                    image = (image / 256).astype(np.uint8)
                    
                # Emit the processed image
                self.image_signal.emit(image)

    def update_exposure(self, exposure_time):
        self.exposure_time = float(exposure_time * 1e-3)

    def adjust_roi(self, roi):
        self.roi = roi


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

        self.spin_box = QtWidgets.QDoubleSpinBox(self)
        self.spin_box.setRange(1, 10000)  # Adjust the range as needed
        self.spin_box.setDecimals(0)
        self.spin_box.setValue(10)
        self.spin_box.setSingleStep(1)  # Setting step size to 1
        self.spin_box.valueChanged.connect(self.adjust_exposure)

        # Spin boxes for ROI adjustments
        self.left_spin_box = QtWidgets.QSpinBox(self)
        self.left_spin_box.setRange(1, 2048)
        self.left_spin_box.setValue(1)
        self.left_spin_box.valueChanged.connect(self.adjust_roi)

        self.top_spin_box = QtWidgets.QSpinBox(self)
        self.top_spin_box.setRange(1, 2048)
        self.top_spin_box.setValue(1)
        self.top_spin_box.valueChanged.connect(self.adjust_roi)

        self.right_spin_box = QtWidgets.QSpinBox(self)
        self.right_spin_box.setRange(1, 2048)
        self.right_spin_box.setValue(2048)
        self.right_spin_box.valueChanged.connect(self.adjust_roi)

        self.bottom_spin_box = QtWidgets.QSpinBox(self)
        self.bottom_spin_box.setRange(1, 2048)
        self.bottom_spin_box.setValue(2048)
        self.bottom_spin_box.valueChanged.connect(self.adjust_roi)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.image_label)
        layout.addWidget(self.spin_box)

        # Add the spin boxes to your layout
        layout.addWidget(QtWidgets.QLabel("Left ROI"))
        layout.addWidget(self.left_spin_box)
        layout.addWidget(QtWidgets.QLabel("Top ROI"))
        layout.addWidget(self.top_spin_box)
        layout.addWidget(QtWidgets.QLabel("Right ROI"))
        layout.addWidget(self.right_spin_box)
        layout.addWidget(QtWidgets.QLabel("Bottom ROI"))
        layout.addWidget(self.bottom_spin_box)

        layout.addWidget(self.start_button)
        self.setLayout(layout)

        self.camera_thread = CameraThread()

        self.camera_thread.image_signal.connect(self.update_image)

    def legalize_roi(self, roi, camera_type='panda 4.2', current_roi=None, verbose=True):
        left = roi.get('left')
        right = roi.get('right')
        bottom = roi.get('bottom')
        top = roi.get('top')
        if verbose:
            print(" Requested camera ROI:")
            print("  From pixel", left, "to pixel", right, "(left/right)")
            print("  From pixel", top, "to pixel", bottom, "(up/down)")
        min_lr, min_ud = 1, 1
        #set-up min width/height SPECIFICALLY for 'panda 4.2'
        min_width, min_height = 192, 10
        max_lr, max_ud, step_lr = 2048, 2048, 32
        if current_roi is None:
            current_roi = {'left': min_lr, 'right':  max_lr,
                        'top':  min_ud, 'bottom': max_ud}
        # Legalize left/right
        if left is None and right is None:
            # User isn't trying to change l/r ROI; use existing ROI.
            left, right = current_roi['left'], current_roi['right']
        elif left is not None:
            # 'left' is specified, 'left' is the master.
            if left < min_lr: #Legalize 'left'
                left = min_lr
            elif left > max_lr - min_width + 1:
                left = max_lr - min_width + 1
            else:
                left = 1 + step_lr*((left - 1) // step_lr)
            if right is None: #Now legalize 'right'
                right = current_roi['right']
            if right < left + min_width - 1:
                right = left + min_width - 1
            elif right > max_lr:
                right = max_lr
            else:
                right = left - 1 + step_lr*((right - (left - 1)) // step_lr)
        else:
            # 'left' is unspecified, 'right' is specified. 'right' is the master.
            if right > max_lr: #Legalize 'right'
                right = max_lr
            elif right < min_lr - 1 + min_width:
                right = min_width
            else:
                right = step_lr * (right  // step_lr)
            left = current_roi['left'] #Now legalize 'left'
            if left > right - min_width + 1:
                left = right - min_width + 1
            elif left < min_lr:
                left = min_lr
            else:
                left = right + 1 - step_lr * ((right - (left - 1)) // step_lr)
        assert min_lr <= left < left + min_width - 1 <= right <= max_lr
        # Legalize top/bottom
        if top is None and bottom is None:
            # User isn't trying to change u/d ROI; use existing ROI.
            top, bottom = current_roi['top'], current_roi['bottom']
        elif top is not None:
        # 'top' is specified, 'top' is the master.
            if top < min_ud: #Legalize 'top'
                top = min_ud
            if top > (max_ud - min_height)//2 + 1:
                top = (max_ud - min_height)//2 + 1
            bottom = max_ud - top + 1 #Now bottom is specified
        else:
        # 'top' is unspecified, 'bottom' is specified, 'bottom' is the master.
            if bottom > max_ud: #Legalize 'bottom'
                bottom = max_ud
            if bottom < (max_ud + min_height)//2:
                bottom = (max_ud + min_height)//2
            top = max_ud - bottom + 1 #Now 'top' is specified
        assert min_ud <= top < top + min_height - 1 <= bottom <= max_ud
        new_roi = {'left': left, 'top': top, 'right': right, 'bottom': bottom}
        if verbose and new_roi != roi:
            print(" **Requested ROI must be adjusted to match the camera**")
        return new_roi

    def update_image(self, image):
        q_image = QtGui.QImage(image.data, image.shape[1], image.shape[0], image.strides[0], QtGui.QImage.Format_Grayscale8)
        pixmap = QtGui.QPixmap.fromImage(q_image).scaled(self.image_label.width(), self.image_label.height(), QtCore.Qt.KeepAspectRatio)
        self.image_label.setPixmap(pixmap)

    @QtCore.pyqtSlot()
    def live_preview(self):
        if not self.camera_thread.isRunning():
            self.camera_thread.start()

    @QtCore.pyqtSlot(float)
    def adjust_exposure(self, value):
        self.camera_thread.update_exposure(value)

    @QtCore.pyqtSlot(int)
    def adjust_roi(self, _):
        left_value = self.left_spin_box.value()
        top_value = self.top_spin_box.value()
        right_value = self.right_spin_box.value()
        bottom_value = self.bottom_spin_box.value()

        requested_roi = {'left': left_value, 'top': top_value, 'right': right_value, 'bottom': bottom_value}
        
        # Use the legalize_roi function to adjust the requested ROI
        legal_roi = self.legalize_roi(requested_roi, camera_type='edge 4.2')  # Adjust the camera_type if needed
        
        # Convert the legal ROI to a tuple
        roi_tuple = (legal_roi['left'], legal_roi['top'], legal_roi['right'], legal_roi['bottom'])
        print(f"Setting ROI to: {roi_tuple}")
        
        # Update the ROI in your camera_thread
        self.camera_thread.adjust_roi(roi_tuple)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = CameraPreviewWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()