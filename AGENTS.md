# lean4mini — agent notes

MiniLang 自舉編譯器：stage0 用 Lean 4 寫（`Main.lean`），自舉編譯器用 MiniLang 自己寫
（`compiler.lm`，單趟、不建 AST），目標為堆疊機 IR，由內建 VM 執行。

Workspace root 就是本目錄，所有命令都在這裡跑。

## Toolchain

- `lean-toolchain`：`leanprover/lean4:v4.20.0`（經 elan），不要覆寫。
- `lakefile.lean`：`lean_exe minic`，`root := Main`。`lake build` 產出 `.lake/build/bin/minic`。
- `.gitignore` 只忽略 `.lake/`；`build/*.ir` 是自舉產物快照，版本提交時一起收。

## Build — 順序重要

`bootstrap.sh` 已編碼正確順序，不要打亂：

```bash
lake build
M=.lake/build/bin/minic
mkdir -p build
$M compile compiler.lm               > build/stage0.ir   # Lean 編譯器 → IR₀
$M run build/stage0.ir < compiler.lm > build/stage1.ir   # IR₀ 在 VM 上編譯自己 → IR₁
$M run build/stage1.ir < compiler.lm > build/stage2.ir   # IR₁ 在 VM 上編譯自己 → IR₂
cmp build/stage0.ir build/stage1.ir && cmp build/stage1.ir build/stage2.ir
$M bootstrap compiler.lm examples/*.lm
```

- stage1/2 依賴前一階段的 IR，一律按順序重建；絕不手改 `build/*.ir`。
- 自舉成功 ⇔ IR₀ = IR₁ = IR₂（逐位元相同，不動點）。

## CLI（`minic`）

- `compile <f.lm>`：輸出機器可讀 IR（整數串流：`memsize, op₀, arg₀, …`）。
- `list <f.lm|f.ir>`：人類可讀組合語言。
- `run <f.lm|f.ir> [-i 輸入檔]`：編譯（若是 `.lm`）並在 VM 上執行。無 `-i` 時程式 stdin
  即本程序 stdin（會先讀完整個 stdin，無輸入請加 `</dev/null` 或用 `-i`）。
- `bootstrap <compiler.lm> [tests…]`：三階段自舉＋範例比對（stage2 編各範例，須與 stage0 一致）。

## Verify

- 單一入口：`./test.sh [fuzz顆數，預設 20]`，含 [1] `lake build` [2] `./bootstrap.sh`
  （不動點＋範例 IR 比對）[3] 範例 golden 輸出＋負向測試 [4] `difftest.py`；最後印
  `PASS=n FAIL=0` 且 exit 0 才算綠。
- 只改文件時至少跑 `[1]`；改 `Main.lean`/`compiler.lm`/`examples/` 時跑完整 `./test.sh`。

## 改語言 — 2 處同步（缺一即破不動點）

`Main.lean`（Lean 版，有 AST）與 `compiler.lm`（自舉版，單趟直接 emit）是同一個編譯器的
兩份實現，語義必須逐位元一致。加語法/IR/運算子時：

1. 先改 `Main.lean`（`lex`/`parse*`/`compileExpr`/`compileStmt`/`Instr`），`lake build` 通過。
2. 再鏡像改 `compiler.lm`（`lex`/`parse*`/`emit` 呼叫點），`./bootstrap.sh` 仍為不動點才算完。
3. 同步更新 `README.md` 語言小節與本檔 gotcha。

## 加範例

`examples/<name>.lm` 即自動納入（`bootstrap.sh` 用 `examples/*.lm` glob，無需另註冊）；但新增語法特性時
   也要在 `difftest.py` 的 `gen_prog` 加入對應生成分支。

## Gotchas（已踩過的坑）

- 單趟編譯限制：**全域（`array`/`let`）須先宣告再使用**，函式呼叫可前向（`resolveCalls` 回填）。
  範例中 `array buf` 一定要寫在用它的 `fn` 之前。
- 全域陣列 vs 全域變數：`x[i]` 的底址對陣列是常數位址，對全域變數（字串/指標）要先 `mload`
  解參照。`Main.lean` 用 `CState.garr`、`compiler.lm` 用 `gisarr` 區分；動索引邏輯時兩邊一起動。
- 字串以 0 結尾靠的是 VM 記憶體零初始化（`Array.replicate memsize 0`），`strLit` 只寫字元、
  不另寫終止符；改 VM 記憶體初始化會破字串語義。
- `compiler.lm` 固定容量：`src 80000 / tok 30000 / code 60000 / 全域 2000 / 區域 200 / 函式 500 /`
  `呼叫點 3000`，超限報 `fail(70-76)`；stage0（Lean）無此限制，大程式的差異測試以自舉版為準。
- 字串尚無跳脫（`"a\"b"`、`"\n"` 會斷；字元常數 `'\\'`/`'\n'`/`'\t'` 有支援），改詞法時兩邊同步。
- `minic run` 讀 stdin 的特性也會影響自舉：`run stage0.ir < compiler.lm` 是把原始碼經由
  VM 的 `getc` 餵給自舉編譯器，不要把 `-i` 誤用在這裡。

## Version commits

- 每次版本提交附 `_doc/vX.Y.md`（變更內容、IR 統計、驗證結果、已知限制）。
- `build/stage{0,1,2}.ir` 與綠燈的 `./bootstrap.sh` 一起快照，絕不單獨手動更新。
