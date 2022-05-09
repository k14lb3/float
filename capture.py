import cv2 as cv

class Capture:
    def __init__(self, cap_src=0):
        self._cap = cv.VideoCapture(cap_src)
        self._success = False

    def __del__(self):
        if self._cap.isOpened():
            self._cap.release()

    def read(self) :
        success, frame = self._cap.read()
        
        self._success = success

        return success, frame

    def get_success(self):
        return self._success

    def get_width(self):
        return int(self._cap.get(cv.CAP_PROP_FRAME_WIDTH))

    def get_height(self):
        return int(self._cap.get(cv.CAP_PROP_FRAME_HEIGHT))

    def get_fps(self):
        return int(self._cap.get(cv.CAP_PROP_FPS))
