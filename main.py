import os
import math
import cv2 as cv
import numpy as np
import mediapipe as mp
import tkinter as tk
from PIL import Image, ImageTk
import pyvirtualcam
from constants import *


class App(tk.Tk):
    def __init__(self, cam, float_images, cap_src=0):
        """Initializes the app.

        Keyword arguments:
        cam -- Virtual cam source.
        float_images -- List of FloatImages objects.
        cap_src -- Capture source.
        """

        tk.Tk.__init__(self)
        self.overrideredirect(True)
        self.cam = cam
        self.cap_src = cap_src
        self.dragging = False
        self.width = 816
        self.height = 582
        self.float_images = float_images
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

    def drag_gesture(self):
        if (
            self.hand_detector.get_distance(
                self.hand_detector.hands_list[0][1][INDEX_FINGER_TIP],
                self.hand_detector.hands_list[0][1][MIDDLE_FINGER_TIP],
            )
            < 40
            and (
                self.hand_detector.hands_list[0][1][INDEX_FINGER_TIP][1]
                < self.hand_detector.hands_list[0][1][INDEX_FINGER_DIP][1]
            )
            and (
                self.hand_detector.hands_list[0][1][MIDDLE_FINGER_TIP][1]
                < self.hand_detector.hands_list[0][1][MIDDLE_FINGER_DIP][1]
            )
        ):

            print(self.hand_detector.hands_list[0][0])
            return True
        return False

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

                self.hand_detector.hands_list = []
                frame = self.hand_detector.find_hands(frame, True)

                for float_image in self.float_images:
                    frame = self.img_draw(frame, float_image)

                frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

                if self.float_images:
                    if self.hand_detector.hands_list:
                        if self.drag_gesture():
                            # Make index finger the cursor
                            cursor = self.hand_detector.hands_list[0][1][
                                INDEX_FINGER_TIP
                            ]
                            for float_image in self.float_images:
                                float_image.drag(cursor)

                self.cam.send(frame)
                self.cam.sleep_until_next_frame()

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

    def overlay_transparent(self, bg, fg, pos=(0, 0)):
        """Overlays a png image over a jpg image.

        Keyword arguments:
        bg -- Background image.
        fg -- Foreground image.
        pos -- Position of foreground over the background.
        Return: Background image overlayed with the foreground image.
        """

        bg_h, bg_w, bg_c = bg.shape
        fg_h, fg_w = fg.shape[:2]
        pos_x, pos_y = pos

        # Create mask from alpha
        *_, fg_alpha = cv.split(fg)

        # Convert mask from foreground to BGRA which
        # is the same size as the foreground to
        # be able to use bitwise operation
        fg_mask_bgra = cv.cvtColor(fg_alpha, cv.COLOR_GRAY2BGRA)
        fg_rgba = cv.bitwise_and(fg, fg_mask_bgra)

        # Convert image to BGR which is the same size
        # as the background mask to be able to use
        # bitwise operation
        fg_rgb = cv.cvtColor(fg_rgba, cv.COLOR_BGRA2BGR)

        # Create a blank image of the same size
        # with the background for the full foreground mask
        fg_mask_full = np.zeros((bg_h, bg_w, bg_c), np.uint8)

        # Replace full foreground mask at the given position
        # with the RGB foreground
        fg_mask_full[pos_y : pos_y + fg_h, pos_x : pos_x + fg_w] = fg_rgb

        # Convert mask from foreground to BGR which
        # is the same size as the background to
        # be able to use bitwise operation
        fg_mask_bgr = cv.cvtColor(fg_alpha, cv.COLOR_GRAY2BGR)

        # Invert mask
        fg_mask_bgr_inv = cv.bitwise_not(fg_mask_bgr)

        # Create a blank image of the same size with the background
        bg_mask_full = np.ones((bg_h, bg_w, bg_c), np.uint8) * 255

        # Replace full background mask at the given position
        # with the RGB foreground
        bg_mask_full[pos_y : pos_y + fg_h, pos_x : pos_x + fg_w] = fg_mask_bgr_inv

        # Mask background
        bg_masked = cv.bitwise_and(bg, bg_mask_full)

        # Put the masked foreground to the masked background
        img = cv.bitwise_or(bg_masked, fg_mask_full)

        return img

    def img_draw(self, frame, float_image):
        pos = []
        frame_h, frame_w = frame.shape[:2]
        w, h = float_image.get_width(), float_image.get_height()
        x, y = float_image.get_pos_x(), float_image.get_pos_y()

        if float_image.is_png():
            # Top Left
            if x <= 0 and y <= 0:
                pos = (0, 0)
            # Top Right
            elif x >= frame_w - w and y <= 0:
                pos = (frame_w - w, 0)
            # Bottom Right
            elif x >= frame_w - w and y >= frame_h - h:
                pos = (frame_w - w, frame_h - h)
            # Bottom Left
            elif x <= 0 and y >= frame_h - h:
                pos = (0, frame_h - h)
            # Top
            elif y <= 0:
                pos = (x, 0)
            # Right
            elif x >= frame_w - w:
                pos = (frame_w - w, y)
            # Bottom
            elif y >= frame_h - h:
                pos = (x, frame_h - h)
            # Left
            elif x <= 0:
                pos = (0, y)
            else:
                pos = (x, y)

            frame[:] = self.overlay_transparent(frame, float_image.img, pos)
        else:
            # Top Left
            if x <= 0 and y <= 0:
                pos = slice(0, h), slice(0, w)
            # Top Right
            elif x >= frame_w - w and y <= 0:
                pos = slice(0, h), slice(frame_w - w, frame_w)
            # Bottom Right
            elif x >= frame_w - w and y >= frame_h - h:
                pos = slice(frame_h - h, frame_h), slice(frame_w - w, frame_w)
            # Bottom Left
            elif x <= 0 and y >= frame_h - h:
                pos = slice(frame_h - h, frame_h), slice(0, w)
            # Top
            elif y <= 0:
                pos = slice(0, h), slice(x, x + w)
            # Right
            elif x >= frame_w - w:
                pos = slice(y, y + h), slice(frame_w - w, frame_w)
            # Bottom
            elif y >= frame_h - h:
                pos = slice(frame_h - h, frame_h), slice(x, x + w)
            # Left
            elif x <= 0:
                pos = slice(y, y + h), slice(0, w)
            else:
                pos = slice(y, y + h), slice(x, x + w)

            frame[pos] = float_image.img

        return frame

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
        title.bind("<ButtonRelease-1>", self.win_drag__release)

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
    def __init__(self, cap_src=0):
        self.cap = cv.VideoCapture(cap_src)
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_hands = mp.solutions.hands

    def get_video_capture_frame(self):
        if self.cap.isOpened():
            success, frame = self.cap.read()

            if success:
                return (success, cv.flip(frame, 1))

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
        """Initializes hand detector.

        Keyword arguments:
        static_image_mode -- Whether to treat the input images as a batch of static
            and possibly unrelated images, or a video stream.
        max_num_hands -- Maximum number of hands to detect.
        min_detection_confidence -- Minimum confidence value ([0.0, 1.0]) for hand
            detection to be considered successful.
        min_tracking_confidence -- Minimum confidence value ([0.0, 1.0]) for the
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

        Keyword arguments:
        frame: Image to detect hands in.
        draw: Draw the output on the image.
        Return: Returns an image if draw is True.
        """

        img = cv.cvtColor(img, cv.COLOR_BGR2RGB)

        img.flags.writeable = False

        results = self.hands.process(img)

        img.flags.writeable = True

        img = cv.cvtColor(img, cv.COLOR_RGB2BGR)

        (
            h,
            w,
        ) = img.shape[:2]

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

                self.hands_list.append(hand)

                if draw:
                    self.mp_drawing.draw_landmarks(
                        img,
                        hand_landmarks,
                        self.mp_hands.HAND_CONNECTIONS,
                    )

        return img

    def get_distance(self, p1, p2):
        x1, y1 = p1
        x2, y2 = p2
        dist = math.hypot(x2 - x1, y2 - y1)
        return dist


class FloatImage:
    def __init__(self, path, pos):
        """Initializes an interactable image using hand gestures.

        Keyword arguments:
        path -- File path of the image.
        pos -- Position of the image.
        """

        self.path = path
        self.pos = pos

        if "png" in os.path.splitext(self.path)[1]:
            self.img = cv.imread(self.path, cv.IMREAD_UNCHANGED)
            self.png = True
        else:
            self.img = cv.imread(self.path)
            self.png = False

        self.size = self.img.shape[:2]

    def drag(self, cursor):
        cursor_x, cursor_y = cursor
        x, y = self.get_pos_x(), self.get_pos_y()
        w, h = self.get_width(), self.get_height()
        if x < cursor_x < x + w and y < cursor_y < y + h:
            self.set_pos_x(cursor_x - w // 2)
            self.set_pos_y(cursor_y - h // 2)

    def is_png(self):
        return self.png

    def get_width(self):
        return self.size[1]

    def get_height(self):
        return self.size[0]

    def get_pos_x(self):
        return self.pos[0]

    def get_pos_y(self):
        return self.pos[1]

    def set_width(self, w):
        self.size = (self.size[0], w)

    def set_height(self, h):
        self.size = (h, self.size[1])

    def set_pos_x(self, x):
        self.pos = (x, self.pos[1])

    def set_pos_y(self, y):
        self.pos = (self.pos[0], y)


def main():

    dir_images = os.listdir(PATH_IMAGES)
    float_images = []

    for i, PATH_IMAGE in enumerate(dir_images):
        float_images.append(
            FloatImage(f"{PATH_IMAGES}/{PATH_IMAGE}", (50 + i * 300, 100))
        )

    with pyvirtualcam.Camera(width=1280, height=720, fps=60) as cam:
        app = App(cam, float_images)
        app.mainloop()


if __name__ == "__main__":
    main()
