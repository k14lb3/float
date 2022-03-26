import cv2 as cv

class Capture:
    def __init__(self, cap_src=0):
        self._cap = cv.VideoCapture(cap_src)

    def get_video_capture_frame(self):
        if self._cap.isOpened():
            success, frame = self._cap.read()

            if success:
                return (success, frame)

    def __del__(self):
        if self._cap.isOpened():
            self._cap.release()

