"""CHIP-8 機械。Fetch → Decode → Execute。

正本:
- 命令の意味: docs/CHIP-8-命令セット.md（mattmikolay / COSMAC）
- 状態の切り方と描画: docs/chip8-part1-仕様.md

この最小コアが実行するのは次だけである。
00E0 00EE 1NNN 2NNN 3XNN 4XNN 6XNN 7XNN ANNN DXYN EX9E EXA1
それ以外は UnknownOpcode で止める。0NNN（RCA 1802 呼び出し）は実装しない。

シフトと FX55/FX65 は未実装なので、COSMAC / SCHIP の差はまだ分岐に出ない。
文書の正本は COSMAC 側である。
"""

from __future__ import annotations

DISPLAY_WIDTH = 64
DISPLAY_HEIGHT = 32
MEMORY_SIZE = 4096
PROGRAM_START = 0x200
STACK_DEPTH = 16
REGISTER_COUNT = 16
FONT_SIZE = 80

# 数字 0–F。各 5 バイト。メモリ先頭へ置く。
FONT: tuple[int, ...] = (
    0xF0, 0x90, 0x90, 0x90, 0xF0,  # 0
    0x20, 0x60, 0x20, 0x20, 0x70,  # 1
    0xF0, 0x10, 0xF0, 0x80, 0xF0,  # 2
    0xF0, 0x10, 0xF0, 0x10, 0xF0,  # 3
    0x90, 0x90, 0xF0, 0x10, 0x10,  # 4
    0xF0, 0x80, 0xF0, 0x10, 0xF0,  # 5
    0xF0, 0x80, 0xF0, 0x90, 0xF0,  # 6
    0xF0, 0x10, 0x20, 0x40, 0x40,  # 7
    0xF0, 0x90, 0xF0, 0x90, 0xF0,  # 8
    0xF0, 0x90, 0xF0, 0x10, 0xF0,  # 9
    0xF0, 0x90, 0xF0, 0x90, 0x90,  # A
    0xE0, 0x90, 0xE0, 0x90, 0xE0,  # B
    0xF0, 0x80, 0x80, 0x80, 0xF0,  # C
    0xE0, 0x90, 0x90, 0x90, 0xE0,  # D
    0xF0, 0x80, 0xF0, 0x80, 0xF0,  # E
    0xF0, 0x80, 0xF0, 0x80, 0x80,  # F
)


class UnknownOpcode(Exception):
    """このコアが実行しないオペコード。テストが落ちる方が、黙って進むよりよい。"""

    def __init__(self, opcode: int, pc: int) -> None:
        self.opcode = opcode & 0xFFFF
        self.pc = pc & 0xFFFF
        super().__init__(f"未知のオペコード 0x{self.opcode:04X}（fetch 前 PC=0x{self.pc:04X}）")


class Chip8:
    """メモリ・画面・レジスタ・入力を 1 つの機械に置く。"""

    def __init__(self) -> None:
        self.memory = bytearray(MEMORY_SIZE)
        self.display = [[False] * DISPLAY_WIDTH for _ in range(DISPLAY_HEIGHT)]
        self.v = [0] * REGISTER_COUNT
        self.i = 0
        self.pc = PROGRAM_START
        self.stack = [0] * STACK_DEPTH
        self.sp = 0
        self.delay = 0
        self.sound = 0
        # 16 キー。押下は set_key。描画ループとは分ける。
        self.keys = [False] * 16
        self.memory[:FONT_SIZE] = bytes(FONT)
        self.halted = False
        self.last_opcode = 0

    def reset(self) -> None:
        self.__init__()

    def load(self, program: bytes, address: int = PROGRAM_START) -> None:
        end = address + len(program)
        if address < 0 or end > MEMORY_SIZE:
            raise ValueError(f"プログラムがメモリ外: 0x{address:03X}..0x{end:03X}")
        self.memory[address:end] = program
        self.pc = address

    def set_key(self, key: int, pressed: bool) -> None:
        if not 0 <= key <= 0xF:
            raise ValueError(f"キーは 0–F: {key}")
        self.keys[key] = pressed

    def pixel(self, x: int, y: int) -> bool:
        return self.display[y][x]

    def lit_pixels(self) -> list[tuple[int, int]]:
        return [
            (x, y)
            for y in range(DISPLAY_HEIGHT)
            for x in range(DISPLAY_WIDTH)
            if self.display[y][x]
        ]

    def render_text(self, on: str = "█", off: str = " ") -> str:
        """端末確認用。本番ログにはしない。"""
        rows = []
        for y in range(DISPLAY_HEIGHT):
            rows.append("".join(on if self.display[y][x] else off for x in range(DISPLAY_WIDTH)))
        return "\n".join(rows)

    def tick_timers(self) -> None:
        """60Hz 側。命令サイクルとは別。CLI は命令 N 回につき 1 回呼ぶ。"""
        if self.delay > 0:
            self.delay -= 1
        if self.sound > 0:
            self.sound -= 1

    def cycle(self) -> int:
        """命令を 1 つ実行し、オペコードを返す。タイマは減らさない。"""
        if self.halted:
            raise UnknownOpcode(self.last_opcode, self.pc)
        opcode = self._fetch()
        self.last_opcode = opcode
        try:
            self._execute(opcode)
        except UnknownOpcode:
            self.halted = True
            raise
        return opcode

    def run(self, steps: int) -> int:
        """最大 steps 命令。未知命令で止まったら、実行済み命令数を返す。"""
        done = 0
        for _ in range(steps):
            try:
                self.cycle()
            except UnknownOpcode:
                break
            done += 1
        return done

    def _fetch(self) -> int:
        if self.pc < 0 or self.pc + 1 >= MEMORY_SIZE:
            raise UnknownOpcode(0, self.pc)
        hi = self.memory[self.pc]
        lo = self.memory[self.pc + 1]
        pc = self.pc
        self.pc = (self.pc + 2) & 0xFFFF
        return (hi << 8) | lo

    def _execute(self, opcode: int) -> None:
        op = (opcode & 0xF000) >> 12
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        n = opcode & 0x000F
        nn = opcode & 0x00FF
        nnn = opcode & 0x0FFF

        if opcode == 0x00E0:
            self._cls()
            return
        if opcode == 0x00EE:
            self._ret()
            return
        if op == 0x1:
            self.pc = nnn
            return
        if op == 0x2:
            self._call(nnn)
            return
        if op == 0x3:
            if self.v[x] == nn:
                self.pc = (self.pc + 2) & 0xFFFF
            return
        if op == 0x4:
            if self.v[x] != nn:
                self.pc = (self.pc + 2) & 0xFFFF
            return
        if op == 0x6:
            self.v[x] = nn
            return
        if op == 0x7:
            self.v[x] = (self.v[x] + nn) & 0xFF
            return
        if op == 0xA:
            self.i = nnn
            return
        if op == 0xD:
            self._draw(x, y, n)
            return
        if op == 0xE and nn == 0x9E:
            if self.keys[self.v[x] & 0xF]:
                self.pc = (self.pc + 2) & 0xFFFF
            return
        if op == 0xE and nn == 0xA1:
            if not self.keys[self.v[x] & 0xF]:
                self.pc = (self.pc + 2) & 0xFFFF
            return
        raise UnknownOpcode(opcode, (self.pc - 2) & 0xFFFF)

    def _cls(self) -> None:
        for row in self.display:
            for x in range(DISPLAY_WIDTH):
                row[x] = False

    def _call(self, nnn: int) -> None:
        if self.sp >= STACK_DEPTH:
            raise RuntimeError("コールスタックが溢れた")
        self.stack[self.sp] = self.pc
        self.sp += 1
        self.pc = nnn

    def _ret(self) -> None:
        if self.sp <= 0:
            raise RuntimeError("空のコールスタックから戻ろうとした")
        self.sp -= 1
        self.pc = self.stack[self.sp]

    def _draw(self, x: int, y: int, n: int) -> None:
        """DXYN。開始座標だけ剰余。端はクリップ。画素は XOR。消したら VF=1。"""
        vx = self.v[x] % DISPLAY_WIDTH
        vy = self.v[y] % DISPLAY_HEIGHT
        self.v[0xF] = 0
        for row in range(n):
            py = vy + row
            if py >= DISPLAY_HEIGHT:
                break
            sprite = self.memory[(self.i + row) & 0xFFF]
            for bit in range(8):
                px = vx + bit
                if px >= DISPLAY_WIDTH:
                    break
                if sprite & (0x80 >> bit):
                    if self.display[py][px]:
                        self.v[0xF] = 1
                    self.display[py][px] = not self.display[py][px]
