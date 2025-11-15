from dataclasses import dataclass, field
import pyray as rl
from component import Component


@dataclass
class TiltControls(Component):
    position: rl.Vector3 = field(default_factory=lambda: rl.Vector3(0.0, 0.0, 0.0))
    direction: rl.Vector2 = field(default_factory=lambda: rl.Vector2(1.0, 0.0))
    speed: float = 10.0
    rotation_speed: float = 1.0
    is_turning_right: bool = False
    is_turning_left: bool = False
    is_walking_forward: bool = False
    is_walking_backward: bool = False

    def update(self, dt: float):
        if self.is_turning_right:
            rotation = rl.vector2_rotate(self.direction, dt * self.rotation_speed)
            self.direction.x = rotation.x
            self.direction.y = rotation.y

        if self.is_turning_left:
            rotation = rl.vector2_rotate(self.direction, -dt * self.rotation_speed)
            self.direction.x = rotation.x
            self.direction.y = rotation.y

        if self.is_walking_forward:
            movement = rl.vector3_add(
                self.position,
                rl.Vector3(
                    self.speed * dt * self.direction.x,
                    0.0,
                    self.speed * dt * self.direction.y,
                ),
            )
            self.position.x = movement.x
            self.position.z = movement.z

        if self.is_walking_backward:
            movement = rl.vector3_add(
                self.position,
                rl.Vector3(
                    -self.speed * dt * self.direction.x,
                    0.0,
                    -self.speed * dt * self.direction.y,
                ),
            )
            self.position.x = movement.x
            self.position.z = movement.z
