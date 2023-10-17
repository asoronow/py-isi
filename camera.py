import pco
import cv2

# Start a live preview
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

def live_preview(shutter_time=100, exposure=10):
    '''
    Generate a live preview of the camera by taking sequential images.

    Args:
        - shutter_time: Shutter time in milliseconds
        - exposure: Exposure time in milliseconds
    '''
    camera = pco.Camera()
    print("Started preview with exposure {:.2f} ms".format(exposure))
    with camera as cam:
        # Set camera parameters
        while True:
            cam.configuration = {
                "exposure time": exposure * 1e-3,
                "roi": (1, 1, 2048, 2048),
            }
            cam.record(mode="sequence")
            image, meta = cam.image()
            
            # Resize image 720 x 1024
            image = cv2.resize(image, (1024, 720))
            cv2.imshow("Live Preview", image)
            
            if ord("q") == cv2.waitKey(shutter_time):
                break

def main():
    live_preview(exposure=20)


if __name__ == "__main__":
    main()