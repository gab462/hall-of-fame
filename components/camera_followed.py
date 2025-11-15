import math
import pyray as rl
from component import Component


class CameraFollowed(Component):
    position: rl.Vector3
    direction: rl.Vector2
    distance: float
    camera: rl.Camera3D

    def __init__(self, position: rl.Vector3, direction: rl.Vector2, distance: float = 15.0):
        self.position = position
        self.direction = direction
        self.distance = distance

        self.camera = rl.Camera3D(rl.Vector3(- self.direction.x * self.distance, 10.0, - self.direction.y * self.distance),
                                  self.position,
                                  rl.Vector3(0.0, 1.0, 0.0),
                                  45.0,
                                  rl.CameraProjection.CAMERA_PERSPECTIVE)

    def update(self, dt: float):
        self.camera.position = rl.Vector3(self.position.x - self.direction.x * self.distance,
                                          self.distance / 2.0,
                                          self.position.z - self.direction.y * self.distance)
        self.camera.target = self.position
