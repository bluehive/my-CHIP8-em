"""組み込みデモ。外部 ROM を同梱しない。

レイアウトは Part 1 のテストと同じ考え方である。
スプライトを 0x200、命令をその直後に置き、PC は命令の先頭から始める。

描くのは 8×5 の顔である。
  █ █ █ █
  █     █
  █ █ █ █
  █     █
  █ █ █ █
"""

from chip8.machine import PROGRAM_START, Chip8

# 5 バイト。各バイトの上位 4 ビットだけが点灯する。
FACE = bytes((0xF0, 0x90, 0xF0, 0x90, 0xF0))

# 6XNN / ANNN / DXYN。X=1 に列 8、Y=2 に行 4。I はスプライト先頭。
FACE_PROGRAM = bytes((
    0x61, 0x08,  # LD V1, 8
    0x62, 0x04,  # LD V2, 4
    0xA2, 0x00,  # LD I, 0x200（load_face がスプライトをここへ置く）
    0xD1, 0x25,  # DRW V1, V2, 5
))

SPRITE_ADDRESS = PROGRAM_START
CODE_ADDRESS = PROGRAM_START + len(FACE)
# face.ch8 はスプライト 5 バイトの直後に命令がある。PC はそこから。
FACE_ENTRY = CODE_ADDRESS


def face_rom() -> bytes:
    """0x200 から連続したバイト列。CLI がファイルとしても読める。"""
    return FACE + FACE_PROGRAM


def load_face(machine: Chip8) -> None:
    machine.load(face_rom(), SPRITE_ADDRESS)
    machine.pc = CODE_ADDRESS
