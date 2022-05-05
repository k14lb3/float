import os
import cv2 as cv

class FloatImage:
    def __init__(self, path, pos):
        """Initializes an interactable image using hand gestures.

        Arguments:
            path: File path of the image.
            pos: Position of the image.
        """

        self._path = path
        self._pos = pos
        self._dragging = None

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

    def drag(self, handedness, cursor):
        cursor_x, cursor_y = cursor
        x, y = self.get_pos_x(), self.get_pos_y()
        w, h = self.get_width(), self.get_height()
        
        self._dragging = None
        
        if x < cursor_x < x + w and y < cursor_y < y + h:
            self._dragging = handedness
            self.set_pos_x(cursor_x - w // 2)
            self.set_pos_y(cursor_y - h // 2)
            
            return True
        
        return False

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