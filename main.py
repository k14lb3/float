import os
import cv2 as cv
import mediapipe as mp
import tkinter as tk
from PIL import Image, ImageTk
from constants import *


class App(tk.Tk):
    def __init__(self, capture_source=0):
        tk.Tk.__init__(self)
        self.overrideredirect(True)
        self.cap_src = capture_source
        self.dragging = False
        self.width = 816
        self.height = 582
        self.geometry(
            f"{self.width}x{self.height}"
            f"+{self.winfo_screenwidth()//2 - self.width//2}"
            f"+{self.winfo_screenheight()//2 - self.height//2}"
        )
        self.configure(bg=COLOR_GRAY)
        self.init_images()
        self.init_title_bar()
        self.init_btn_settings()
        self.init_btn_import()
        self.init_capture()
        self.hand_detector = HandDetector()
        self.update_capture()

    def update_capture(self):
        if not self.dragging:

            def frame_resize(img):
                # Resize by maintaining the aspect ratio by determining what is
                # the percentage of the height relative to the original height in pixels.
                # And then multiplying the original the original width to that percentage.
                base_height = CAPTURE_HEIGHT
                height_percent = base_height / float(img.size[1])
                width = int((float(img.size[0]) * float(height_percent)))
                return img.resize((width, base_height), Image.ANTIALIAS)

            success, frame = self.cap.get_video_capture_frame()

            if success:

                frame = cv.flip(frame, 1)

                frame = self.hand_detector.find_hands(frame, True)

                frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
                
                frame_arr = Image.fromarray(frame)
                frame_arr = frame_resize(frame_arr)
                self.cap_frame = ImageTk.PhotoImage(image=frame_arr)
                if self.cap_frame.height() != CAPTURE_WIDTH:
                    self.canvas_camera.create_image(
                        ((CAPTURE_WIDTH // 2) - (frame_arr.size[0] // 2)),
                        0,
                        image=self.cap_frame,
                        anchor=tk.NW,
                    )
                else:
                    self.canvas_camera.create_image(
                        0, 0, image=self.cap_frame, anchor=tk.NW
                    )

        self.after(10, self.update_capture)

    def init_capture(self):
        self.cap = Capture(self.cap_src)

        self.canvas_camera = tk.Canvas(self, bg=COLOR_BLACK, highlightthickness=0)
        self.canvas_camera.place(
            width=CAPTURE_WIDTH,
            height=CAPTURE_HEIGHT,
            x=48,
            y=128,
        )

    def init_btn_settings(self):
        btn_settings = tk.Label(self, image=self.img_cog, bg=COLOR_GRAY, cursor="hand2")
        btn_settings.place(width=56, height=56, x=self.width - 56 - 48, y=49)

    def init_btn_import(self):
        btn_import = tk.Label(
            self, image=self.img_file_image, bg=COLOR_BLUE, cursor="hand2"
        )
        btn_import.place(width=56, height=56, x=48, y=49)

    def init_title_bar(self):
        # Create base
        title_bar = tk.Frame(self, bg=COLOR_BLACK, relief="flat")
        title_bar.place(width=self.width, height=25, x=0, y=0)

        title_bar.bind("<Button-1>", self.win_drag__init)
        title_bar.bind("<B1-Motion>", self.win_drag)
        title_bar.bind("<ButtonRelease-1>", self.win_drag__release)

        # Create title
        title = tk.Label(
            title_bar, text="Float", font="Consolas 18 bold", fg="#01ADB5", bg="#232934"
        )
        title.pack(side="left")
        title.bind("<Button-1>", self.win_drag__init)
        title.bind("<B1-Motion>", self.win_drag)

        # Create minimize button
        btn_minimize = tk.Label(
            title_bar,
            bg=COLOR_BLACK,
            image=self.img_minimize,
        )
        btn_minimize.bind(
            "<Enter>", lambda _: btn_minimize.config(background="#343d4a")
        )
        btn_minimize.bind(
            "<Leave>", lambda _: btn_minimize.config(background=COLOR_BLACK)
        )
        btn_minimize.bind("<Button-1>", self.win_minimize)
        btn_minimize.place(height=25, width=50, x=self.width - 100, y=0)

        # Create close button
        btn_close = tk.Label(
            title_bar,
            bg=COLOR_BLACK,
            image=self.img_close,
        )
        btn_close.bind("<Enter>", lambda _: btn_close.config(background="#ed4245"))
        btn_close.bind("<Leave>", lambda _: btn_close.config(background=COLOR_BLACK))
        btn_close.bind("<Button-1>", lambda _: self.destroy())
        btn_close.place(height=25, width=50, x=self.width - 50, y=0)

    def win_drag__init(self, e):
        # Get cursor position relative to the window
        self.cursor_rel_x, self.cursor_rel_y = e.x, e.y
        self.dragging = True

    def win_drag(self, e):
        self.geometry(
            f"+{e.x_root - self.cursor_rel_x}" f"+{e.y_root - self.cursor_rel_y}"
        )

    def win_drag__release(self, _):
        self.dragging = False

    def win_minimize(self, _):
        self.withdraw()
        self.overrideredirect(False)
        self.iconify()
        self.attributes("-alpha", 0.0)
        self.bind("<Map>", self.win_restore)

    def win_restore(self, _):
        self.overrideredirect(True)
        self.attributes("-alpha", 1.0)
        self.unbind("<Map>")

    def init_images(self):
        self.img_minimize = tk.PhotoImage(file=PATH_ICONS + "minimize.png")
        self.img_close = tk.PhotoImage(file=PATH_ICONS + "close.png")
        self.img_cog = tk.PhotoImage(file=PATH_ICONS + "cog.png")
        self.img_file_image = tk.PhotoImage(file=PATH_ICONS + "file-image.png")


class Capture:
    def __init__(self, src=0):
        self.cap = cv.VideoCapture(src)
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_hands = mp.solutions.hands

    def get_video_capture_frame(self):
        if self.cap.isOpened():
            success, frame = self.cap.read()

            if success:
                return (success, frame)

    def __del__(self):
        if self.cap.isOpened():
            self.cap.release()


class HandDetector:
    def __init__(
        self,
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ):
        """Initializes hand detector

        Args:
        static_image_mode: Whether to treat the input images as a batch of static
            and possibly unrelated images, or a video stream.
        max_num_hands: Maximum number of hands to detect.
        min_detection_confidence: Minimum confidence value ([0.0, 1.0]) for hand
            detection to be considered successful.
        min_tracking_confidence: Minimum confidence value ([0.0, 1.0]) for the
            hand landmarks to be considered tracked successfully.
        """
        self.static_image_mode = static_image_mode
        self.max_num_hands = max_num_hands
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence

        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            self.static_image_mode,
            self.max_num_hands,
            self.min_detection_confidence,
            self.min_tracking_confidence,
        )
        self.hands_list = []

    def find_hands(self, img, draw=False):
        """Finds hands in an image.

        frame: Image to detect hands in.
        draw: Draw the output on the image.
        return: Image.
        """

        img = cv.cvtColor(img, cv.COLOR_BGR2RGB)

        img.flags.writeable = False

        results = self.hands.process(img)

        img.flags.writeable = True

        img = cv.cvtColor(img, cv.COLOR_RGB2BGR)

        w, h, _ = img.shape

        if results.multi_hand_landmarks:
            for handedness, hand_landmarks in zip(
                results.multi_handedness, results.multi_hand_landmarks
            ):
                hand = []
                if handedness.classification[0].label == "Left":
                    hand.append("Right")
                else:
                    hand.append("Left")

                hand.append([])
                for landmark in list(hand_landmarks.landmark):
                    hand[1].append(
                        (
                            int(landmark.x * w),
                            int(landmark.y * h),
                        )
                    )

                self.hands_list.append(hand)

                if draw:
                    self.mp_drawing.draw_landmarks(
                        img,
                        hand_landmarks,
                        self.mp_hands.HAND_CONNECTIONS,
                    )

        return img

def main():

    dir_images = os.listdir(PATH_IMAGES)

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
