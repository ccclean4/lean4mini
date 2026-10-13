# lean4mini

A mini lean4. (DIY)

MiniLang 自舉編譯器（Lean 4），原始碼副檔名為 `.lm`（lean4 mini 縮寫）。

```
lake build                 # 建置 stage0（Lean 寫的編譯器 + VM）
./bootstrap.sh             # 三階段自舉並驗證不動點
.lake/build/bin/minic run examples/fib.lm </dev/null
.lake/build/bin/minic run examples/io.lm -i /tmp/io.in   # -i 分離程式輸入與 shell stdin
.lake/build/bin/minic list examples/fib.lm      # 看 IR 組合語言
```

| 檔案 | 說明 |
|---|---|
| `Main.lean` | stage0：Lean 寫的詞法/語法分析、IR 產生器、堆疊 VM、自舉驅動 |
| `compiler.lm` | 用 MiniLang 寫的 MiniLang 編譯器（單趟、不建 AST） |
| `examples/` | 範例程式（遞迴、陣列、字串、I/O、短路求值） |
| `build/` | 自舉產物 stage0/1/2.ir（應逐位元相同） |

注意：`minic run` 無 `-i` 時會先讀完整個 stdin，沒有輸入時請加 `</dev/null` 或用 `-i`。
全域需先宣告再使用（單趟編譯限制），函式可前向呼叫。
`compiler.lm` 有固定容量（src 80000/tok 30000/code 60000/全域 2000/函式 500/呼叫點 3000），超限以 `fail(70-76)` 回報。
