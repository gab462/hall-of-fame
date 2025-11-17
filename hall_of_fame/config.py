import pathlib
import sys


def this_file() -> str:
    if getattr(sys, 'frozen', False):
        return sys.executable
    else:
        return __file__


MODEL_PATH = str(pathlib.Path(this_file()).parent / "assets" / "robot.glb")

PLAYER_IDLE_ANIMATION = 2
PLAYER_WALKING_ANIMATION = 10

IP = "127.0.0.1"
PORT = 8172
