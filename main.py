import os
import math
from ctypes import windll
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
        self.configure(bg=COLOR_GRAY)
        self.init_variables(cam, float_images, cap_src)
        self.init_icons()
        self.init_title_bar()
        self.init_btn_settings()
        self.init_btn_import()
        self.init_capture()
        self.init_cam_preview_switch()
        self.init_gesture_control_switch()
        self.update_capture()
        self.after(10, lambda: self.set_appwindow())
        self.title("Float")
        self.iconbitmap("icon.ico")
        self.center_window()
        windll.shell32.SetCurrentProcessExplicitAppUserModelID('mycompany.myproduct.subproduct.version')

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
                    if float_image.is_visible():
                        frame = self.img_draw(frame, float_image)

                frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

                if self.float_images:
                    if self.gesture_control:
                        self.check_gestures()

                self.cam.send(frame)
                self.cam.sleep_until_next_frame()

                if self.cam_preview:
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
                else:
                    self.canvas_camera.delete(tk.ALL)
                    self.canvas_camera.create_text(
                        216,
                        184,
                        text="Preview disabled",
                        fill=COLOR_WHITE,
                        font="Consolas 24",
                        anchor=tk.NW,
                    )

        self.after(10, self.update_capture)

    def check_gestures(self):
        for hand in self.hand_detector.hands_list:
            if self.GESTURES[GESTURE_DRAG](hand):
                # Make index finger the cursor
                cursor = hand[1][INDEX_FINGER_TIP]
                for float_image in self.float_images:
                    float_image.drag(cursor)

        if len(self.hand_detector.hands_list) > 1:
            for i in range(2):
                if self.GESTURES[GESTURE_DELETE](self.hand_detector.hands_list[i]):
                    hand = self.hand_detector.hands_list[(i + 1) % 2]
                    if hand[1][INDEX_FINGER_TIP][1] < hand[1][INDEX_FINGER_DIP][1]:
                        cursor = hand[1][INDEX_FINGER_TIP]
                        for float_image in self.float_images:
                            float_image.delete(cursor)

    def img_draw(self, frame, float_image):
        def overlay_transparent(bg, fg, pos=(0, 0)):
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

            frame[:] = overlay_transparent(frame, float_image.img, pos)
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

    def center_window(self):
        self.geometry(
            f"{self.width}x{self.height}"
            f"+{self.winfo_screenwidth()//2 - self.width//2}"
            f"+{self.winfo_screenheight()//2 - self.height//2}"
        )

    def set_appwindow(self):
        hwnd = windll.user32.GetParent(self.winfo_id())
        style = windll.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        style = style & ~WS_EX_TOOLWINDOW
        style = style | WS_EX_APPWINDOW
        windll.user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style)
        self.wm_withdraw()
        self.after(10, lambda: self.wm_deiconify())

    def init_cam_preview_switch(self):
        def toggle_cam_preview(switch):
            if self.cam_preview:
                switch.config(image=self.img_toggle_switch_off)
            else:
                switch.config(image=self.img_toggle_switch_on)
            self.cam_preview = not self.cam_preview

        label = tk.Label(
            self,
            text="Camera Preview",
            font="Consolas 14",
            fg=COLOR_WHITE,
            bg=COLOR_GRAY,
            bd=-2,
        )
        label.place(x=48, y=543)

        toggle_switch = tk.Label(
            self, image=self.img_toggle_switch_on, bg=COLOR_GRAY, cursor="hand2"
        )
        toggle_switch.place(w=42, h=21, x=198, y=544)

        toggle_switch.bind("<Button-1>", lambda _: toggle_cam_preview(toggle_switch))

    def init_gesture_control_switch(self):
        def toggle_gesture_control(switch):
            if self.gesture_control:
                switch.config(image=self.img_toggle_switch_off)
            else:
                switch.config(image=self.img_toggle_switch_on)
            self.gesture_control = not self.gesture_control

        label = tk.Label(
            self,
            text="Gesture Control",
            font="Consolas 14",
            fg=COLOR_WHITE,
            bg=COLOR_GRAY,
            bd=-2,
        )
        label.place(x=280, y=543)
        toggle_switch = tk.Label(
            self, image=self.img_toggle_switch_on, bg=COLOR_GRAY, cursor="hand2"
        )
        toggle_switch.place(w=42, h=21, x=440, y=544)

        toggle_switch.bind(
            "<Button-1>", lambda _: toggle_gesture_control(toggle_switch)
        )

    def init_capture(self):
        self.cap = Capture(self.cap_src)

        self.canvas_camera = tk.Canvas(self, bg=COLOR_BLACK, highlightthickness=0)
        self.canvas_camera.place(
            w=CAPTURE_WIDTH,
            h=CAPTURE_HEIGHT,
            x=48,
            y=128,
        )

    def init_btn_settings(self):
        btn_settings = tk.Label(self, image=self.img_cog, bg=COLOR_GRAY, cursor="hand2")
        btn_settings.place(w=56, h=56, x=self.width - 56 - 48, y=49)

    def init_btn_import(self):
        btn_import = tk.Label(
            self, image=self.img_file_image, bg=COLOR_BLUE, cursor="hand2"
        )
        btn_import.place(w=56, h=56, x=48, y=49)

    def init_title_bar(self):
        def win_drag__init(e):
            # Get cursor position relative to the window
            self.cursor_rel_x, self.cursor_rel_y = e.x, e.y
            self.dragging = True

        def win_drag(e):
            self.geometry(
                f"+{e.x_root - self.cursor_rel_x}" f"+{e.y_root - self.cursor_rel_y}"
            )

        def win_drag__release():
            self.dragging = False

        def win_minimize():
            self.withdraw()
            self.overrideredirect(False)
            self.iconify()
            self.attributes("-alpha", 0.0)
            self.bind("<Map>", lambda _: win_restore())

        def win_restore():
            self.overrideredirect(True)
            self.after(10, lambda: self.set_appwindow())
            self.attributes("-alpha", 1.0)
            self.unbind("<Map>")

        # Create base
        title_bar = tk.Frame(self, bg=COLOR_BLACK, relief="flat")
        title_bar.place(w=self.width, h=25, x=0, y=0)

        title_bar.bind("<Button-1>", win_drag__init)
        title_bar.bind("<B1-Motion>", win_drag)
        title_bar.bind("<ButtonRelease-1>", lambda _: win_drag__release())

        # Create title
        title = tk.Label(
            title_bar, text="Float", font="Consolas 18 bold", fg="#01ADB5", bg="#232934"
        )
        title.pack(side="left")
        title.bind("<Button-1>", win_drag__init)
        title.bind("<B1-Motion>", win_drag)
        title.bind("<ButtonRelease-1>", lambda _: win_drag__release())

        # Create minimize button
        btn_minimize = tk.Label(
            title_bar,
            bg=COLOR_BLACK,
            image=self.img_minimize,
        )
        btn_minimize.bind(
            "<Enter>", lambda _: btn_minimize.config(bg="#343d4a")
        )
        btn_minimize.bind(
            "<Leave>", lambda _: btn_minimize.config(bg=COLOR_BLACK)
        )
        btn_minimize.bind("<Button-1>", lambda _: win_minimize())
        btn_minimize.place(h=25, w=50, x=self.width - 100, y=0)

        # Create close button
        btn_close = tk.Label(
            title_bar,
            bg=COLOR_BLACK,
            image=self.img_close,
        )
        btn_close.bind("<Enter>", lambda _: btn_close.config(bg="#ed4245"))
        btn_close.bind("<Leave>", lambda _: btn_close.config(bg=COLOR_BLACK))
        btn_close.bind("<Button-1>", lambda _: self.destroy())
        btn_close.place(h=25, w=50, x=self.width - 50, y=0)

    def init_icons(self):
        self.img_minimize = tk.PhotoImage(file=PATH_ICONS + "minimize.png")
        self.img_close = tk.PhotoImage(file=PATH_ICONS + "close.png")
        self.img_cog = tk.PhotoImage(file=PATH_ICONS + "cog.png")
        self.img_file_image = tk.PhotoImage(file=PATH_ICONS + "file-image.png")
        self.img_toggle_switch_off = tk.PhotoImage(
            file=PATH_ICONS + "toggle-switch/off.png"
        )
        self.img_toggle_switch_on = tk.PhotoImage(
            file=PATH_ICONS + "toggle-switch/on.png"
        )

    def init_variables(self, cam, float_images, cap_src):
        self.cam = cam
        self.float_images = float_images
        self.cap_src = cap_src
        self.width = 816
        self.height = 591
        self.hand_detector = HandDetector()
        self.dragging = False
        self.cam_preview = True
        self.gesture_control = True
        self.GESTURES = {
            GESTURE_DRAG: lambda hand: self.hand_detector.get_distance(
                hand[1][INDEX_FINGER_TIP],
                hand[1][MIDDLE_FINGER_TIP],
            )
            < 40
            and (hand[1][INDEX_FINGER_TIP][1] < hand[1][INDEX_FINGER_DIP][1])
            and (hand[1][MIDDLE_FINGER_TIP][1] < hand[1][MIDDLE_FINGER_DIP][1]),
            GESTURE_DELETE: lambda hand: self.hand_detector.get_distance(
                hand[1][MIDDLE_FINGER_TIP],
                hand[1][THUMB_TIP],
            )
            < 30
            and self.hand_detector.get_distance(
                hand[1][RING_FINGER_TIP],
                hand[1][THUMB_TIP],
            )
            < 30
            and self.hand_detector.get_distance(
                hand[1][PINKY_TIP],
                hand[1][THUMB_TIP],
            )
            < 30
            and (hand[1][INDEX_FINGER_TIP][1] < hand[1][INDEX_FINGER_DIP][1]),
        }


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
        self.visible = True

    def drag(self, cursor):
        cursor_x, cursor_y = cursor
        x, y = self.get_pos_x(), self.get_pos_y()
        w, h = self.get_width(), self.get_height()
        if x < cursor_x < x + w and y < cursor_y < y + h:
            self.set_pos_x(cursor_x - w // 2)
            self.set_pos_y(cursor_y - h // 2)

    def delete(self, cursor):
        cursor_x, cursor_y = cursor
        x, y = self.get_pos_x(), self.get_pos_y()
        w, h = self.get_width(), self.get_height()
        if x < cursor_x < x + w and y < cursor_y < y + h:
            self.invisible()

    def invisible(self):
        self.visible = False

    def is_png(self):
        return self.png

    def is_visible(self):
        return self.visible

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
