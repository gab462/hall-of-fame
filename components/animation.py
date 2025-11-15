from collections.abc import Sequence
from dataclasses import dataclass
import pyray as rl
from component import Component


@dataclass
class Animation(Component):
    model: rl.Model
    animations: Sequence[rl.ModelAnimation]
    animation_count: int
    current_animation: int = 0
    frame: int = 0

    def update(self, dt: float):
        self.frame = (self.frame + 1) % self.animations[
            self.current_animation
        ].frameCount
        rl.update_model_animation(
            self.model, self.animations[self.current_animation], self.frame
        )
