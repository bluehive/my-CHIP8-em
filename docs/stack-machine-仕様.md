# スタックマシン仕様（CHIP-8 前段）

CHIP-8 のレジスタ機械に入る前に、オペランドをスタックから取る最小 VM を固定する。
実装コードは置かない。CHIP-8 本体の定数は [chip8-part1-仕様](chip8-part1-仕様.md) に譲る。

学習用リポジトリを GitHub で探したうえで、共通項だけをこの機械の仕様にした。
クローンしない。参考は次の 4 系統である。

- TinyVM: 短い命令表の MVP スタック VM。[1][2]
- MicroMini: Racket 製の 8 bit スタック機械。オペランドはほぼスタック頂点から取る。[3][4]
- cslarsen/stack-machine: レジスタ無し、データスタックと命令スタックの二本。[5]
- pbohun/stack-vm-tutorials: ゼロから積み上げる授業形式。[6]

## なぜ CHIP-8 の前に置くか

CHIP-8 はデータ用のオペランドスタックを持たない。算術は V0–VF、呼び出しだけが 16 段スタックである。
先に「値はスタック、演算は pop して結果を push」を閉じないと、CHIP-8 の `7XNN` や `8XY4` が「スタック演算」に見えてしまう。

この前段で学ぶのは次だけである。

- 機械状態を 1 か所に置く
- 1 命令フェッチして実行するループ
- 空スタックでの pop はエラー
- 後置（RPN）で式を書く

メモリマップ・画面・タイマ・キーは持たない。

## 機械の定数

| 項目 | 値 | 根拠 |
|---|---|---|
| データ幅 | 8 bit（0–255、加算はラップ） | CHIP-8 の Vx と同じ幅。MicroMini も 8 bit データバス。[4] |
| データスタック深さ | 16 | CHIP-8 の呼び出しスタック段数に揃える |
| プログラム | 命令の列（トークンでよい。バイトコードは後でよい） | TinyVM はテキスト命令列から入る。[2] |
| PC | 命令列上の添字。初期値 0 | MicroMini は実行開始アドレスを明示する。[4] |
| レジスタ | 無し | スタック機械の定義。cslarsen もレジスタ無し。[5] |
| 画面 / キー / タイマ | 無し | Part 1 の外。前段でも外。 |

TinyVM は整数 `isize` とラベル飛びで Turing 完全を取る。[2]
こちらは CHIP-8 前段なので、飛びと手続きは第二段まで遅らせる。

## 状態（1 か所）

次だけを 1 つの機械に載せる。

- `program` — 命令列
- `pc` — 次に読む位置
- `stack` — データスタック（頂点が末尾）
- `halt?` — 停止

MicroMini はこれに RAM・リターンポインタ・キャリー・サイクルカウンタを足す。[4]
前段では足さない。キャリーと RAM は CHIP-8 側の仕事である。

cslarsen は理論上のプッシュダウンオートマトンに合わせ、データと命令ポインタでスタックを二本にする。[5]
CHIP-8 の二本目は「戻りアドレス専用」である。前段ではデータスタック一本。CALL/RET を足すときに二本目を開ける。

## 実行サイクル

毎サイクル:

1. `halt?` なら停止
2. `pc` がプログラム末尾なら停止（MicroMini は RAM 末端で halt-bit。[4]）
3. 命令を 1 つ読む
4. `pc` を 1 進める（オペランド付き命令は、読んだ分だけさらに進める）
5. 実行する

TinyVM は命令ポインタと行を対応させるために Noop を置く。[2]
テストをベタ書きする段階では、命令列をベクタにして添字を PC にすれば足りる。

アンダーフロー（空なのに pop）とオーバーフロー（16 を超える push）はエラーで止める。
未知命令も止める。画面に出して続行しない。

## 命令（第一段）

演算はスタック頂点から取る。これが MicroMini の原則である。[4]
TinyVM の表から、CHIP-8 前段に必要な最小交差を取る。[2]

| 命令 | スタック（前 → 後） | 意味 |
|---|---|---|
| `PUSH n` | … → … n | 即値を積む。n は 0–255 |
| `POP` | … a → … | 捨てる |
| `DUP` | … a → … a a | 頂点を複製 |
| `SWAP` | … a b → … b a | 頂点 2 つを入れ替え |
| `ADD` | … a b → … (a+b) | 8 bit ラップ。キャリーは立てない（CHIP-8 の `7XNN` と同じ） |
| `SUB` | … a b → … (a−b) | 頂点が減数。アンダーフローはラップ |
| `HALT` | 不変 | `halt?` を真にする |

第一段に入れないもの（TinyVM / MicroMini にあるが CHIP-8 前段では早い）:

- ラベル Jump / JNE 一式 — TinyVM の Turing 完全側。[2]
- Call / Ret / GetArg — 手続き。CHIP-8 の `2NNN`/`00EE` で学ぶ。[2]
- AND/OR/XOR/NOT — MicroMini にある。[4] CHIP-8 の `8XYn` で学ぶ。
- メモリ LOAD/STOR、端末 I/O — 別機械の話。[4][5]

`DUP` と `SWAP` は TinyVM 表には無いが、後置の手計算とテストに要る。CHIP-8 命令セットにも無い。前段の学習語彙としてだけ置く。

## 第二段（任意・CHIP-8 の直前）

第一段がテストで止まってから足す。

| 命令 | 意味 | CHIP-8 への橋 |
|---|---|---|
| `JMP dest` | PC を dest にする | `1NNN` |
| `CALL dest` | 戻り PC をリターンスタックに積み、PC を dest | `2NNN` |
| `RET` | リターンスタックから PC を戻す | `00EE` |

リターンスタックも深さ 16。溢れはエラー。
データスタックと混ぜない（cslarsen の二本を、CHIP-8 と同じ役割分担にする）。[5]

## テスト（ROM ファイルは読まない）

CHIP-8 Part 1 と同じく、命令列をベタ書きして数サイクル回す。

合格例:

- `PUSH 3` `PUSH 4` `ADD` `HALT` → スタック頂点 7、それ以外空
- `PUSH 1` `PUSH 2` `SWAP` `SUB` `HALT` → 頂点 1（2−1）
- 空に `POP` → エラー
- 深さ 16 を超える `PUSH` → エラー

表示はスタックの中身だけでよい。█ 画面は CHIP-8 側。

## CHIP-8 に持っていくもの / 置いていくもの

持っていく:

- 状態は 1 構造体
- フェッチしてから実行
- 失敗は言語のエラー（黙って wrap して続行しない。算術の 8 bit wrap は別）
- 呼び出しスタックはデータスタックと別物

置いていく:

- オペランドスタックそのもの（CHIP-8 の演算は Vx）
- `DUP` / `SWAP`
- トークン列のプログラム（CHIP-8 は 2 バイトオペコード）

pbohun の授業は「1 レッスンごとに機械を厚くする」。[6]
ここでも同じ順にする: スタック四則 → CALL/RET →（別仕様）CHIP-8 のメモリと DRW。

## Sources

[1] https://github.com/mkhan45/tinyvm — mkhan45/tinyvm: MVP stack-based bytecode VM
[2] https://raw.githubusercontent.com/mkhan45/tinyvm/main/README.md — TinyVM README (instruction table)
[3] https://github.com/jarcane/MicroMini — jarcane/MicroMini: Racket 8-bit stack machine
[4] https://raw.githubusercontent.com/jarcane/MicroMini/master/docs/MicroMini.txt — MicroMini instruction documentation
[5] https://github.com/cslarsen/stack-machine — cslarsen/stack-machine: Forth-like stack VM
[6] https://github.com/pbohun/stack-vm-tutorials — pbohun/stack-vm-tutorials: build a stack VM from scratch
