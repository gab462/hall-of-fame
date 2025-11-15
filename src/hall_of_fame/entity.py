from dataclasses import dataclass, field
from hall_of_fame.component import Component


@dataclass
class Entity:
    components: list[Component] = field(default_factory=lambda: [])

    def update(self, dt: float):
        for c in self.components:
            c.update(dt)
