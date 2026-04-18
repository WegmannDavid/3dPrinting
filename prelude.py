import cadquery as cq

NOZZLE = 0.4
LAYER = 0.2
EPSILON = 0.0001


def negative_point(point):
    """
    Invert a point by negating its coordinates.

    Args:
        point: a tuple (x, y, z) representing the point

    Returns:
        a tuple representing the inverted point
    """
    return tuple(-p for p in point)


def translate_all(objects, translation):
    """
    Translate a tuple (or list) of CadQuery objects by the given translation.

    Args:
        objects: tuple or list of Workplane or Shape objects
        translation: a tuple (x, y, z) or cq.Vector

    Returns:
        tuple of translated objects
    """
    return tuple(obj.translate(translation) for obj in objects)


def translate_point(point, translation):
    """
    Translate a point by the given translation.

    Args:
        point: a tuple (x, y, z) representing the point
        translation: a tuple (x, y, z) or cq.Vector

    Returns:
        a tuple representing the translated point
    """
    return tuple(p + t for p, t in zip(point, translation))


def translate_points(points, translation):
    """
    Translate a list of points by the given translation.

    Args:
        points: a list of tuples (x, y, z) representing the points
        translation: a tuple (x, y, z) or cq.Vector

    Returns:
        a list of tuples representing the translated points
    """
    return [translate_point(point, translation) for point in points]
