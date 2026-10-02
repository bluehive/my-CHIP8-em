"""Part 1 の最小テスト。ROM ファイルは読まない。画素が点灯しているかを見る。"""

from __future__ import annotations

import unittest

from chip8.demo import CODE_ADDRESS, FACE, load_face
from chip8.machine import FONT, PROGRAM_START, Chip8, UnknownOpcode


def word(opcode: int) -> bytes:
    return bytes(((opcode >> 8) & 0xFF, opcode & 0xFF))


class FontTests(unittest.TestCase):
    def test_font_sits_at_the_start_of_memory(self) -> None:
        machine = Chip8()
        self.assertEqual(bytes(machine.memory[: len(FONT)]), bytes(FONT))
        self.assertEqual(machine.pc, PROGRAM_START)


class DrawTests(unittest.TestCase):
    def test_face_sprite_lights_the_expected_pixels(self) -> None:
        machine = Chip8()
        load_face(machine)
        self.assertEqual(machine.pc, CODE_ADDRESS)
        self.assertEqual(bytes(machine.memory[PROGRAM_START : PROGRAM_START + 5]), FACE)

        done = machine.run(4)
        self.assertEqual(done, 4)
        self.assertEqual(machine.v[1], 8)
        self.assertEqual(machine.v[2], 4)
        self.assertEqual(machine.v[0xF], 0)

        # 開始 (8, 4)。各行の上位 4 ビット。0xF0 は 4 点、0x90 は両端だけ。
        expected = []
        for row, byte in enumerate(FACE):
            for bit in range(8):
                if byte & (0x80 >> bit):
                    expected.append((8 + bit, 4 + row))
        self.assertEqual(machine.lit_pixels(), expected)
        text = machine.render_text(on="#", off=".")
        self.assertIn("####", text.splitlines()[4])

    def test_collision_sets_vf_and_xor_clears(self) -> None:
        machine = Chip8()
        machine.memory[0x300] = 0x80
        program = word(0x6100) + word(0x6200) + word(0xA300) + word(0xD011) + word(0xD011)
        machine.load(program)
        machine.run(4)
        self.assertTrue(machine.pixel(0, 0))
        self.assertEqual(machine.v[0xF], 0)
        machine.cycle()
        self.assertFalse(machine.pixel(0, 0))
        self.assertEqual(machine.v[0xF], 1)

    def test_draw_clips_at_the_edge(self) -> None:
        machine = Chip8()
        machine.memory[0x300] = 0xFF
        # LD V1,62 / LD V0,0 / LD I,0x300 / DRW V1,V0,1
        # DXYN の N は最下位ニブル。0xD110 は高さ 0 になるので、高さ 1 は 0xD101。
        program = word(0x613E) + word(0x6000) + word(0xA300) + word(0xD101)
        machine.load(program)
        machine.run(4)
        self.assertTrue(machine.pixel(62, 0))
        self.assertTrue(machine.pixel(63, 0))
        self.assertEqual(len(machine.lit_pixels()), 2)


class ControlTests(unittest.TestCase):
    def test_call_and_ret(self) -> None:
        # 0x200: CALL 0x206 / LD V1,1 / JP 0x204
        # 0x206: LD V1,9 / RET
        program = word(0x2206) + word(0x6101) + word(0x1204) + word(0x6109) + word(0x00EE)
        machine = Chip8()
        machine.load(program)
        machine.run(3)
        self.assertEqual(machine.v[1], 9)
        self.assertEqual(machine.sp, 0)
        machine.cycle()
        self.assertEqual(machine.v[1], 1)

    def test_add_wraps_without_carry(self) -> None:
        machine = Chip8()
        machine.load(word(0x61FF) + word(0x7102))
        machine.run(2)
        self.assertEqual(machine.v[1], 1)
        self.assertEqual(machine.v[0xF], 0)

    def test_cls(self) -> None:
        machine = Chip8()
        machine.display[0][0] = True
        machine.load(word(0x00E0))
        machine.cycle()
        self.assertEqual(machine.lit_pixels(), [])

    def test_skip_equal_and_not_equal(self) -> None:
        machine = Chip8()
        # V1=1, SE V1,1 → skip LD V2,9, then LD V2,3
        machine.load(word(0x6101) + word(0x3101) + word(0x6209) + word(0x6203))
        machine.run(3)
        self.assertEqual(machine.v[2], 3)

    def test_unknown_opcode_stops(self) -> None:
        machine = Chip8()
        machine.load(word(0x8000))  # 8XY0 はまだ実装しない
        with self.assertRaises(UnknownOpcode) as caught:
            machine.cycle()
        self.assertEqual(caught.exception.opcode, 0x8000)
        self.assertTrue(machine.halted)


class InputTests(unittest.TestCase):
    def test_skip_if_key(self) -> None:
        machine = Chip8()
        machine.set_key(0xA, True)
        # LD V1, 0xA / SKP V1 / LD V2, 1 / LD V2, 2
        machine.load(word(0x610A) + word(0xE19E) + word(0x6201) + word(0x6202))
        machine.run(3)
        self.assertEqual(machine.v[2], 2)

        fresh = Chip8()
        # キーを押していない。SKP はスキップしないので LD V2,1 が実行され、次の LD V2,2 で上書きされる。
        # 押下時との差は、スキップしたとき V2 が 2 のまま、という一点で見る。
        fresh.load(word(0x610A) + word(0xE19E) + word(0x6201))
        fresh.run(3)
        self.assertEqual(fresh.v[2], 1)

    def test_skip_if_key_not_pressed(self) -> None:
        machine = Chip8()
        machine.load(word(0x610A) + word(0xE1A1) + word(0x6201) + word(0x6202))
        machine.run(3)
        self.assertEqual(machine.v[2], 2)


if __name__ == "__main__":
    unittest.main()
