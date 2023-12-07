import sys
import pco
import numpy as np
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QMessageBox
from pathlib import Path
from datetime import datetime
import os
from PyQt5.QtCore import QTimer
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

    def __init__(self, exposure_time=10e-3, delay_time=0):
        super(CameraThread, self).__init__()
        self.exposure_time = exposure_time
        self.delay_time = delay_time
        self.roi = (1, 1, 2048, 2048)
        self.running = False  # Flag to control the running of the thread

    def run(self):
        self.running = True
        camera = pco.Camera()
        with camera as cam:
            while self.running:
                cam.configuration = {
                    "exposure time": self.exposure_time,
                    "delay time": self.delay_time,  # Use the updated delay time value
                    "roi": self.roi,  # Use the updated ROI value
                }
                cam.record(mode="sequence")
                image, meta = cam.image()

                # Convert to 8-bit if the image is 16-bit
                if image.dtype == np.uint16:
                    image = (image / 256).astype(np.uint8)

                if not self.running:
                    break  # Break the loop if running is set to False
                    
                # Emit the processed image
                self.image_signal.emit(image)
    def stop(self):
        self.running = False  # Set the flag to False to stop the loop

    def update_exposure(self, exposure_time):
        self.exposure_time = float(exposure_time * 1e-3)

    def adjust_roi(self, roi):
        self.roi = roi

class CameraPreviewWindow(QtWidgets.QWidget):
    def __init__(self):
        super(CameraPreviewWindow, self).__init__()

        self.save_location = None  # Initialize the save location

        # Add a timer for continuous capture
        self.capture_timer = QTimer(self)
        self.capture_timer.timeout.connect(self.capture_continuous)

        # Set window title and initial size
        self.setWindowTitle("PCO Camera Live Preview")
        self.resize(1024, 720)

        self.image_label = QtWidgets.QLabel(self)
        self.image_label.setFixedSize(1024, 700)
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)  # Center the image in QLabel

        # Select Save Path Button
        self.select_save_path_button = QtWidgets.QPushButton("Select Save Path", self)
        self.select_save_path_button.clicked.connect(self.select_save_path)

        # Start Preview Button
        self.start_button = QtWidgets.QPushButton("Start Preview", self)
        self.start_button.clicked.connect(self.live_preview)

        # Stop Preview Button
        self.stop_button = QtWidgets.QPushButton("Stop Preview", self)
        self.stop_button.clicked.connect(self.stop_preview)
        # Initially disable the stop button as there is no preview to stop
        self.stop_button.setEnabled(False)

        # Single Capture Button
        self.single_capture_button = QtWidgets.QPushButton("Single Capture", self)
        self.single_capture_button.clicked.connect(self.single_capture)
        self.single_capture_button.setEnabled(False)  # Initially disable the button

        # Record Button
        self.record_button = QtWidgets.QPushButton("Record", self)
        self.record_button.clicked.connect(self.start_recording)
        self.record_button.setEnabled(False)  # Initially disable the button

        # Stop Record Button
        self.stop_record_button = QtWidgets.QPushButton("Stop Record", self)
        self.stop_record_button.clicked.connect(self.stop_recording)
        self.stop_record_button.setEnabled(False)  # Disable the button initially

        # Spin box for Exposure Time
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

        # Spin box for Delay Time adjustments
        self.delay_spin_box = QtWidgets.QDoubleSpinBox(self)
        self.delay_spin_box.setRange(0, 1000)  # Adjust the range as needed
        self.delay_spin_box.setDecimals(1) 
        self.delay_spin_box.setValue(0.0)  # Initial value
        self.delay_spin_box.setSingleStep(0.5)  # Setting step size to 0.5
        self.delay_spin_box.valueChanged.connect(self.adjust_delay)

        # Set the font to bold for the ROI labels
        bold_font = QtGui.QFont()
        bold_font.setBold(True)

        # Horizontal layouts for each ROI spin box with bold labels
        left_roi_label = QtWidgets.QLabel("Left ROI:")
        left_roi_label.setFont(bold_font)
        left_roi_layout = QtWidgets.QHBoxLayout()
        left_roi_layout.addWidget(left_roi_label)
        left_roi_layout.addWidget(self.left_spin_box)

        top_roi_label = QtWidgets.QLabel("Top ROI:")
        top_roi_label.setFont(bold_font)
        top_roi_layout = QtWidgets.QHBoxLayout()
        top_roi_layout.addWidget(top_roi_label)
        top_roi_layout.addWidget(self.top_spin_box)

        right_roi_label = QtWidgets.QLabel("Right ROI:")
        right_roi_label.setFont(bold_font)
        right_roi_layout = QtWidgets.QHBoxLayout()
        right_roi_layout.addWidget(right_roi_label)
        right_roi_layout.addWidget(self.right_spin_box)

        bottom_roi_label = QtWidgets.QLabel("Bottom ROI:")
        bottom_roi_label.setFont(bold_font)
        bottom_roi_layout = QtWidgets.QHBoxLayout()
        bottom_roi_layout.addWidget(bottom_roi_label)
        bottom_roi_layout.addWidget(self.bottom_spin_box)

        # Right-side layout for controls
        control_layout = QtWidgets.QVBoxLayout()

        # Add the Select Save Path button to the layout
        control_layout.addWidget(self.select_save_path_button)
        
        # Add the start button to the layout
        control_layout.addWidget(self.start_button)
    
        # Add the stop button to the layout
        control_layout.addWidget(self.stop_button)

        # Add the Single Capture button to the layout
        control_layout.addWidget(self.single_capture_button)

        # Add the Record button to the layout
        control_layout.addWidget(self.record_button)

        # Add the Stop Record button to the layout
        control_layout.addWidget(self.stop_record_button)

        # Horizontal layout for Exposure Time
        exposure_time_layout = QtWidgets.QHBoxLayout()
        exposure_label = QtWidgets.QLabel("Exposure Time:")
        exposure_label.setFont(bold_font)  # Set the font to bold if you want
        exposure_time_layout.addWidget(exposure_label)
        exposure_time_layout.addWidget(self.spin_box)
        # Adding the Exposure Time layout to the control layout
        control_layout.addLayout(exposure_time_layout)

        # Add the ROI layouts to the control layout
        control_layout.addLayout(left_roi_layout)
        control_layout.addLayout(top_roi_layout)
        control_layout.addLayout(right_roi_layout)
        control_layout.addLayout(bottom_roi_layout)

        # Horizontal layout for Delay Time
        delay_time_layout = QtWidgets.QHBoxLayout()
        delay_label = QtWidgets.QLabel("Delay Time")
        delay_label.setFont(bold_font)  # Optional: Set the font to bold if desired
        delay_time_layout.addWidget(delay_label)
        delay_time_layout.addWidget(self.delay_spin_box)
        # Add the Delay Time layout to the control layout
        control_layout.addLayout(delay_time_layout)

        #Main layout
        main_layout = QtWidgets.QHBoxLayout()
        main_layout.addWidget(self.image_label)
        main_layout.addLayout(control_layout)

        self.setLayout(main_layout)
        self.save_location = None  # Initialize the save location
        self.current_recording_path = None
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
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)

            # Enable the Single Capture and Record buttons
            self.single_capture_button.setEnabled(True)
            self.record_button.setEnabled(True)

            print("Live preview started.")
        else:
            print("Live preview is already running.")



    def select_save_path(self):
        """
        Opens a dialog for the user to select a directory where images will be saved.
        """
        selected_directory = QFileDialog.getExistingDirectory(self, "Select Directory", str(Path.home()))

        if selected_directory:
            self.save_location = selected_directory
            print(f"Save path selected: {self.save_location}")
        else:
            print("No directory was selected.")

    @QtCore.pyqtSlot()
    def stop_preview(self):
        if self.camera_thread.isRunning():
            self.camera_thread.stop()  # Stop the camera thread
            self.camera_thread.wait()  # Wait for the thread to fully stop
        
            # Re-enable the start button as the preview has stopped
            self.start_button.setEnabled(True)

            # Optionally disable the stop button as there is no preview to stop
            self.stop_button.setEnabled(False)

            self.image_label.clear()   # Clear the image label
            print("Camera thread stopped.")
        else:
            print("Camera thread is not running.")

    def single_capture(self):
        if not self.save_location:
            QMessageBox.warning(self, "No Save Path", "Please select a save path before capturing an image.")
            return

        try:
            pixmap = self.image_label.grab()
            if not pixmap.isNull():
                now = datetime.now()
                timestamp = now.strftime("%Y%m%d_%H%M%S")
                file_name = f"Image_{timestamp}.png"
                file_path = Path(self.save_location) / file_name

                if pixmap.save(str(file_path), 'PNG'):
                    print(f"Image captured and saved as {file_path}")
                else:
                    print("Failed to save the image.")
            else:
                print("No image available for capture.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def start_recording(self):
        if not self.save_location:  
            QMessageBox.warning(self, "No Save Path", "Please select a save path before starting the recording.")
            return

        now = datetime.now()
        folder_name = now.strftime("Recording_%Y%m%d_%H%M%S")
        self.current_recording_path = Path(self.save_location) / folder_name
        self.current_recording_path.mkdir(parents=True, exist_ok=True)

        self.capture_timer.start(1000)
        self.record_button.setEnabled(False)
        self.stop_record_button.setEnabled(True)
        self.single_capture_button.setEnabled(False)
        self.stop_button.setEnabled(False)  # Disable the Stop Preview button
        print(f"Recording started in {self.current_recording_path}")


    def stop_recording(self):
        """
        Stops the continuous capture for recording.
        """
        self.capture_timer.stop()  
        self.record_button.setEnabled(True)
        self.stop_record_button.setEnabled(False)
        self.single_capture_button.setEnabled(True)
        self.stop_button.setEnabled(True)  # Re-enable the Stop Preview button
        print("Recording stopped.")

    def capture_continuous(self):
        """
        Captures the current preview image and saves it in the current recording folder.
        """
        if self.current_recording_path:
            pixmap = self.image_label.grab()
            if not pixmap.isNull():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_name = f"Image_{timestamp}.png"
                file_path = self.current_recording_path / file_name

                if pixmap.save(str(file_path), 'PNG'):
                    print(f"Image captured and saved as {file_path}")
                else:
                    print(f"Failed to save image as {file_path}")
            else:
                print("No image available for capture or QPixmap is invalid.")
        else:
            print("Recording folder not set. Cannot capture image.")

    @QtCore.pyqtSlot(float)
    def adjust_exposure(self, value):
        self.camera_thread.update_exposure(value)

    @QtCore.pyqtSlot(float)
    def adjust_delay(self, value):
        delay_time = value  # No need to call self.delay_spin_box.value() since value is passed as an argument
        # Now you can use the delay_time value for your camera or any other operation
        # e.g., set it to your camera's configuration or use it in a QTimer, etc.

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