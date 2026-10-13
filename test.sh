#!/bin/sh
# test.sh — lean4mini 一鍵測試
#   [1] lake build
#   [2] ./bootstrap.sh（自舉不動點 IR₀=IR₁=IR₂ ＋ 範例 IR 比對）
#   [3] 範例 golden 輸出（含 -i 輸入檔、一則編譯錯誤負向測試）
#   [4] python3 difftest.py（隨機程式 stage0 vs stage2 差異測試）
# 用法：./test.sh [fuzz 顆數，預設 20]
set -u
cd "$(dirname "$0")"
M=.lake/build/bin/minic
N=${1:-20}
PASS=0
FAIL=0

ok()  { PASS=$((PASS + 1)); echo "ok   $1"; }
bad() { FAIL=$((FAIL + 1)); echo "FAIL $1"; }

echo "== [1/4] lake build =="
if lake build > /tmp/lean4mini_build.log 2>&1; then
  ok "lake build"
else
  bad "lake build — 見 /tmp/lean4mini_build.log"
fi

echo "== [2/4] bootstrap =="
if ./bootstrap.sh > /tmp/lean4mini_bootstrap.log 2>&1; then
  ok "bootstrap（不動點＋範例 IR 比對）"
else
  bad "bootstrap — 見 /tmp/lean4mini_bootstrap.log"
  tail -5 /tmp/lean4mini_bootstrap.log
fi

echo "== [3/4] 範例 golden 輸出 =="
chk() { # chk <名稱> <程式> <輸入檔（空字串=無輸入）> <預期輸出> [<額外參數…>]
  name=$1; prog=$2; inp=$3; want=$4; shift 4
  if [ -z "$inp" ]; then
    got=$($M run "$prog" "$@" </dev/null 2>&1)
  else
    got=$($M run "$prog" -i "$inp" "$@" </dev/null 2>&1)
  fi
  if [ "$got" = "$want" ]; then
    ok "$name"
  else
    bad "$name"
    echo "--- want ---"; printf '%s\n' "$want"
    echo "--- got  ---"; printf '%s\n' "$got"
  fi
}

chk "fib"    examples/fib.lm    "" "$(printf '55\n610')"
chk "while"  examples/while.lm  "" "$(printf '45\n1')"
chk "array"  examples/array.lm  "" "$(printf '0\n1\n4\n9\n16\n25\n36\n49\n64\n81\n25')"
chk "string" examples/string.lm "" "$(printf '104\n105\n33\nABC\n3')"

printf 'Hi\n' > /tmp/lean4mini_io.in
chk "io(-i)" examples/io.lm /tmp/lean4mini_io.in \
  "$(printf 'Hi\n888\n0\n888\n999\n2\n1\n0\n11\n3\n1')"

# 負向測試：未定義變數必須編譯失敗
printf 'print nosuchvar;\n' > /tmp/lean4mini_bad.lm
if $M compile /tmp/lean4mini_bad.lm > /dev/null 2>&1; then
  bad "neg-undef（應編譯失敗卻成功）"
else
  ok "neg-undef"
fi

echo "== [4/4] difftest × $N =="
if python3 difftest.py "$N"; then
  ok "difftest"
else
  bad "difftest"
fi

echo "------------------------"
echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
