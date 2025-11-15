import math
from dataclasses import dataclass
import pyray as rl
from component import Component


@dataclass
class Model(Component):
    model: rl.Model
    position: rl.Vector3
    direction: rl.Vector2

    def update(self, dt: float):
        rl.draw_model_ex(self.model,
                         self.position,
                         rl.Vector3(0.0, 1.0, 0.0),
                         math.atan2(self.direction.x, self.direction.y) * (180.0  / math.pi),
                         rl.Vector3(0.5, 0.5, 0.5),
                         rl.WHITE)
