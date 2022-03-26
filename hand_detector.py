import mediapipe as mp
from math import hypot
import cv2 as cv


class HandDetector:
    def __init__(
        self,
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ):
        """Initializes hand detector.

        Arguments:
            static_image_mode: Whether to treat the input images as a batch of static
            and possibly unrelated images, or a video stream.
            max_num_hands: Maximum number of hands to detect.
            min_detection_confidence: Minimum confidence value ([0.0, 1.0]) for hand
            detection to be considered successful.
            min_tracking_confidence: Minimum confidence value ([0.0, 1.0]) for the
            hand landmarks to be considered tracked successfully.
        """
        self._static_image_mode = static_image_mode
        self._max_num_hands = max_num_hands
        self._min_detection_confidence = min_detection_confidence
        self._min_tracking_confidence = min_tracking_confidence

        self._mp_hands = mp.solutions.hands
        self._mp_drawing = mp.solutions.drawing_utils
        self._hands = self._mp_hands.Hands(
            self._static_image_mode,
            self._max_num_hands,
            self._min_detection_confidence,
            self._min_tracking_confidence,
        )
        self._hands_list = []

    def find_hands(self, img, draw=False):
        """Finds hands in an image.

        Arguments:
            frame: Image to detect hands in.
            draw: Draw the output on the image.

        Return:
            Image.
        """

        img = cv.cvtColor(img, cv.COLOR_BGR2RGB)

        # Prevents copying of image; increases process performance.
        img.flags.writeable = False

        results = self._hands.process(img)

        img.flags.writeable = True

        img = cv.cvtColor(img, cv.COLOR_RGB2BGR)

        h, w = img.shape[:2]

        if results.multi_hand_landmarks:
            for handedness, hand_landmarks in zip(
                results.multi_handedness, results.multi_hand_landmarks
            ):
                hand = []
                hand.append(handedness.classification[0].label)
                hand.append([])
                for landmark in list(hand_landmarks.landmark):
                    hand[1].append(
                        (
                            int(landmark.x * w),
                            int(landmark.y * h),
                        )
                    )

                self._hands_list.append(hand)

                if draw:
                    self._mp_drawing.draw_landmarks(
                        img,
                        hand_landmarks,
                        self._mp_hands.HAND_CONNECTIONS,
                    )

        return img

    def get_distance(self, p1, p2):
        x1, y1 = p1
        x2, y2 = p2
        dist = hypot(x2 - x1, y2 - y1)
        return dist

    def reset_hands_list(self):
        self._hands_list = []
