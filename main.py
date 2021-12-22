import os
import math
from ctypes import windll
import cv2 as cv
import numpy as np
import mediapipe as mp
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import pyvirtualcam
from constants import *


class App(tk.Tk):
    def __init__(self, cam, cap_src=0):
        """Initializes the app.

        Arguments:
            cam: Virtual cam source.
            cap_src: Capture source.
        """

        tk.Tk.__init__(self)

        # Initialize tkinter style.
        self._style = ttk.Style()

        self._style.theme_use("clam")

        # Change scrollbar colors.
        self._style.configure(
            "Vertical.TScrollbar",
            gripcount=0,
            background="#01ADB5",
            darkcolor="#232932",
            lightcolor="#232932",
            troughcolor="#232932",
            bordercolor="#232932",
            arrowcolor="#EEEEEE",
        )

        # Make window frameless.
        self.overrideredirect(True)

        # Change the windows background color.
        self.configure(bg=COLOR_GRAY)

        # Initialize variables.
        self._init_variables(cam, cap_src)

        # Initialize GUI.
        self._init_gui()

        self._update_capture()

        self.after(10, lambda: self._set_appwindow())

        # Set the window's title.
        self.title("Float")

        # Set the window's icon.
        self.iconbitmap("icon.ico")

        # Set the window's height, width, and position.
        self.geometry(
            f"{self._width}x{self._height}"
            f"+{self.winfo_screenwidth()//2 - self._width//2}"
            f"+{self.winfo_screenheight()//2 - self._height//2}"
        )

        # Set the app icon in the taskbar.
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "mycompany.myproduct.subproduct.version"
        )

    def _update_capture(self):
        if not self.is_dragging():

            def frame_resize(img):
                # Resizes the image by maintaining the aspect ratio by determining what is
                # the percentage of the height relative to the original height in pixels.
                # And then multiplying the original the original width to that percentage.
                base_height = CAPTURE_HEIGHT
                height_percent = base_height / float(img.size[1])
                width = int((float(img.size[0]) * float(height_percent)))
                return img.resize((width, base_height), Image.ANTIALIAS)

            success, frame = self._cap.get_video_capture_frame()

            if success:

                self._hand_detector.reset_hands_list()

                frame = self._hand_detector.find_hands(frame, True)

                if self._float_images:
                    for float_image in self._float_images:
                        frame = self._img_draw(frame, float_image)

                frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

                if self._float_images:
                    if self._gesture_control:
                        self._check_gestures()

                # Send frame to the virtual camera.
                self._virtual_cam.send(frame)

                self._virtual_cam.sleep_until_next_frame()

                if self._cam_preview:
                    frame_arr = Image.fromarray(frame)
                    frame_arr = frame_resize(frame_arr)
                    self._cap_frame = ImageTk.PhotoImage(image=frame_arr)
                    if self._cap_frame.height() != CAPTURE_WIDTH:
                        self._canvas_camera.create_image(
                            ((CAPTURE_WIDTH // 2) - (frame_arr.size[0] // 2)),
                            0,
                            image=self._cap_frame,
                            anchor=tk.NW,
                        )
                    else:
                        self._canvas_camera.create_image(
                            0, 0, image=self._cap_frame, anchor=tk.NW
                        )
                else:
                    self._canvas_camera.delete(tk.ALL)
                    self._canvas_camera.create_text(
                        216,
                        184,
                        text="Preview disabled",
                        fill=COLOR_WHITE,
                        font="Consolas 24",
                        anchor=tk.NW,
                    )

        self.after(10, self._update_capture)

    def _check_gestures(self):
        for hand in self._hand_detector._hands_list:
            if self._GESTURES[GESTURE_DRAG](hand):
                # Make index finger the cursor.
                cursor = hand[1][INDEX_FINGER_TIP]
                for float_image in self._float_images:
                    float_image.drag(cursor)

        if len(self._hand_detector._hands_list) > 1:
            for i in range(2):
                if self._GESTURES[GESTURE_DELETE](self._hand_detector._hands_list[i]):
                    hand = self._hand_detector._hands_list[(i + 1) % 2]
                    if hand[1][INDEX_FINGER_TIP][1] < hand[1][INDEX_FINGER_DIP][1]:
                        cursor = hand[1][INDEX_FINGER_TIP]
                        for float_image in self._float_images:
                            float_image.delete(self._float_images, cursor)

    def _img_draw(self, frame, float_image):
        def overlay_transparent(bg, fg, pos=(0, 0)):
            """Overlays a png image over a jpg image.

            Arguments:
                bg: Background image.
                fg: Foreground image.
                pos: Position of foreground over the background.

            Return:
                Background image overlayed with the foreground image.
            """

            bg_h, bg_w, bg_c = bg.shape
            fg_h, fg_w = fg.shape[:2]
            pos_x, pos_y = pos

            # Create mask from alpha.
            *_, fg_alpha = cv.split(fg)

            # Convert mask from foreground to BGRA which
            # is the same size as the foreground to
            # be able to use bitwise operation.
            fg_mask_bgra = cv.cvtColor(fg_alpha, cv.COLOR_GRAY2BGRA)
            fg_rgba = cv.bitwise_and(fg, fg_mask_bgra)

            # Convert image to BGR which is the same size
            # as the background mask to be able to use
            # bitwise operation.
            fg_rgb = cv.cvtColor(fg_rgba, cv.COLOR_BGRA2BGR)

            # Create a blank image of the same size
            # with the background for the full foreground mask.
            fg_mask_full = np.zeros((bg_h, bg_w, bg_c), np.uint8)

            # Replace full foreground mask at the given position
            # with the RGB foreground.
            fg_mask_full[pos_y : pos_y + fg_h, pos_x : pos_x + fg_w] = fg_rgb

            # Convert mask from foreground to BGR which
            # is the same size as the background to
            # be able to use bitwise operation.
            fg_mask_bgr = cv.cvtColor(fg_alpha, cv.COLOR_GRAY2BGR)

            # Invert mask.
            fg_mask_bgr_inv = cv.bitwise_not(fg_mask_bgr)

            # Create a blank image of the same size with the background.
            bg_mask_full = np.ones((bg_h, bg_w, bg_c), np.uint8) * 255

            # Replace full background mask at the given position
            # with the RGB foreground.
            bg_mask_full[pos_y : pos_y + fg_h, pos_x : pos_x + fg_w] = fg_mask_bgr_inv

            # Mask background.
            bg_masked = cv.bitwise_and(bg, bg_mask_full)

            # Put the masked foreground to the masked background.
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

            frame[:] = overlay_transparent(frame, float_image.get_img(), pos)
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

            frame[pos] = float_image.get_img()

        return frame

    def _set_appwindow(self):
        hwnd = windll.user32.GetParent(self.winfo_id())
        style = windll.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        style = style & ~WS_EX_TOOLWINDOW
        style = style | WS_EX_APPWINDOW
        windll.user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style)
        self.wm_withdraw()
        self.after(10, lambda: self.wm_deiconify())

    def _init_gui(self):
        def win_drag__init(e):
            # Get the cursor position relative to the window.
            self._cursor_rel_x, self._cursor_rel_y = e.x, e.y
            self._dragging = True

        def win_drag(e):
            self.geometry(
                f"+{e.x_root - self._cursor_rel_x}" f"+{e.y_root - self._cursor_rel_y}"
            )

        def win_drag__release():
            self._dragging = False

        def win_minimize():
            self.withdraw()
            self.overrideredirect(False)
            self.iconify()
            self.attributes("-alpha", 0.0)
            self.bind("<Map>", lambda _: win_restore())

        def win_restore():
            self.overrideredirect(True)
            self.after(10, lambda: self._set_appwindow())
            self.attributes("-alpha", 1.0)
            self.unbind("<Map>")

        # Initialize title bar's base.
        self._title_bar = tk.Frame(self, bg=COLOR_BLACK)
        self._title_bar.place(w=self._width, h=25, x=0, y=0)

        self._title_bar.bind("<Button-1>", win_drag__init)
        self._title_bar.bind("<B1-Motion>", win_drag)
        self._title_bar.bind("<ButtonRelease-1>", lambda _: win_drag__release())

        # Initialize title bar's title label.
        self._title = tk.Label(
            self._title_bar,
            text="Float",
            font="Consolas 18 bold",
            fg=COLOR_BLUE,
            bg=COLOR_BLACK,
        )
        self._title.pack(side="left")
        self._title.bind("<Button-1>", win_drag__init)
        self._title.bind("<B1-Motion>", win_drag)
        self._title.bind("<ButtonRelease-1>", lambda _: win_drag__release())

        # Initialize title bar's minimize button.
        self._btn_minimize = tk.Label(
            self._title_bar,
            bg=COLOR_BLACK,
            image=self._img_minimize,
        )
        self._btn_minimize.bind(
            "<Enter>", lambda _: self._btn_minimize.config(bg="#343d4a")
        )
        self._btn_minimize.bind(
            "<Leave>", lambda _: self._btn_minimize.config(bg=COLOR_BLACK)
        )
        self._btn_minimize.bind("<Button-1>", lambda _: win_minimize())
        self._btn_minimize.place(h=25, w=50, x=self._width - 100, y=0)

        # Initialize title bar's close button.
        self._btn_close = tk.Label(
            self._title_bar,
            bg=COLOR_BLACK,
            image=self._img_close,
        )
        self._btn_close.bind("<Enter>", lambda _: self._btn_close.config(bg="#ed4245"))
        self._btn_close.bind(
            "<Leave>", lambda _: self._btn_close.config(bg=COLOR_BLACK)
        )
        self._btn_close.bind("<Button-1>", lambda _: self.destroy())
        self._btn_close.place(h=25, w=50, x=self._width - 50, y=0)

        # Initialize import image button.
        def _btn_import__click():
            # Initialize variables.
            self._win_import = ToplevelWindow(self, "Import image", 372, 303)
            self._win_import.btn_names = ["alphabet", "shapes", "imports"]
            self._win_import.btn_alphabet = None
            self._win_import.btn_shapes = None
            self._win_import.btn_imports = None
            self._win_import.btn_down = None
            self._win_import.btn_up = None

            self._win_import.imgs_alphabet = []
            self._win_import.imgs_shapes = []
            self._win_import.imgs_imports = []

            def show_category_imgs(btn_name):
                # Initiatialize category images.
                self._win_import.frame_imgs = tk.Frame(self._win_import, bg=COLOR_GRAY)
                self._win_import.frame_imgs.place(w=340, h=166, x=16, y=59)

                btn = getattr(self._win_import, f"_imgs_{btn_name}")
                category_imgs = getattr(self, f"_imgs_{btn_name}")

                x, y = 0, 0
                imgs_count = len(category_imgs)

                if imgs_count > 18:
                    scrollbar__init()

                for i in range(imgs_count):
                    thumbnail, path = category_imgs[i]
                    btn.append(
                        tk.Label(
                            self._win_import.frame_imgs,
                            image=thumbnail,
                            bg=COLOR_GRAY,
                            cursor="hand2",
                        )
                    )
                    btn[i].place(w=50, h=50, x=x, y=y)

                    btn[i].bind(
                        "<Button-1>",
                        lambda _, path=path: self._float_images.append(
                            FloatImage(path, (0, 0))
                        ),
                    )

                    x += 58

                    if (i + 1) % 6 == 0:
                        x = 0
                        y += 58

            def scrollbar__init():
                self._win_import.frame_canvas = tk.Canvas(self._win_import.frame_imgs)

                self._win_import.scrollbar = ttk.Scrollbar(
                    self._win_import, orient="vertical"
                )
                self._win_import.scrollbar.place(h=166, x=355, y=59)

            def frame_imgs__init():
                self._win_import.canvas_imgs = tk.Canvas(
                    self._win_import, bg=COLOR_GRAY
                )
                self._win_import.frame_imgs = tk.Frame(self._win_import.canvas_imgs)
                self._win_import.canvas_imgs.create_window(
                    (0, 0), window=self._win_import.frame_imgs
                )

            def btn_category__enter(coord):
                x, y = coord
                self._win_import.cursor.place_forget()
                self._win_import.cursor.place(w=50, h=3, x=x, y=y)
                self._win_import.cursor.configure(bg=COLOR_BLUE)

            def btn_category__select(btn_name):
                self._win_import.label_category.configure(text=btn_name.capitalize())

                # Reset category images and cursor to default.
                for name in self._win_import.btn_names:
                    getattr(self._win_import, f"btn_{name}").configure(
                        image=getattr(self, f"_img_{name}"), cursor="hand2"
                    )

                # Bind events.
                btns_category__bind(btn_name)

                btn = getattr(self._win_import, f"btn_{btn_name}")
                btn.configure(
                    image=getattr(self, f"_img_{btn_name}__selected"),
                    cursor="arrow",
                )
                self._win_import.cursor.configure(bg=COLOR_GRAY)

                setattr(self._win_import, f"_imgs_{btn_name}", [])

                self._win_import.frame_imgs.destroy()

                # Show images from the given category.
                show_category_imgs(btn_name)

            def btns_category__bind(exclude=None):
                gap = 0
                for name in ["alphabet", "shapes", "imports"]:
                    btn = getattr(self._win_import, f"btn_{name}")

                    if exclude != name:
                        if name == "imports":
                            gap = 290
                        btn.bind(
                            "<Enter>",
                            lambda _, gap=gap: btn_category__enter((16 + gap, 287)),
                        )
                        btn.bind(
                            "<Leave>",
                            lambda _: self._win_import.cursor.configure(bg=COLOR_GRAY),
                        )
                        btn.bind(
                            "<Button-1>",
                            lambda _, name=name: btn_category__select(name),
                        )

                    else:
                        btn.unbind("<Enter>")
                        btn.unbind("<Leave>")
                        btn.unbind("<Button-1>")

                    gap += 58

            def btns_category__init():
                gap = 0
                for btn_name in ["alphabet", "shapes", "imports"]:
                    if btn_name == "imports":
                        gap = 290

                    setattr(
                        self._win_import,
                        f"btn_{btn_name}",
                        tk.Label(
                            self._win_import,
                            image=getattr(self, f"_img_{btn_name}"),
                            bg=COLOR_GRAY,
                            cursor="hand2",
                        ),
                    )
                    btn = getattr(self._win_import, f"btn_{btn_name}")
                    btn.place(w=50, h=40, x=16 + gap, y=247)

                    gap += 58

            # Initialize category label.
            self._win_import.label_category = tk.Label(
                self._win_import,
                font="Consolas 16",
                fg=COLOR_WHITE,
                bg=COLOR_GRAY,
                border=0,
            )
            self._win_import.label_category.place(x=16, y=27)

            frame_imgs__init()

            tk.Frame(self._win_import, bg=COLOR_BLACK).place(w=340, h=3, x=16, y=235)

            # Initialize cursor.
            self._win_import.cursor = tk.Frame(self._win_import, bg=COLOR_GRAY)

            # Initialize category buttons.
            btns_category__init()

            # Bind events to the buttons.
            btns_category__bind()

            # Select Alphabet as the first one selected by default.
            btn_category__select("alphabet")

        self._btn_import = tk.Label(
            self, image=self._img_file_image, bg=COLOR_BLUE, cursor="hand2"
        )
        self._btn_import.place(w=56, h=56, x=48, y=49)
        self._btn_import.bind("<Button-1>", lambda _: _btn_import__click())

        # Initialize settings button.
        self._btn_settings = tk.Label(
            self, image=self._img_cog, bg=COLOR_GRAY, cursor="hand2"
        )
        self._btn_settings.place(w=56, h=56, x=self._width - 56 - 48, y=49)

        def ts__click(switch):
            if getattr(self, f"_{switch}"):
                getattr(self, f"_ts_{switch}").config(image=self._img_toggle_switch_off)
            else:
                getattr(self, f"_ts_{switch}").config(image=self._img_toggle_switch_on)
            setattr(self, f"_{switch}", not getattr(self, f"_{switch}"))

        # Initilize camera preview toggle switch.
        tk.Label(
            self,
            text="Camera Preview",
            font="Consolas 16",
            fg=COLOR_WHITE,
            bg=COLOR_GRAY,
            bd=0,
        ).place(x=48, y=543)

        self._ts_cam_preview = tk.Label(
            self, image=self._img_toggle_switch_on, bg=COLOR_GRAY, cursor="hand2"
        )
        self._ts_cam_preview.place(w=42, h=21, x=226, y=546)

        self._ts_cam_preview.bind("<Button-1>", lambda _: ts__click("cam_preview"))

        # Initialize gesture control toggle switch.
        tk.Label(
            self,
            text="Gesture Control",
            font="Consolas 16",
            fg=COLOR_WHITE,
            bg=COLOR_GRAY,
            bd=0,
        ).place(x=306, y=543)

        self._ts_gesture_control = tk.Label(
            self, image=self._img_toggle_switch_on, bg=COLOR_GRAY, cursor="hand2"
        )
        self._ts_gesture_control.place(w=42, h=21, x=493, y=546)

        self._ts_gesture_control.bind(
            "<Button-1>", lambda _: ts__click("gesture_control")
        )

        # Initialize camera preview.
        self._canvas_camera = tk.Canvas(self, bg=COLOR_BLACK, highlightthickness=0)
        self._canvas_camera.place(
            w=CAPTURE_WIDTH,
            h=CAPTURE_HEIGHT,
            x=48,
            y=128,
        )

    def _init_variables(self, cam, cap_src):
        self._virtual_cam = cam
        self._cap_src = cap_src
        self._width = 816
        self._height = 591
        self._cap = Capture(self._cap_src)
        self._hand_detector = HandDetector()
        self._dragging = False
        self._cam_preview = True
        self._gesture_control = True
        self._float_images = []
        self._GESTURES = {
            GESTURE_DRAG: lambda hand: self._hand_detector.get_distance(
                hand[1][INDEX_FINGER_TIP],
                hand[1][MIDDLE_FINGER_TIP],
            )
            < 40
            and (hand[1][INDEX_FINGER_TIP][1] < hand[1][INDEX_FINGER_DIP][1])
            and (hand[1][MIDDLE_FINGER_TIP][1] < hand[1][MIDDLE_FINGER_DIP][1]),
            GESTURE_DELETE: lambda hand: self._hand_detector.get_distance(
                hand[1][MIDDLE_FINGER_TIP],
                hand[1][THUMB_TIP],
            )
            < 30
            and self._hand_detector.get_distance(
                hand[1][RING_FINGER_TIP],
                hand[1][THUMB_TIP],
            )
            < 30
            and self._hand_detector.get_distance(
                hand[1][PINKY_TIP],
                hand[1][THUMB_TIP],
            )
            < 30
            and (hand[1][INDEX_FINGER_TIP][1] < hand[1][INDEX_FINGER_DIP][1]),
        }
        self._img_minimize = tk.PhotoImage(file=PATH_ICONS + "minimize.png")
        self._img_close = tk.PhotoImage(file=PATH_ICONS + "close.png")
        self._img_cog = tk.PhotoImage(file=PATH_ICONS + "cog.png")
        self._img_file_image = tk.PhotoImage(file=PATH_ICONS + "file-image.png")
        self._img_toggle_switch_off = tk.PhotoImage(
            file=PATH_ICONS + "toggle-switch/off.png"
        )
        self._img_toggle_switch_on = tk.PhotoImage(
            file=PATH_ICONS + "toggle-switch/on.png"
        )
        self._img_alphabet = tk.PhotoImage(file=PATH_ICONS + "alphabet/default.png")
        self._img_alphabet__selected = tk.PhotoImage(
            file=PATH_ICONS + "alphabet/selected.png"
        )
        self._img_shapes = tk.PhotoImage(file=PATH_ICONS + "shapes/default.png")
        self._img_shapes__selected = tk.PhotoImage(
            file=PATH_ICONS + "shapes/selected.png"
        )
        self._img_imports = tk.PhotoImage(file=PATH_ICONS + "imports/default.png")
        self._img_imports__selected = tk.PhotoImage(
            file=PATH_ICONS + "imports/selected.png"
        )
        self._img_arrow_down = tk.PhotoImage(file=PATH_ICONS + "arrow/down/default.png")
        self._img_arrow_down__hover = tk.PhotoImage(
            file=PATH_ICONS + "arrow/down/hover.png"
        )
        self._img_arrow_up = tk.PhotoImage(file=PATH_ICONS + "arrow/up/default.png")
        self._img_arrow_up__hover = tk.PhotoImage(
            file=PATH_ICONS + "arrow/up/hover.png"
        )
        self._imgs_shapes = []
        self._imgs_alphabet = []
        self._imgs_imports = []

        for category in ["shapes", "alphabet", "imports"]:
            imgs_path = PATH_IMAGES + f"{category}/"
            files = os.listdir(imgs_path)
            if len(files) != 0:
                for filename in files:
                    filepath = imgs_path + filename
                    img = Image.open(filepath)
                    img.thumbnail((40, 40))
                    pi_img = ImageTk.PhotoImage(img)
                    getattr(self, f"_imgs_{category}").append([pi_img, filepath])

    def is_dragging(self):
        return self._dragging

    def set_dragging(self, flag):
        self._dragging = flag


class ToplevelWindow(tk.Toplevel):
    def __init__(self, parent, title, width, height):
        """Initializes a TopLevelWindow.

        Arguments:
            parent: Parent window of the TopLevelWindow.
            title: Title of the window.
            width: Width of the window.
            height: Height of the window.
        """

        tk.Toplevel.__init__(self, parent)

        # Make window frameless.
        self.overrideredirect(True)

        # Change the windows background color.
        self.configure(bg=COLOR_GRAY)

        # Prevent interaction with the parent window.
        self.grab_set()

        # Initialize variables.
        self._init_variables(parent, width, height)

        # Initialize GUI.
        self._init_gui(title)

        # Set the window's height, width, and position.
        self.geometry(
            f"{self._width}x{self._height}"
            f"+{(parent.winfo_x() + parent._width//2) - (self._width//2)}"
            f"+{(parent.winfo_y() + parent._height//2) - (self._height//2)}"
        )

    def _init_gui(self, title):
        def win_drag__init(e):
            # Get the cursor position relative to the window
            self._cursor_rel_x, self._cursor_rel_y = e.x, e.y
            self._parent.set_dragging(True)

        def win_drag(e):
            self.geometry(
                f"+{e.x_root - self._cursor_rel_x}" f"+{e.y_root - self._cursor_rel_y}"
            )

        def win_drag__release():
            self._parent.set_dragging(False)

        # Initialize title bar's base.
        self._title_bar = tk.Frame(self, bg=COLOR_BLACK)
        self._title_bar.place(w=self._width, h=25, x=0, y=0)

        self._title_bar.bind("<Button-1>", win_drag__init)
        self._title_bar.bind("<B1-Motion>", win_drag)
        self._title_bar.bind("<ButtonRelease-1>", lambda _: win_drag__release())

        # Initialize title bar's title label.
        self._title = tk.Label(
            self._title_bar,
            text=title,
            font="Consolas 12",
            fg=COLOR_BLUE,
            bg=COLOR_BLACK,
        )
        self._title.pack(side="left")
        self._title.bind("<Button-1>", win_drag__init)
        self._title.bind("<B1-Motion>", win_drag)
        self._title.bind("<ButtonRelease-1>", lambda _: win_drag__release())

        # Initialize title bar's close button.
        self._btn_close = tk.Label(
            self._title_bar,
            bg=COLOR_BLACK,
            image=self._img_close,
        )
        self._btn_close.bind("<Enter>", lambda _: self._btn_close.config(bg="#ed4245"))
        self._btn_close.bind(
            "<Leave>", lambda _: self._btn_close.config(bg=COLOR_BLACK)
        )
        self._btn_close.bind("<Button-1>", lambda _: self.destroy())
        self._btn_close.place(h=25, w=50, x=self._width - 50, y=0)

    def _init_variables(self, parent, width, height):
        self._parent = parent
        self._width = width
        self._height = height
        self._img_close = self._parent._img_close


class Capture:
    def __init__(self, cap_src=0):
        self._cap = cv.VideoCapture(cap_src)

    def get_video_capture_frame(self):
        if self._cap.isOpened():
            success, frame = self._cap.read()

            if success:
                return (success, cv.flip(frame, 1))

    def __del__(self):
        if self._cap.isOpened():
            self._cap.release()


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
            Image if draw is True otherwise None.
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
        dist = math.hypot(x2 - x1, y2 - y1)
        return dist

    def reset_hands_list(self):
        self._hands_list = []


class FloatImage:
    def __init__(self, path, pos):
        """Initializes an interactable image using hand gestures.

        Arguments:
            path: File path of the image.
            pos: Position of the image.
        """

        self._path = path
        self._pos = pos

        # Load the image with alpha channel if the image format
        # is png, otherwise load the image by default.
        if "png" in os.path.splitext(self._path)[1]:
            self._img = cv.imread(self._path, cv.IMREAD_UNCHANGED)
            self._png = True if self._img.shape[2] == 4 else False
        else:
            self._img = cv.imread(self._path)
            self._png = False

        self._img = self.img_resize(self._img, width=200)

        self._size = self._img.shape[:2]

    def img_resize(self, img, width=None, height=None, interpolation=cv.INTER_AREA):
        """Initializes an interactable image using hand gestures.

        Arguments:
            img: Image.
            width: Preferred width.
            height: Preferred height.

        Return:
            Resized image, if no width and height given then it returns
            the given image.
        """
        # Gets the size of the image.
        h, w = img.shape[:2]

        if width is None and height is None:
            return img

        dim = None

        # Finds the ratio and use it to get the desired dimension.
        if width is None:
            r = height / float(h)
            dim = (int(w * r), height)
        else:
            r = width / float(w)
            dim = (width, int(h * r))

        return cv.resize(img, dim, interpolation=interpolation)

    def drag(self, cursor):
        cursor_x, cursor_y = cursor
        x, y = self.get_pos_x(), self.get_pos_y()
        w, h = self.get_width(), self.get_height()
        if x < cursor_x < x + w and y < cursor_y < y + h:
            self.set_pos_x(cursor_x - w // 2)
            self.set_pos_y(cursor_y - h // 2)

    def delete(self, float_images, cursor):
        cursor_x, cursor_y = cursor
        x, y = self.get_pos_x(), self.get_pos_y()
        w, h = self.get_width(), self.get_height()
        if x < cursor_x < x + w and y < cursor_y < y + h:
            float_images.pop()

    def is_png(self):
        return self._png

    def get_img(self):
        return self._img

    def get_width(self):
        return self._size[1]

    def get_height(self):
        return self._size[0]

    def get_pos_x(self):
        return self._pos[0]

    def get_pos_y(self):
        return self._pos[1]

    def set_width(self, w):
        self._size = (self._size[0], w)

    def set_height(self, h):
        self._size = (h, self._size[1])

    def set_pos_x(self, x):
        self._pos = (x, self._pos[1])

    def set_pos_y(self, y):
        self._pos = (self._pos[0], y)


def main():
    with pyvirtualcam.Camera(width=1280, height=720, fps=60) as cam:
        app = App(cam)
        app.mainloop()


if __name__ == "__main__":
    main()
