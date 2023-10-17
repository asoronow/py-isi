import pco
import cv2

# Open camera
cam = pco.Camera()

# Start a live preview
CONFIGURATION = {
    'exposure time': 10e-3,
    'delay time': 0,
    'roi': (1, 1, 512, 512),
    'timestamp': 'ascii',
    'pixel rate': 100_000_000,
    'trigger': 'auto sequence',
    'acquire': 'auto',
    'noise filter': 'on',
    'metadata': 'on',
    'binning': (1, 1)
}

def live_preview(camera, shutter_time=100, exposure=10):
    '''
    Generate a live preview of the camera by taking sequential images.

    Args:
        - shutter_time: Shutter time in milliseconds
        - exposure: Exposure time in milliseconds
    '''

    with camera as cam:
        # Set camera parameters
        while True:
            cam.configuration = {
                "exposure time": exposure * 1e-3,
            }
            cam.record(mode="sequence")
            image, meta = cam.image()

            cv2.imshow("Live Preview", image)
            cv2.waitKey(shutter_time)

live_preview(cam)



