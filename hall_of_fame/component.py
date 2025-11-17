from abc import ABC, abstractmethod


class Component(ABC):
    @abstractmethod
    def update(self, dt: float):
        pass
