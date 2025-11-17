from queue import Queue
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import pyray as rl
import websockets.sync.client as client
from hall_of_fame import config
from hall_of_fame.entity import Entity
from hall_of_fame.components.tilt_controls import TiltControls
from hall_of_fame.components.camera_followed import CameraFollowed
from hall_of_fame.components.model import Model
from hall_of_fame.components.animation import Animation
from hall_of_fame.message import Message
from hall_of_fame import message


connection: client.ClientConnection
connected = False
net_id: bytes = b""


@dataclass
class PeerState:
    entity: Entity
    controls: TiltControls
    model: Model
    animation: Animation


def instantiate_player() -> tuple[Entity, TiltControls, Model, Animation]:
    player = Entity()

    controls = TiltControls()
    player.components.append(controls)

    model_path = config.MODEL_PATH
    player_model = rl.load_model(model_path)
    model = Model(player_model, controls.position, controls.direction)
    player.components.append(model)

    animations_count = rl.ffi.new("int *", 1)
    player_animations = rl.load_model_animations(model_path, animations_count)
    animation = Animation(model.model, player_animations, animations_count[0])
    player.components.append(animation)

    return player, controls, model, animation


def process_input(player_control: TiltControls, player_animation: Animation):
    if rl.is_key_pressed(rl.KeyboardKey.KEY_D):
        player_control.is_turning_right = True
        connection.send(message.serialize(message.TurningRight(net_id, True)))
    elif rl.is_key_released(rl.KeyboardKey.KEY_D):
        player_control.is_turning_right = False
        connection.send(message.serialize(message.TurningRight(net_id, False)))

    if rl.is_key_pressed(rl.KeyboardKey.KEY_A):
        player_control.is_turning_left = True
        connection.send(message.serialize(message.TurningLeft(net_id, True)))
    elif rl.is_key_released(rl.KeyboardKey.KEY_A):
        player_control.is_turning_left = False
        connection.send(message.serialize(message.TurningLeft(net_id, False)))

    if rl.is_key_pressed(rl.KeyboardKey.KEY_W):
        player_control.is_walking_forward = True
        player_animation.current_animation = config.PLAYER_WALKING_ANIMATION
        connection.send(message.serialize(message.WalkingForward(net_id, True)))
    elif rl.is_key_released(rl.KeyboardKey.KEY_W):
        player_control.is_walking_forward = False
        player_animation.current_animation = config.PLAYER_IDLE_ANIMATION
        connection.send(message.serialize(message.WalkingForward(net_id, False)))

    if rl.is_key_pressed(rl.KeyboardKey.KEY_S):
        player_control.is_walking_backward = True
        connection.send(message.serialize(message.WalkingBackward(net_id, True)))
    elif rl.is_key_released(rl.KeyboardKey.KEY_S):
        player_control.is_walking_backward = False
        connection.send(message.serialize(message.WalkingBackward(net_id, False)))


def enqueue_messages(message_queue: Queue[Message]):
    with client.connect(f"ws://{config.IP}:{config.PORT}") as conn:
        try:
            conn.send(message.serialize(message.Hello()))

            buf = conn.recv()
            assert isinstance(buf, bytes)
            msg = message.deserialize(buf)
            assert isinstance(msg, message.Welcome)

            global net_id, connection, connected
            net_id = msg.to_id
            connection = conn
            connected = True

            conn.send(message.serialize(message.GetState(net_id)))

            while True:
                buf = conn.recv()
                assert isinstance(buf, bytes)
                msg = message.deserialize(buf)
                message_queue.put(msg)
        except Exception as e:
            print(f"Message error: {e}")


def process_messages(
    message_queue: Queue[Message],
    peers: dict[bytes, PeerState],
    player_controls: TiltControls,
):
    try:
        while True:
            msg = message_queue.get_nowait()

            match msg:
                case message.Welcome(to_id):
                    print(f"Player {to_id!r} joined")
                    entity, controls, model, animation = instantiate_player()
                    peers[to_id] = PeerState(entity, controls, model, animation)

                case message.Sync(from_id, to_id):
                    if to_id != net_id:
                        print("Sync received but not asked for")
                        continue

                    if from_id not in peers.keys():
                        print(f"Player {from_id!r} instantiated")
                        entity, controls, model, animation = instantiate_player()
                        peers[from_id] = PeerState(entity, controls, model, animation)

                    msg.to_controls(peers[from_id].controls)

                case message.GetState(from_id):
                    connection.send(
                        message.serialize(
                            message.Sync.from_controls(net_id, from_id, player_controls)
                        )
                    )

                case message.Left(from_id):
                    print(f"Player {from_id!r} left")

                    rl.unload_model_animations(
                        peers[from_id].animation.animations,
                        peers[from_id].animation.animation_count,
                    )
                    rl.unload_model(peers[from_id].model.model)

                    del peers[from_id]
                case message.TurningRight(from_id, state):
                    peers[from_id].controls.is_turning_right = state

                case message.TurningLeft(from_id, state):
                    peers[from_id].controls.is_turning_left = state

                case message.WalkingForward(from_id, state):
                    peers[from_id].controls.is_walking_forward = state
                    if state:
                        peers[
                            from_id
                        ].animation.current_animation = config.PLAYER_WALKING_ANIMATION
                    else:
                        peers[
                            from_id
                        ].animation.current_animation = config.PLAYER_IDLE_ANIMATION

                case message.WalkingBackward(from_id, state):
                    peers[from_id].controls.is_walking_backward = state

                case _:
                    print("Unhandled message")
    except Exception:
        pass


def main():
    rl.trace_log(rl.TraceLogLevel.LOG_INFO, "Opening window...")

    rl.init_window(800, 600, "Hall of Fame")

    player, controls, model, animation = instantiate_player()

    camera = CameraFollowed(controls.position, controls.direction)
    player.components.append(camera)

    # rl.disable_cursor()

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
