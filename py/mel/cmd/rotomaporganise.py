"""Organise images into rotomaps."""

import os
import shutil

import cv2

import mel.lib.common
import mel.lib.ui


def setup_parser(parser):
    parser.add_argument(
        'IMAGES',
        nargs='+',
        help="A list of paths to images sets or images.")
    parser.add_argument(
        '--display-width',
        type=int,
        default=None,
        help="Width of the preview display window.")
    parser.add_argument(
        '--display-height',
        type=int,
        default=None,
        help="Width of the preview display window.")


def process_args(args):

    display = OrganiserDisplay(
        "rotomap-organise",
        _expand_dirs_to_images(args.IMAGES),
        args.display_width,
        args.display_height)

    mel.lib.ui.bring_python_to_front()

    print("Press left arrow or right arrow to change image.")
    print("Press backspace to delete image.")
    print("Press 'g' to group images before current to a folder.")
    print("Press any other key to exit.")

    is_finished = False
    while not is_finished:
        key = cv2.waitKey(50)
        if key != -1:
            if key == mel.lib.ui.WAITKEY_RIGHT_ARROW:
                display.next_image()
            elif key == mel.lib.ui.WAITKEY_LEFT_ARROW:
                display.prev_image()
            elif key == mel.lib.ui.WAITKEY_BACKSPACE:
                display.delete_image()
            elif key == ord('g'):
                destination = input('group destination: ')
                display.group_images(destination)
            else:
                is_finished = True


class OrganiserDisplay():
    """Display images in a window, supply controls for organising."""

    def __init__(self, name, image_list, width=None, height=None):
        if not image_list:
            raise ValueError(
                "image_list must be a list with at least one image.")

        self._original_title = name
        self._display = mel.lib.ui.ImageDisplay(name, width, height)
        self._image_list = image_list
        self._index = 0
        self._show()

    def next_image(self):
        if self._image_list:
            self._index = (self._index + 1) % len(self._image_list)
        self._show()

    def prev_image(self):
        if self._image_list:
            num_images = len(self._image_list)
            self._index = (self._index + num_images -
                           1) % len(self._image_list)
        self._show()

    def delete_image(self):
        if self._image_list:
            os.remove(self._image_list[self._index])
            del self._image_list[self._index]
            self._index -= 1
            self.next_image()

    def group_images(self, destination):
        if self._image_list:
            if not os.path.exists(destination):
                os.makedirs(destination)
            for image_path in self._image_list[:self._index + 1]:
                shutil.move(image_path, destination)
            del self._image_list[:self._index + 1]
            self._index = -1
            self.next_image()

    def _show(self):
        if self._image_list:
            path = self._image_list[self._index]
            self._display.show_image(
                cv2.imread(
                    path))
            self._display.set_title(path)
        else:
            self._display.show_image(
                mel.lib.common.new_image(
                    self._display.height,
                    self._display.width))
            self._display.set_title(self._original_title)


def _expand_dirs_to_images(path_list):
    image_paths = []
    for path in path_list:
        if os.path.isdir(path):
            image_paths.extend(list(_yield_only_jpegs_from_dir(path)))
        else:
            image_paths.append(path)
    return image_paths


def _yield_only_jpegs_from_dir(path):
    for filename in os.listdir(path):
        if _is_jpeg_name(filename):
            yield os.path.join(path, filename)


def _is_jpeg_name(filename):
    lower_ext = os.path.splitext(filename)[1].lower()
    return lower_ext in ('.jpg', '.jpeg')