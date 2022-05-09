import os
import cv2 as cv


class FloatImage:
    def __init__(self, path, cap_w=None):
        """Initializes an interactable image using hand gestures.

        Arguments:
            path: File path of the image.
            pos: Position of the image.
        """

        self._path = path

        # Load the image with alpha channel if the image format
        # is png, otherwise load the image by default.
        if "png" in os.path.splitext(self._path)[1]:
            self._img = cv.imread(self._path, cv.IMREAD_UNCHANGED)
            self._png = True if self._img.shape[2] == 4 else False
        else:
            self._img = cv.imread(self._path)
            self._png = False

        self._img = self.img_resize(width=int(cap_w * 0.12))
        self._size = self._img.shape[:2]
        self._pos = (cap_w - self._size[1], 0)
        self._dragging = None
        self._resizing = None

    def img_resize(self, width=None, height=None, interpolation=cv.INTER_AREA):
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
        h, w = self._img.shape[:2]

        if width is None and height is None:
            return self._img

        dim = None

        # Finds the ratio and use it to get the desired dimension.
        if width is None:
            r = height / float(h)
            dim = (int(w * r), height)
        else:
            r = width / float(w)
            dim = (width, int(h * r))

        return cv.resize(self._img, dim, interpolation=interpolation)

    def drag_start(self, handedness, cursor):
        cursor_x, cursor_y = cursor
        x, y = self.get_pos_x(), self.get_pos_y()
        w, h = self.get_width(), self.get_height()

        # Check if the image is within the image
        if x < cursor_x < x + w and y < cursor_y < y + h:
            self._dragging = handedness
            self._drag_init = (cursor_x - x, cursor_y - y)

            return True

        return False

    def drag(self, frame, cursor):
        frame_h, frame_w = frame.shape[:2]
        cursor_x, cursor_y = cursor
        drag_init_x, drag_init_y = self._drag_init
        w, h = self.get_width(), self.get_height()

        drag_x = cursor_x - drag_init_x
        drag_y = cursor_y - drag_init_y

        # If the image would be outside the frame's dimension,
        # then bring the image back in the frame's dimension.
        if drag_x < 0:
            drag_x = 0
        elif drag_x > frame_w - w:
            drag_x = frame_w - w

        if drag_y < 0:
            drag_y = 0
        elif drag_y > frame_h - h:
            drag_y = frame_h - h

        self.set_pos_x(drag_x)
        self.set_pos_y(drag_y)

    def delete(self, cursor):
        cursor_x, cursor_y = cursor
        x, y = self.get_pos_x(), self.get_pos_y()
        w, h = self.get_width(), self.get_height()
        if x < cursor_x < x + w and y < cursor_y < y + h:
            return True

        return False

    def resize_start(self, cursor, other_cursor):
        x, y = self.get_pos_x(), self.get_pos_y()
        w, h = self.get_width(), self.get_height()
        p = 0.5

        def top_left(cursor):
            return x < cursor[0] < x + (w * p) and y < cursor[1] < y + (h * p)

        def top_right(cursor):
            return x + (w * (1 - p)) < cursor[0] < x + w and y < cursor[1] < y + (h * p)

        def bottom_left(cursor):
            return x < cursor[0] < x + (w * p) and y + (h * (1 - p)) < cursor[1] < y + h

        def bottom_right(cursor):
            return (
                x + (w * (1 - p)) < cursor[0] < x + w
                and y + (h * (1 - p)) < cursor[1] < y + h
            )

        if bottom_left(cursor) and top_right(other_cursor):
            self._resizing = "Right"
        elif bottom_right(cursor) and top_left(other_cursor):
            self._resizing = "Left"

    def resize(self, frame, cursor, other_cursor, resize_w):
        frame_h, frame_w = frame.shape[:2]

        x, y = self.get_pos_x(), self.get_pos_y()

        padding = int(resize_w * 0.20)

        img = self.img_resize(
            width=resize_w - padding,
        )

        h, w = img.shape[:2]

        if w < self.get_width() and w < frame_w * 0.05:
            return

        if abs((cursor[0] + other_cursor[0]) / 2) - (w / 2) <= 0:
            return

        if abs((cursor[1] + other_cursor[1]) / 2) - (h / 2) <= 0:
            return

        if x + w > frame_w:
            return

        if y + h > frame_h:
            return

        if self._png:
            self._img = cv.imread(self._path, cv.IMREAD_UNCHANGED)
        else:
            self._img = cv.imread(self._path)

        self._img = self.img_resize(width=resize_w - padding)
        self._size = self._img.shape[:2]

        self.set_pos_x(
            int(abs((cursor[0] + other_cursor[0]) / 2) - (self.get_width() / 2))
        )
        self.set_pos_y(
            int(abs((cursor[1] + other_cursor[1]) / 2) - (self.get_height() / 2))
        )

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
