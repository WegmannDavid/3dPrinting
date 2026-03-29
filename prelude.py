import cadquery as cq

NOZZLE = 0.4
LAYER = 0.2
EPSILON = 0.001


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
