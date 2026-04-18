import math
from dataclasses import dataclass


@dataclass
class PolygonPort:
    """
    A closed polygon lying in a plane, defined by its ordered vertices.

    The plane's normal is determined by the right-hand rule applied to
    the vertex ordering: curl the right hand in the direction of the
    vertex sequence, and the thumb points along the normal.

    Assumes at least 3 non-collinear vertices.
    """

    vertices: list[tuple[float, float, float]]

    def __post_init__(self):
        if len(self.vertices) < 3:
            raise ValueError(
                f"PolygonPort requires at least 3 vertices, got {len(self.vertices)}"
            )

    def normal(self) -> tuple[float, float, float]:
        """
        Return the unit normal vector of the plane containing the polygon.

        Uses Newell's method, which is robust even when the first three
        vertices are collinear and handles non-convex polygons correctly.
        """
        nx = ny = nz = 0.0
        n = len(self.vertices)
        for i in range(n):
            a = self.vertices[i]
            b = self.vertices[(i + 1) % n]
            nx += (a[1] - b[1]) * (a[2] + b[2])
            ny += (a[2] - b[2]) * (a[0] + b[0])
            nz += (a[0] - b[0]) * (a[1] + b[1])

        mag = math.sqrt(nx * nx + ny * ny + nz * nz)
        if mag < 1e-12:
            raise ValueError(
                "Cannot compute normal: polygon is degenerate (all vertices collinear)"
            )

        return (nx / mag, ny / mag, nz / mag)

    def transform(self, offset: tuple[float, float, float]) -> "PolygonPort":
        """Return a copy of this port translated by the given offset."""
        dx, dy, dz = offset
        new_vertices = [(v[0] + dx, v[1] + dy, v[2] + dz) for v in self.vertices]
        return PolygonPort(vertices=new_vertices)


import math
from dataclasses import dataclass


@dataclass
class CircularPort:
    """
    A circular port defined by its center point, normal vector, and radius.

    The normal is automatically normalized on construction. It points in
    the direction of the port's opening (outward from the solid).
    """

    center: tuple[float, float, float]
    normal: tuple[float, float, float]
    radius: float

    def __post_init__(self):
        mag = math.sqrt(sum(c * c for c in self.normal))
        if mag < 1e-12:
            raise ValueError("Normal vector cannot be zero")
        self.normal = (self.normal[0] / mag, self.normal[1] / mag, self.normal[2] / mag)

        if self.radius <= 0:
            raise ValueError(f"Radius must be positive, got {self.radius}")

    def transform(self, offset: tuple[float, float, float]) -> "CircularPort":
        """Return a copy of this port translated by the given offset."""
        dx, dy, dz = offset
        new_center = (self.center[0] + dx, self.center[1] + dy, self.center[2] + dz)
        return CircularPort(center=new_center, normal=self.normal, radius=self.radius)

    def rotate(
        self,
        axisStartPoint: tuple[float, float, float],
        axisEndPoint: tuple[float, float, float],
        angleDegrees: float,
    ) -> "CircularPort":
        """
        Return a copy of this port rotated around an axis defined by two
        points, by the given angle in degrees. Matches CadQuery's rotate
        signature.

        The rotation follows the right-hand rule: looking from
        axisEndPoint toward axisStartPoint, positive angles rotate
        counterclockwise.
        """
        # Axis direction and a point on the axis
        sx, sy, sz = axisStartPoint
        ex, ey, ez = axisEndPoint
        ax, ay, az = ex - sx, ey - sy, ez - sz

        mag = math.sqrt(ax * ax + ay * ay + az * az)
        if mag < 1e-12:
            raise ValueError("Rotation axis has zero length (start == end)")
        ax, ay, az = ax / mag, ay / mag, az / mag

        angle = math.radians(angleDegrees)
        c = math.cos(angle)
        s = math.sin(angle)
        one_minus_c = 1.0 - c

        def rotate_vec(vx, vy, vz):
            """Rotate a free vector around the axis direction (Rodrigues)."""
            dot = ax * vx + ay * vy + az * vz
            cx = ay * vz - az * vy
            cy = az * vx - ax * vz
            cz = ax * vy - ay * vx
            return (
                vx * c + cx * s + ax * dot * one_minus_c,
                vy * c + cy * s + ay * dot * one_minus_c,
                vz * c + cz * s + az * dot * one_minus_c,
            )

        # Rotate center: translate so axisStartPoint is at origin,
        # rotate, then translate back
        cx, cy, cz = self.center
        tx, ty, tz = cx - sx, cy - sy, cz - sz
        rx, ry, rz = rotate_vec(tx, ty, tz)
        new_center = (rx + sx, ry + sy, rz + sz)

        # Rotate normal as a free direction (pivot point doesn't matter)
        new_normal = rotate_vec(*self.normal)

        return CircularPort(
            center=new_center,
            normal=new_normal,
            radius=self.radius,
        )
