"""ヘッドレス起動。画素はテキストで出す。キーは対話では取らない。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chip8.demo import CODE_ADDRESS, FACE_ENTRY, face_rom, load_face
from chip8.machine import PROGRAM_START, Chip8, UnknownOpcode

# 目安は 1 秒に約 700 命令、タイマは 60Hz。ここは命令 N 回につきタイマ 1 回。
INSTRUCTIONS_PER_TIMER = 700 // 60


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chip8",
        description="CHIP-8 学習用コアをヘッドレスで数サイクル回し、画面をテキストで出す。",
    )
    parser.add_argument(
        "rom",
        nargs="?",
        help="ROM ファイル（.ch8 など）。省略すると組み込みの顔デモを使う",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=4,
        help="実行する命令数（既定: デモなら 4、ROM なら指定値）",
    )
    parser.add_argument(
        "--address",
        type=lambda s: int(s, 0),
        default=PROGRAM_START,
        help="ROM を置くアドレス（既定: 0x200）",
    )
    parser.add_argument(
        "--entry",
        type=lambda s: int(s, 0),
        default=None,
        help="実行開始 PC。省略時は配置アドレス。roms/face.ch8 は 0x205",
    )
    parser.add_argument(
        "--timer-every",
        type=int,
        default=INSTRUCTIONS_PER_TIMER,
        help="何命令ごとにディレイ/サウンドを 1 減らすか（既定: 11）",
    )
    args = parser.parse_args(argv)

    machine = Chip8()
    if args.rom is None:
        load_face(machine)
        steps = args.steps
        label = "組み込み顔デモ"
    else:
        data = Path(args.rom).read_bytes()
        machine.load(data, args.address)
        if args.entry is not None:
            machine.pc = args.entry
        elif data == face_rom() and args.address == PROGRAM_START:
            # 同梱デモはスプライトが先頭にある。命令として実行しない。
            machine.pc = FACE_ENTRY
        steps = args.steps
        if "--steps" not in sys.argv[1:] and data != face_rom():
            steps = 200
        label = args.rom

    entry = machine.pc
    executed = 0
    stopped: UnknownOpcode | None = None
    for n in range(steps):
        try:
            machine.cycle()
        except UnknownOpcode as exc:
            stopped = exc
            break
        executed += 1
        if args.timer_every > 0 and executed % args.timer_every == 0:
            machine.tick_timers()

    print(f"# {label}")
    print(f"# 実行命令数: {executed}  PC=0x{machine.pc:04X}  I=0x{machine.i:03X}")
    print(f"# V1={machine.v[1]:02X} V2={machine.v[2]:02X} VF={machine.v[0xF]}")
    if entry == CODE_ADDRESS:
        print(f"# 命令開始: 0x{CODE_ADDRESS:03X}")
    if stopped is not None:
        print(f"# 停止: {stopped}")
    print(machine.render_text())
    return 0 if stopped is None else 2


if __name__ == "__main__":
    raise SystemExit(main())
