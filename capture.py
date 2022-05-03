import cv2 as cv

class Capture:
    def __init__(self, cap_src=0):
        self._cap = cv.VideoCapture(cap_src)

    def __del__(self):
        if self._cap.isOpened():
            self._cap.release()

    def __call__(self):
        return self._cap

    def get_width(self):
        return int(self._cap.get(cv.CAP_PROP_FRAME_WIDTH))

    def get_height(self):
        return int(self._cap.get(cv.CAP_PROP_FRAME_HEIGHT))

    def get_fps(self):
        return int(self._cap.get(cv.CAP_PROP_FPS))
