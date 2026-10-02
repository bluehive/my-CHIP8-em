# my-CHIP8-em

Python で CHIP-8 エミュレータを学ぶためのリポジトリです。

- 言語: Python 3.12（[uv](https://docs.astral.sh/uv/) / [mise](https://mise.jdx.dev/)）
- ライセンス: [BSD-2-Clause](LICENSE)
- 画面と入力の確認はヘッドレスです。ウィンドウは置きません。

## 仕様とコードの対応

命令の意味の正本は [docs/CHIP-8-命令セット.md](docs/CHIP-8-命令セット.md) です。
状態の切り方と描画の手順は [docs/chip8-part1-仕様.md](docs/chip8-part1-仕様.md) です。
コードは `src/chip8/machine.py` の `Chip8` に、メモリ・画面・レジスタ・キーをまとめて置きます。

いま実行するのは Part 1 の命令に、キー状態を見る 2 命令を足したものです。

| オペコード | 意味 |
|---|---|
| `00E0` `00EE` | 画面消去、サブルーチンから戻る |
| `1NNN` `2NNN` | ジャンプ、呼び出し |
| `3XNN` `4XNN` | 即値と比較してスキップ |
| `6XNN` `7XNN` | 即値の格納、加算（キャリーは立てない） |
| `ANNN` `DXYN` | I の設定、スプライト描画 |
| `EX9E` `EXA1` | キーが押されている / いないならスキップ |

表に無い命令は `UnknownOpcode` で止まります。`0NNN`（RCA 1802 の呼び出し）は実装しません。
シフトと `FX55` / `FX65` は未実装です。文書の正本は COSMAC 側（`VY` をシフトして `VX` へ、`I` は増やす）ですが、分岐はまだありません。

マイクロスタックマシンは CHIP-8 とは別の教材です。命令もメモリも共用しません。

- 短い正本: [docs/stack-machine-仕様.md](docs/stack-machine-仕様.md)
- 厚い説明: [Wiki](https://github.com/bluehive/my-CHIP8-em/wiki)（鏡: [docs/wiki/](docs/wiki/)）

## 起動

依存パッケージはありません。Python は uv が用意します。

```bash
mise trust
mise exec -- uv sync --python 3.12
uv run chip8
```

引数なしは組み込みの顔デモです。4 命令のあと、64×32 のテキスト画面に 8×5 の顔が出ます。

```text
        ████
        █  █
        ████
        █  █
        ████
```

同梱 ROM は自作の `roms/face.ch8` だけです。先頭 5 バイトはスプライトなので、PC は `0x205` から始まります。`uv run chip8 roms/face.ch8` はこのファイルだと入口を自動で合わせます。

他の `.ch8` は、プログラムが `0x200` から始まるものとして読みます。

```bash
uv run chip8 path/to/game.ch8 --steps 200
uv run chip8 path/to/game.ch8 --address 0x200 --entry 0x200 --steps 50
```

このコアが知らない命令に当たると、そこまでの画面を出して終了コード 2 で止まります。有名 ROM の多くは未実装命令を使うので、顔は出ません。それは未実装の検出です。

キーは対話では取りません。`Chip8.set_key(0xA, True)` で状態を置いてから `EX9E` / `EXA1` を実行します。

タイマは命令サイクルでは減らしません。CLI は既定で 11 命令ごとに `tick_timers()` を 1 回呼びます（目安: 約 700 命令/秒に対して 60Hz）。`FX07` などはまだ無いので、減算の結果はログに出ません。

## テスト

```bash
uv run python -m unittest discover -s tests -v
```

第一号は「顔スプライトの指定画素が点灯している」です。衝突で `VF=1` になること、画面端でクリップすること、未知命令で止まることも見ます。
