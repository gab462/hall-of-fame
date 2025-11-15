import io
import struct
import typing
from dataclasses import dataclass, fields, asdict
from components.tilt_controls import TiltControls


@dataclass
class Hello:
    pass


@dataclass
class Welcome:
    to_id: bytes


@dataclass
class GetState:
    from_id: bytes


@dataclass
class Sync:
    from_id: bytes
    to_id: bytes
    position_x: float
    position_y: float
    position_z: float
    direction_x: float
    direction_y: float
    speed: float
    rotation_speed: float
    is_turning_right: bool
    is_turning_left: bool
    is_walking_forward: bool
    is_walking_backward: bool

    @classmethod
    def from_controls(cls, from_id: bytes, to_id: bytes, controls: TiltControls) -> typing.Self:
        return cls(from_id, to_id,
                   controls.position.x, controls.position.y, controls.position.z,
                   controls.direction.x, controls.direction.y,
                   controls.speed, controls.rotation_speed,
                   controls.is_turning_right, controls.is_turning_left,
                   controls.is_walking_forward, controls.is_walking_backward)

    def to_controls(self, controls: TiltControls):
        controls.position.x = self.position_x
        controls.position.y = self.position_y
        controls.position.z = self.position_z

        controls.direction.x = self.direction_x
        controls.direction.y = self.direction_y

        controls.speed = self.speed
        controls.rotation_speed = self.rotation_speed

        controls.is_turning_right = self.is_turning_right
        controls.is_turning_left = self.is_turning_left
        controls.is_walking_forward = self.is_walking_forward
        controls.is_walking_backward = self.is_walking_backward


@dataclass
class Left:
    from_id: bytes


@dataclass
class TurningRight:
    from_id: bytes
    state: bool


@dataclass
class TurningLeft:
    from_id: bytes
    state: bool


@dataclass
class WalkingForward:
    from_id: bytes
    state: bool


@dataclass
class WalkingBackward:
    from_id: bytes
    state: bool


Message = Hello | Welcome | GetState | Sync | Left | TurningRight | TurningLeft | WalkingForward | WalkingBackward


def get_fmt(cls: type) -> str:
    type_mappings: dict[type, str] = {
        int: 'i',
        float: 'f',
        bool: '?',
        bytes: '16s', # only uuid allowed
    }

    fmt = io.StringIO()

    fmt.write('!')
    fmt.write(type_mappings[int]) # message_type

    for t in typing.get_type_hints(cls).values():
        fmt.write(type_mappings[t])

    return fmt.getvalue()


def serialize(obj: Message) -> bytes:
    message_type = typing.get_args(Message).index(type(obj))

    return struct.pack(get_fmt(type(obj)), message_type, *asdict(obj).values())


def deserialize(buf: bytes) -> Message:
    message_type, = struct.unpack('!i', buf[:4])

    t = typing.get_args(Message)[message_type]

    message_type, *data = struct.unpack(get_fmt(t), buf)

    return t(*data)
