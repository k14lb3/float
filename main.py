import os
import math
import cv2 as cv
import mediapipe as mp
from constants import *


def main():

    dir_images = os.listdir(PATH_IMAGES)

    mp_drawing = mp.solutions.drawing_utils
    mp_hands = mp.solutions.hands

    cap = cv.VideoCapture(0)
    cap.set(3, CAPTURE_WIDTH)
    cap.set(4, CAPTURE_HEIGHT)

    with mp_hands.Hands(
        min_detection_confidence=0.5, min_tracking_confidence=0.5
    ) as hands:
        while cap.isOpened():
            success, frame = cap.read()

            frame.flags.writeable = False
            frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
            results = hands.process(frame)

            frame.flags.writeable = True
            frame = cv.cvtColor(frame, cv.COLOR_RGB2BGR)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                    )

            cv.imshow("Float", cv.flip(frame, 1))

            if cv.waitKey(1) & 0xFF == ord("q"):
                break

        cap.release()


if __name__ == "__main__":
    main()
