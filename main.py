import os
import math
import cv2 as cv
import mediapipe as mp


CAPTURE_WIDTH, CAPTURE_HEIGHT = 1280, 720
PATH_IMAGES = "images"
DIRECTORY = os.listdir(PATH_IMAGES)

"""21 hand landmarks"""

WRIST = 0
THUMB_CMC = 1
THUMB_MCP = 2
THUMB_IP = 3
THUMB_TIP = 4
INDEX_FINGER_MCP = 5
INDEX_FINGER_PIP = 6
INDEX_FINGER_DIP = 7
INDEX_FINGER_TIP = 8
MIDDLE_FINGER_MCP = 9
MIDDLE_FINGER_PIP = 10
MIDDLE_FINGER_DIP = 11
MIDDLE_FINGER_TIP = 12
RING_FINGER_MCP = 13
RING_FINGER_PIP = 14
RING_FINGER_DIP = 15
RING_FINGER_TIP = 16
PINKY_MCP = 17
PINKY_PIP = 18
PINKY_DIP = 19
PINKY_TIP = 20


def main():

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
