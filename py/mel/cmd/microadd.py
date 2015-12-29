"""Capture images from an attached microscope and add to existing moles."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import cv2
import os
import numpy

import mel.lib.common
import mel.lib.datetime
import mel.lib.image
import mel.lib.moleimaging
import mel.lib.ui


def setup_parser(parser):
    parser.add_argument(
        'PATH',
        type=str,
        help="Path to the mole to add new microscope images to.")
    parser.add_argument(
        '--display-width',
        type=int,
        default=800,
        help="Width of the preview display window.")
    parser.add_argument(
        '--display-height',
        type=int,
        default=600,
        help="Width of the preview display window.")


def get_context_image_name(path):
    # Paths should alpha-sort to recent last, pick the first jpg
    children = reversed(sorted(os.listdir(path)))
    for name in children:
        # TODO: support more than just '.jpg'
        if name.lower().endswith('.jpg'):
            return os.path.join(path, name)

    return None


def get_dirs_to_path(path_in):
    """Return a list of the intermediate paths between cwd and path.

    Raise if path is not below the current working directory (cwd).

    :returns: list of strings, includes cwd and destination path
    :path: string path

    """
    cwd = os.getcwd()
    path_abs = os.path.abspath(path_in)
    if cwd != os.path.commonprefix([cwd, path_abs]):
        raise Exception('{} is not under cwd ({})'.format(path_abs, cwd))
    path_rel = os.path.relpath(path_abs, cwd)
    path_list = []
    while path_rel:
        path_rel, tail = os.path.split(path_rel)
        path_list.append(os.path.join(cwd, path_rel, tail))
    path_list.append(cwd)
    return path_list


def load_context_image(path):

    image_name = get_context_image_name(path)
    if image_name:
        return cv2.imread(image_name)

    raise Exception("No image in {}".format(path))


def load_context_images(path):
    image_list = []
    path_list = get_dirs_to_path(path)
    for path in path_list:
        name = get_context_image_name(path)
        if name:
            image_list.append(cv2.imread(name))
    return image_list


def get_first_micro_image_path(path):

    micro_path = os.path.join(path, '__micro__')

    # Paths should alpha-sort to recent last, pick the first jpg
    children = sorted(os.listdir(micro_path))
    for name in children:
        # TODO: support more than just '.jpg'
        if name.lower().endswith('.jpg'):
            return os.path.join(micro_path, name)


def load_first_micro_image(path):
    micro_path = get_first_micro_image_path(path)
    if micro_path is None:
        return None
    return micro_path, cv2.imread(micro_path)


def process_args(args):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise Exception("Could not open video capture device.")

    width = args.display_width
    height = args.display_height

    first_micro_image_data = load_first_micro_image(args.PATH)

    if first_micro_image_data is not None:
        first_micro_path, first_micro_image = first_micro_image_data
        display = mel.lib.ui.MultiImageDisplay(first_micro_path, width, height)
    else:
        display = mel.lib.ui.MultiImageDisplay(args.PATH, width, height)

    context_images = load_context_images(args.PATH)
    for image in context_images:
        display.add_image(image)

    if context_images:
        display.new_row()

    if first_micro_image_data:
        display.add_image(first_micro_image)

    # wait for confirmation
    mole_acquirer = mel.lib.moleimaging.MoleAcquirer()
    is_finished = False
    ret, frame = cap.read()
    if not ret:
        raise Exception("Could not read frame.")
    capindex = display.add_image(frame, 'capture')
    while not is_finished:
        frame = capture(cap, display, capindex, mole_acquirer)
        print(
            "Press 'a' to abort, 'r' to retry, "
            "any other key to save and quit.")
        while True:
            key = cv2.waitKey(50)
            if key != -1:
                if key == ord('a'):
                    raise Exception('User aborted.')
                elif key == ord('r'):
                    print("Retry capture")
                    break
                else:
                    is_finished = True
                    break

    # write the mole image
    filename = mel.lib.datetime.make_now_datetime_string() + ".jpg"
    dirname = os.path.join(args.PATH, '__micro__')
    if not os.path.isdir(dirname):
        os.makedirs(dirname)
    file_path = os.path.join(dirname, filename)
    cv2.imwrite(file_path, frame)


def capture(cap, display, capindex, mole_acquirer):

    # loop until the user presses a key
    print("Press 'c' to force capture a frame, any other key to abort.")
    while True:
        ret, frame = cap.read()
        if not ret:
            raise Exception("Could not read frame.")

        key = cv2.waitKey(50)
        if key != -1:
            if key == ord('c'):
                print('Force capturing frame.')
                break
            else:
                raise Exception('User aborted.')

        is_rot_sensitive = True
        ringed, stats = mel.lib.moleimaging.find_mole(frame)
        asys_image = numpy.copy(frame)
        is_aligned = mel.lib.moleimaging.annotate_image(
            asys_image,
            is_rot_sensitive)

        mole_acquirer.update(stats)

        display.update_image(asys_image, capindex)
        if mole_acquirer.is_locked and is_aligned:
            # show the image with mole encircled
            print("locked and aligned")
            break

    return frame
