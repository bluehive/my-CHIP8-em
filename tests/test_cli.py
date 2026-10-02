"""起動手順の確認。画素の合格は test_machine 側。ここは入口だけ見る。"""

from __future__ import annotations

import unittest
from pathlib import Path

from chip8.cli import main
from chip8.demo import face_rom

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_builtin_demo_prints_a_face(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout

        buf = StringIO()
        with redirect_stdout(buf):
            code = main([])
        text = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("組み込み顔デモ", text)
        self.assertIn("████", text)
        self.assertIn("█  █", text)

    def test_rom_file_matches_builtin(self) -> None:
        self.assertEqual((ROOT / "roms" / "face.ch8").read_bytes(), face_rom())


if __name__ == "__main__":
    unittest.main()
