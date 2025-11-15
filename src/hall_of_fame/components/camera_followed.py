from dataclasses import dataclass, field
import pyray as rl
from hall_of_fame.component import Component


@dataclass
class CameraFollowed(Component):
    position: rl.Vector3
    direction: rl.Vector2
    distance: float = 15.0
    camera: rl.Camera3D = field(default_factory=lambda: rl.Camera3D())

    def __post_init__(self):
        self.camera.up = rl.Vector3(0.0, 1.0, 0.0)
        self.camera.fovy = 45.0
        self.camera.projection = rl.CameraProjection.CAMERA_PERSPECTIVE
        self.camera.position = rl.Vector3(
            self.position.x - self.direction.x * self.distance,
            self.distance / 2.0,
            self.position.z - self.direction.y * self.distance,
        )
        self.camera.target = self.position

    def update(self, dt: float):
        self.camera.position = rl.Vector3(
            self.position.x - self.direction.x * self.distance,
            self.distance / 2.0,
            self.position.z - self.direction.y * self.distance,
        )
        self.camera.target = self.position
