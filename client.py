from queue import Queue
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import pyray as rl
import websockets.sync.client
import websockets.sync as ws
import config
from entity import Entity
from components.tilt_controls import TiltControls
from components.camera_followed import CameraFollowed
from components.model import Model
from components.animation import Animation
from message import Message, Hello, Welcome, GetState, Sync, Left, TurningRight, TurningLeft, WalkingForward, WalkingBackward, serialize, deserialize


@dataclass
class PeerState:
    entity: Entity
    controls: TiltControls
    model: Model
    animation: Animation


connection: ws.client.ClientConnection
connected = False
net_id: bytes = b''

PLAYER_IDLE_ANIMATION = 2
PLAYER_WALKING_ANIMATION = 10


def instantiate_player() -> tuple[Entity, TiltControls, Model, Animation]:
    player = Entity()

    controls = TiltControls()
    player.components.append(controls)

    player_model = rl.load_model('assets/robot.glb')
    model = Model(player_model, controls.position, controls.direction)
    player.components.append(model)

    animations_count = rl.ffi.new('int *', 1)
    player_animations = rl.load_model_animations('assets/robot.glb', animations_count)
    animation = Animation(model.model, player_animations, animations_count[0])
    player.components.append(animation)

    return player, controls, model, animation


def process_input(player_control: TiltControls, player_animation: Animation):
    if rl.is_key_pressed(rl.KeyboardKey.KEY_D):
        player_control.is_turning_right = True
        connection.send(serialize(TurningRight(net_id, True)))
    elif rl.is_key_released(rl.KeyboardKey.KEY_D):
        player_control.is_turning_right = False
        connection.send(serialize(TurningRight(net_id, False)))

    if rl.is_key_pressed(rl.KeyboardKey.KEY_A):
        player_control.is_turning_left = True
        connection.send(serialize(TurningLeft(net_id, True)))
    elif rl.is_key_released(rl.KeyboardKey.KEY_A):
        player_control.is_turning_left = False
        connection.send(serialize(TurningLeft(net_id, False)))

    if rl.is_key_pressed(rl.KeyboardKey.KEY_W):
        player_control.is_walking_forward = True
        player_animation.current_animation = PLAYER_WALKING_ANIMATION
        connection.send(serialize(WalkingForward(net_id, True)))
    elif rl.is_key_released(rl.KeyboardKey.KEY_W):
        player_control.is_walking_forward = False
        player_animation.current_animation = PLAYER_IDLE_ANIMATION
        connection.send(serialize(WalkingForward(net_id, False)))

    if rl.is_key_pressed(rl.KeyboardKey.KEY_S):
        player_control.is_walking_backward = True
        connection.send(serialize(WalkingBackward(net_id, True)))
    elif rl.is_key_released(rl.KeyboardKey.KEY_S):
        player_control.is_walking_backward = False
        connection.send(serialize(WalkingBackward(net_id, False)))


def enqueue_messages(message_queue: Queue[Message]):
    with ws.client.connect(f"ws://{config.ip}:{config.port}") as conn:
        try:
            conn.send(serialize(Hello()))

            buf = conn.recv()
            assert isinstance(buf, bytes)
            msg = deserialize(buf)
            assert isinstance(msg, Welcome)

            global net_id, connection, connected
            net_id = msg.to_id
            connection = conn
            connected = True

            conn.send(serialize(GetState(net_id)))

            while True:
                buf = conn.recv()
                assert isinstance(buf, bytes)
                msg = deserialize(buf)
                message_queue.put(msg)
        except Exception as e:
            print(f"Message error: {e}")


def process_messages(message_queue: Queue[Message], peers: dict[bytes, PeerState], player_controls: TiltControls):
    try:
        while True:
            msg = message_queue.get_nowait()

            match msg:
                case Welcome(to_id):
                    print(f"Player {to_id!r} joined")
                    entity, controls, model, animation = instantiate_player()
                    peers[to_id] = PeerState(entity, controls, model, animation)

                case Sync(from_id, to_id,
                          position_x, position_y, position_z,
                          direction_x, direction_y,
                          speed, rotation_speed,
                          is_turning_right, is_turning_left,
                          is_walking_forward, is_walking_backward):
                    if to_id != net_id:
                        print("Sync received but not asked for")
                        continue

                    if from_id not in peers.keys():
                        print(f"Player {from_id!r} instantiated")
                        entity, controls, model, animation = instantiate_player()
                        peers[from_id] = PeerState(entity, controls, model, animation)

                    msg.to_controls(peers[from_id].controls)

                case GetState(from_id):
                    connection.send(serialize(Sync.from_controls(net_id, from_id, player_controls)))

                case Left(from_id):
                    print(f"Player {from_id!r} left")

                    rl.unload_model_animations(peers[from_id].animation.animations, peers[from_id].animation.animation_count)
                    rl.unload_model(peers[from_id].model.model)

                    del peers[from_id]
                case TurningRight(from_id, state):
                    peers[from_id].controls.is_turning_right = msg.state

                case TurningLeft(from_id, state):
                    peers[from_id].controls.is_turning_left = state

                case WalkingForward(from_id, state):
                    peers[from_id].controls.is_walking_forward = state
                    print(f'Position x: {peers[from_id].controls.position.x}')
                    print(f'Position z: {peers[from_id].controls.position.z}')
                    if state:
                        peers[from_id].animation.current_animation = PLAYER_WALKING_ANIMATION
                    else:
                        peers[from_id].animation.current_animation = PLAYER_IDLE_ANIMATION

                case WalkingBackward(from_id, state):
                    peers[from_id].controls.is_walking_backward = state

                case _:
                    print("Unhandled message")
    except:
        pass


def main():
    rl.trace_log(rl.TraceLogLevel.LOG_INFO, f'Opening window...');

    rl.init_window(800, 600, 'Hall of Fame')

    player, controls, model, animation = instantiate_player()

    camera = CameraFollowed(controls.position, controls.direction)
    player.components.append(camera)

    rl.disable_cursor()

    rl.set_target_fps(60)

    message_queue: Queue[Message] = Queue()
    peers: dict[bytes, PeerState] = {}

    executor = ThreadPoolExecutor()
    executor.submit(enqueue_messages, message_queue)

    while not connected and not rl.window_should_close():
        rl.begin_drawing()
        rl.clear_background(rl.RAYWHITE)
        rl.draw_text("Connecting to server...", 10, 10, 40, rl.GRAY)
        rl.end_drawing()

    while not rl.window_should_close():
        dt = rl.get_frame_time()

        process_input(controls, animation)

        process_messages(message_queue, peers, controls)

        rl.begin_drawing()
        rl.clear_background(rl.RAYWHITE)
        rl.begin_mode_3d(camera.camera)
        rl.draw_grid(512, 1.0)

        player.update(dt)

        for _, peer in peers.items():
            peer.entity.update(dt)

        rl.end_mode_3d()
        rl.end_drawing()

    # Server already handles sending Left()
    # connection.send(serialize(Left(net_id)))

    connection.close()
    executor.shutdown(wait=False, cancel_futures=True)

    rl.unload_model_animations(animation.animations, animation.animation_count)
    rl.unload_model(model.model)

    rl.close_window()


if __name__ == '__main__':
    main()
