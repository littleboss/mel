"""Work with a collection of moles."""


import argparse
import json
import math
import os
import uuid

import cv2
import numpy

import mel.lib.math


class ArgparseRotomapDirectoryType():

    """Use in the 'type=' parameter to add_argument()."""

    def __init__(self, path):
        self.path = path
        if not os.path.isdir(self.path):
            raise argparse.ArgumentTypeError(
                '"{}" is not a directory, so not a rotomap.'.format(self.path))
        files = os.listdir(self.path)
        self.image_paths = [
            os.path.join(self.path, f)
            for f in files
            if f.lower().endswith('.jpg')
        ]
        if not self.image_paths:
            raise argparse.ArgumentTypeError(
                '"{}" has no images, so not a rotomap.'.format(self.path))

    def yield_mole_lists(self):
        """Yield (image_path, mole_list) for all mole image files."""
        for imagepath in self.image_paths:
            yield imagepath, load_image_moles(imagepath)


def load_image_moles(image_path):
    moles_path = image_path + '.json'
    moles = []
    if os.path.exists(moles_path):
        with open(moles_path) as moles_file:
            moles = json.load(moles_file)

    for m in moles:
        if 'is_uuid_canonical' not in m:
            m['is_uuid_canonical'] = True

    for m in moles:
        m['x'] = int(m['x'])
        m['y'] = int(m['y'])

    return moles


def normalise_moles(moles):
    for m in moles:
        m['x'] = int(m['x'])
        m['y'] = int(m['y'])


def save_image_moles(moles, image_path):
    moles_path = image_path + '.json'
    with open(moles_path, 'w') as moles_file:
        json.dump(
            moles,
            moles_file,
            indent=4,
            separators=(',', ': '),
            sort_keys=True)

        # There's no newline after dump(), add one here for happier viewing
        print(file=moles_file)


def add_mole(moles, x, y, mole_uuid=None):
    is_uuid_canonical = True
    if mole_uuid is None:
        mole_uuid = uuid.uuid4().hex
        is_uuid_canonical = False

    moles.append({
        'x': x,
        'y': y,
        'uuid': mole_uuid,
        'is_uuid_canonical': is_uuid_canonical,
    })


def sorted_by_distances(mole_list, x, y):

    def sqdist(mole):
        dist_x = x - mole['x']
        dist_y = y - mole['y']
        return (dist_x * dist_x) + (dist_y * dist_y)

    return sorted(mole_list, key=sqdist)


def nearest_mole_index(moles, x, y):
    return nearest_mole_index_distance(moles, x, y)[0]


def nearest_mole_index_distance(moles, x, y):
    nearest_index = None
    nearest_distance = None
    for i, mole in enumerate(moles):
        dx = x - mole['x']
        dy = y - mole['y']
        distance = math.sqrt(dx * dx + dy * dy)
        if nearest_distance is None or distance < nearest_distance:
            nearest_index = i
            nearest_distance = distance

    return nearest_index, nearest_distance


def uuid_mole_index(moles, mole_uuid):
    """Return the index of the first mole with the specified uuid."""
    for i, mole in enumerate(moles):
        if mole['uuid'] == mole_uuid:
            return i
    return None


def set_nearest_mole_uuid(moles, x, y, mole_uuid, is_canonical=True):
    nearest_index = nearest_mole_index(moles, x, y)
    if nearest_index is not None:
        moles[nearest_index]['uuid'] = mole_uuid
        moles[nearest_index]['is_uuid_canonical'] = is_canonical


def get_nearest_mole_uuid(moles, x, y):
    nearest_index = nearest_mole_index(moles, x, y)
    if nearest_index is not None:
        return moles[nearest_index]['uuid']

    return None


def move_nearest_mole(moles, x, y):
    nearest_index = nearest_mole_index(moles, x, y)

    if nearest_index is not None:
        moles[nearest_index]['x'] = x
        moles[nearest_index]['y'] = y


def remove_nearest_mole(moles, x, y):
    nearest_index = nearest_mole_index(moles, x, y)

    if nearest_index is not None:
        del moles[nearest_index]


def mole_to_point(mole):
    pos = numpy.array((mole['x'], mole['y']))
    mel.lib.math.raise_if_not_int_vector2(pos)
    return pos


def to_uuid_points(moles):
    uuid_points = {}
    for m in moles:
        uuid_points[m['uuid']] = mole_to_point(m)
    return uuid_points


def set_molepos_to_nparray(mole, nparray):
    mole['x'] = int(nparray[0])
    mole['y'] = int(nparray[1])


def is_value_in_range(value, lower, upper):
    return value >= lower and value <= upper


def is_point_in_rect(point, rect):
    return (
        is_value_in_range(point[0], rect[0], rect[2]) and
        is_value_in_range(point[1], rect[1], rect[3])
    )


def triangle_to_points(triangle):
    return (
        (triangle[0], triangle[1]),
        (triangle[2], triangle[3]),
        (triangle[4], triangle[5])
    )


def is_triangle_in_rect(triangle, rect):
    return all(is_point_in_rect(p, rect) for p in triangle_to_points(triangle))


def get_mole_triangles(mole_list, image_rect):
    subdiv = cv2.Subdiv2D(image_rect)
    for mole in mole_list:
        subdiv.insert((mole['x'], mole['y']))

    # filter the list of triangles to those that only have points that fit in
    # the rectangle
    triangle_list = []
    for triangle in subdiv.getTriangleList():
        if is_triangle_in_rect(triangle, image_rect):
            triangle_list.append(triangle)

    return triangle_list


def get_best_triangle_for_mapping(triangle_list, point):
    best_triangle = None
    best_result = None
    for triangle in triangle_list:
        # Ignore "Instance of 'tuple' has no 'astype' member (no-member)" from
        # pylint.
        # pylint: disable=no-member
        #
        # pointPolygonTest() will fail if we don't pass it values exactly like
        # this.
        contour = numpy.array(triangle_to_points(triangle)).astype('float32')
        # pylint: enable=no-member
        result = cv2.pointPolygonTest(contour, tuple(point), True)
        if best_result is None or result > best_result:
            best_result = result
            best_triangle = triangle

    return best_triangle


def get_moles_from_points(mole_list, point_list):
    output_moles = []
    for point in point_list:
        for mole in mole_list:
            molepoint = mole_to_point(mole)
            if numpy.allclose(point, molepoint):
                output_moles.append(mole)

    if len(point_list) != len(output_moles):
        raise ValueError('Not all points match moles: {}, {}'.format(
            point_list, mole_list))

    return output_moles


def get_best_moles_for_mapping(molepoint, mole_list, image_rect):

    if len(mole_list) < 3:
        if len(mole_list) == 0:
            return None
        else:
            return mole_list

    triangle_list = get_mole_triangles(mole_list, image_rect)
    best_triangle = get_best_triangle_for_mapping(triangle_list, molepoint)

    # Discard triangles that are not very equilateral, they seem to give bad
    # mappings.
    if best_triangle is not None:
        points = triangle_to_points(best_triangle)
        distances = [
            mel.lib.math.distance_2d(points[i - 1], points[i])
            for i in range(3)
        ]
        max_ = max(*distances)
        if max_ == 0:
            best_triangle = None
        else:
            norm_distances = [x / max_ for x in distances]
            for x in norm_distances:
                if x <= 0.5:
                    best_triangle = None

    moles_for_mapping = None
    if best_triangle is not None:
        moles_for_mapping = get_moles_from_points(
            mole_list, triangle_to_points(best_triangle))
    else:
        # Two nearest moles to map with is better than none
        return sorted_by_distances(
            mole_list, molepoint[0], molepoint[1])[:2]

    return moles_for_mapping


def mapped_pos(molepos, from_moles, to_moles):
    mel.lib.math.raise_if_not_int_vector2(molepos)

    if not from_moles:
        return molepos

    to_dict = {m['uuid']: m for m in to_moles}
    from_pos_list = [mole_to_point(m) for m in from_moles]
    to_pos_list = [mole_to_point(to_dict[m['uuid']]) for m in from_moles]

    num_pairs = len(from_pos_list)

    if num_pairs > 3:
        # Ideally we'd handle 4 points by using cv2.getPerspectiveTransform()
        # as in this article:
        #
        #     http://www.pyimagesearch.com/2014/08/25/4-point-opencv-getperspective-transform-example/
        #
        # We could take advantage of more than 4 points by using
        # findHomography(), which can use various methods to deal with the
        # ambiguity introduced by multiple points.
        #
        # In practice, trying to use more than 3 points proved difficult as
        # naively including neighboring triangles resulted in adding co-linear
        # points.
        #
        raise ValueError('Too many moles')
    elif num_pairs == 3:
        # The best we can do here is to determine the translation, rotation and
        # scaling to apply in order to map from one triangle to the other. If
        # we want this to be a perspective transformation then we'd need an
        # additional point.
        #
        transform = numpy.matrix(cv2.getAffineTransform(
            numpy.float32(from_pos_list),
            numpy.float32(to_pos_list))).transpose()
        pos = numpy.array([molepos[0], molepos[1], 1.0]) * transform
        pos = numpy.array(pos)
        molepos = pos[0]
    elif num_pairs > 0:
        # Here we'll just assume that the transformation is a translation and
        # compute it from the first pair of points.
        translation = to_pos_list[0] - from_pos_list[0]
        molepos += translation
    # elif num_pairs > 2:
        # In later work, to take advantage of 2 pairs of points, we'll handle
        # it like so:
        #
        # Here we'll assume that the line through the supplied points is
        # roughly perpendicular to the axis of rotation. This means that we'd
        # expect the distance of the point from the line to be constant across
        # the transformation.

    return molepos
