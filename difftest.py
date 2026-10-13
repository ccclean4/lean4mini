#!/usr/bin/env python3
"""差異測試：隨機 MiniLang 程式，stage0 compile vs stage2 compile 的 IR 與執行輸出必須一致。"""
import random, subprocess, sys, os

ROOT = os.path.dirname(os.path.abspath(__file__))
MINIC = os.path.join(ROOT, ".lake/build/bin/minic")

def run(args, inp=b""):
    p = subprocess.run(args, input=inp, capture_output=True, cwd=ROOT)
    return p.returncode, p.stdout, p.stderr

def build_stages():
    subprocess.run(["lake", "build"], cwd=ROOT, check=True, capture_output=True)
    with open(os.path.join(ROOT, "compiler.lm"), "rb") as f:
        comp_src = f.read()
    rc, s0, e = run([MINIC, "compile", "compiler.lm"])
    assert rc == 0, e.decode()
    open("/tmp/diff_s0.ir", "wb").write(s0)
    rc, s1, e = run([MINIC, "run", "/tmp/diff_s0.ir"], comp_src)
    assert rc == 0, e.decode()
    open("/tmp/diff_s1.ir", "wb").write(s1)
    rc, s2, e = run([MINIC, "run", "/tmp/diff_s1.ir"], comp_src)
    assert rc == 0, e.decode()
    open("/tmp/diff_s2.ir", "wb").write(s2)
    return s0, s2

def gen_expr(r, depth, vars_):
    if depth <= 0 or r.random() < 0.3:
        if vars_ and r.random() < 0.6:
            return r.choice(vars_)
        return str(r.randint(0, 20))
    op = r.choice(["+", "-", "*", "==", "<", "&&", "||"])
    a = gen_expr(r, depth - 1, vars_)
    if op in ("&&", "||"):
        b = gen_expr(r, depth - 1, vars_)
        return f"({a} {op} {b})"
    # 避免除零：不用 / %，只用安全運算子
    b = gen_expr(r, depth - 1, vars_)
    if r.random() < 0.2:
        return f"!({a})"
    return f"({a} {op} {b})"

def gen_prog(seed):
    r = random.Random(seed)
    vars_ = [f"g{i}" for i in range(r.randint(1, 3))]
    lines = []
    for v in vars_:
        lines.append(f"let {v} = {r.randint(0, 50)};")
    lines.append("array buf[8];")
    lines.append("fn add2(a, b) { return a + b; }")
    lines.append("fn fact(n) { if (n <= 1) { return 1; } return n * fact(n - 1); }")
    # 主程式
    lines.append(f"print {gen_expr(r, 3, vars_)};")
    lines.append(f"print add2({r.randint(0,20)}, {r.randint(0,20)});")
    lines.append(f"print fact({r.randint(0,6)});")
    lines.append("let i = 0;")
    lines.append("while (i < 8) { buf[i] = i * 3 + 1; i = i + 1; }")
    lines.append(f"print buf[{r.randint(0,7)}];")
    if r.random() < 0.5:
        lines.append(f"if ({gen_expr(r, 2, vars_)}) {{ print 111; }} else {{ print 222; }}")
    # 全域字串指標索引（回歸測試曾經的 bug）
    lines.append('let s = "ABC";')
    lines.append("print s[0]; print s[1]; print s[2];")
    lines.append("s[0] = 90; print s[0];")
    return "\n".join(lines) + "\n"

def main(n=50):
    s0bytes, s2bytes = build_stages()
    assert s0bytes == s2bytes, "stage0 != stage2，前置不動點已破"
    open("/tmp/diff_stage2.ir", "wb").write(s2bytes)
    fails = 0
    for seed in range(n):
        src = gen_prog(seed).encode()
        with open("/tmp/diff_case.lm", "wb") as f:
            f.write(src)
        rc0, ir0, e0 = run([MINIC, "compile", "/tmp/diff_case.lm"])
        rc2, ir2, e2 = run([MINIC, "run", "/tmp/diff_stage2.ir"], src)
        if rc0 != 0 or rc2 != 0:
            print(f"seed {seed}: compile rc {rc0}/{rc2} {e0.decode()[:100]} {e2.decode()[:100]}")
            fails += 1
            continue
        if ir0 != ir2:
            print(f"seed {seed}: IR MISMATCH")
            fails += 1
            continue
        # 執行輸出比對
        with open("/tmp/diff_case.ir", "wb") as f:
            f.write(ir0)
        rcA, outA, errA = run([MINIC, "run", "/tmp/diff_case.ir"])
        # ir0 即 stage0 產物，直接跑
        if rcA != 0:
            print(f"seed {seed}: run fail {errA.decode()[:120]}")
            fails += 1
            continue
    print(f"{n-fails}/{n} passed")
    return 1 if fails else 0

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    sys.exit(main(n))
