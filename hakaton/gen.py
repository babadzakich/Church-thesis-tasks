import os, random, subprocess, sys, time

os.makedirs("tests/simple", exist_ok=True)
os.makedirs("tests/hard",   exist_ok=True)


# ─── Вспомогательная проверка (Python-реализация наива) ──────────────────────
def python_naive(n, constraints):
    for mask in range(1 << n):
        ok = True
        for kind, *args in constraints:
            if kind == "DEP":
                a, b = args
                if (mask >> a) & 1 and not (mask >> b) & 1:
                    ok = False; break
            elif kind == "CONFLICT":
                a, b = args
                if (mask >> a) & 1 and (mask >> b) & 1:
                    ok = False; break
            elif kind == "REQUIRE":
                a, = args
                if not (mask >> a) & 1:
                    ok = False; break
        if ok:
            return ["ON" if (mask >> i) & 1 else "OFF" for i in range(n)]
    return None


def write_test(path, n, constraints):
    with open(path, "w") as f:
        f.write(f"{n} {len(constraints)}\n")
        for c in constraints:
            if c[0] == "DEP":
                f.write(f"DEP {c[1]+1} {c[2]+1}\n")
            elif c[0] == "CONFLICT":
                f.write(f"CONFLICT {c[1]+1} {c[2]+1}\n")
            elif c[0] == "REQUIRE":
                f.write(f"REQUIRE {c[1]+1}\n")


def write_answer(path, result):
    with open(path, "w") as f:
        if result is None:
            f.write("IMPOSSIBLE\n")
        else:
            for i, v in enumerate(result):
                f.write(f"{i+1}: {v}\n")


# ─── ПРОСТЫЕ ТЕСТЫ ───────────────────────────────────────────────────────────
def gen_simple():
    tests = []

    # Тест 1: Пример 1 из условия
    t1_c = [("DEP",0,1),("DEP",0,2),("CONFLICT",1,3),("REQUIRE",0)]
    tests.append(("01_example1", 4, t1_c))

    # Тест 2: Пример 2 из условия — IMPOSSIBLE
    t2_c = [("REQUIRE",0),("REQUIRE",1),("CONFLICT",0,1)]
    tests.append(("02_example2", 2, t2_c))

    # Тест 3: Пример 3 — цепочка + конфликт — IMPOSSIBLE
    t3_c = [("DEP",0,1),("DEP",1,2),("DEP",2,3),("CONFLICT",0,3),("REQUIRE",0)]
    tests.append(("03_example3", 5, t3_c))

    # Тест 4: Один сервис, REQUIRE
    tests.append(("04_single_require", 1, [("REQUIRE",0)]))

    # Тест 5: Один сервис, без ограничений
    tests.append(("05_single_free", 1, []))

    # Тест 6: Все независимы, все required
    n6 = 5
    c6 = [("REQUIRE", i) for i in range(n6)]
    tests.append(("06_all_required", n6, c6))

    # Тест 7: Полный граф конфликтов на 3 — POSSIBLE (выключить все)
    tests.append(("07_triangle_conflict", 3,
        [("CONFLICT",0,1),("CONFLICT",1,2),("CONFLICT",0,2)]))

    # Тест 8: Полный граф конфликтов на 3, все required — IMPOSSIBLE
    tests.append(("08_triangle_conflict_required", 3,
        [("CONFLICT",0,1),("CONFLICT",1,2),("CONFLICT",0,2),
         ("REQUIRE",0),("REQUIRE",1),("REQUIRE",2)]))

    # Тест 9: Цепочка зависимостей
    n9 = 6
    c9 = [("DEP", i, i+1) for i in range(n9-1)] + [("REQUIRE", 0)]
    tests.append(("09_dep_chain", n9, c9))

    # Тест 10: Два кластера, независимые, один конфликт между кластерами
    tests.append(("10_two_clusters", 6, [
        ("REQUIRE",0),("DEP",0,1),("DEP",0,2),
        ("REQUIRE",3),("DEP",3,4),("DEP",3,5),
        ("CONFLICT",1,4),
    ]))

    for name, n, c in tests:
        answer = python_naive(n, c)
        write_test(f"tests/simple/{name}.in", n, c)
        write_answer(f"tests/simple/{name}.ans", answer)
        status = "POSSIBLE  " if answer else "IMPOSSIBLE"
        print(f"  [{status}] {name}  (N={n}, M={len(c)})")

    print(f"\n✓ Сгенерировано {len(tests)} простых тестов в tests/simple/")


# ─── ТЯЖЁЛЫЕ ТЕСТЫ ───────────────────────────────────────────────────────────
# Две категории:
#   H1-H5: N=100 000 — проверяют корректность и скорость эталона
#   H6-H7: N=28/30  — специально для TLE наива (2^28 ≈ 268M, 2^30 ≈ 1B итераций)
def gen_hard():

    def chain(n):
        """Длинная цепочка DEP"""
        c = [("DEP", i, i+1) for i in range(n-1)]
        c.append(("REQUIRE", 0))
        return n, c

    def butterfly(n):
        """Все зависят от 0 или 1, конфликты на концах"""
        c = []
        for i in range(2, n):
            c.append(("DEP", 0 if i % 2 == 0 else 1, i))
        for i in range(2, n-1, 2):
            c.append(("CONFLICT", i, i+1))
        c.append(("REQUIRE", 0))
        c.append(("REQUIRE", 1))
        return n, c

    def random_conflicts(n, m, seed=42):
        """Только конфликты → всегда есть решение (все OFF)"""
        rng = random.Random(seed)
        seen = set()
        c = []
        while len(c) < m:
            a = rng.randint(0, n-1)
            b = rng.randint(0, n-1)
            if a != b and (a,b) not in seen:
                seen.add((a,b)); seen.add((b,a))
                c.append(("CONFLICT", a, b))
        return n, c

    def random_deps(n, m, seed=99):
        """Случайный ациклический DAG зависимостей + REQUIRE 1"""
        rng = random.Random(seed)
        seen = set()
        c = []
        while len(c) < m:
            a = rng.randint(0, n-2)
            b = rng.randint(a+1, n-1)
            if (a,b) not in seen:
                seen.add((a,b))
                c.append(("DEP", a, b))
        c.append(("REQUIRE", 0))
        return n, c

    def impossible_chain(n):
        """Цепочка DEP + конфликт на концах + REQUIRE → IMPOSSIBLE"""
        c = [("DEP", i, i+1) for i in range(n-1)]
        c.append(("CONFLICT", 0, n-1))
        c.append(("REQUIRE", 0))
        return n, c

    def tle_possible(n, seed=7):
        """
        N=28-30: случайный граф без явного решения «все OFF».
        Наив перебирает 2^N конфигураций и умирает от TLE.
        Эталон решает за O(N+M).
        Гарантируем наличие решения: строим ациклический DEP-граф,
        никаких REQUIRE и CONFLICT → все OFF всегда годится,
        но наив всё равно должен проверить все 2^N масок в худшем случае
        (если IMPOSSIBLE — наив пробежит всё до конца).
        Делаем IMPOSSIBLE-вариант, чтобы наив точно пробежал все маски.
        """
        rng = random.Random(seed)
        # Строим плотный граф зависимостей + конфликты, которые делают
        # большинство конфигураций недопустимыми, плюс REQUIRE на всех →
        # ищем долго, а на самом деле IMPOSSIBLE
        c = [("DEP", i, i+1) for i in range(n-1)]
        # Добавляем конфликты, которые замыкают цикл → IMPOSSIBLE
        c.append(("CONFLICT", 0, n-1))
        c.append(("REQUIRE", 0))
        # Дополнительные рёбра для плотности
        for i in range(0, n-3, 3):
            c.append(("CONFLICT", i, i+2))
        return n, c

    spec = [
        # --- Большие тесты для эталона (N=100 000) ---
        ("H1_chain_100k",           *chain(100_000)),
        ("H2_butterfly_100k",       *butterfly(100_000)),
        ("H3_random_conflicts_100k",*random_conflicts(100_000, 200_000)),
        ("H4_random_deps_100k",     *random_deps(100_000, 200_000)),
        ("H5_impossible_chain_100k",*impossible_chain(100_000)),
        # --- TLE-тесты для наива (N=28/30, 2^28-2^30 итераций) ---
        ("H6_tle_n28",              *tle_possible(28)),
        ("H7_tle_n30",              *tle_possible(30, seed=13)),
    ]

    for name, n, c in spec:
        write_test(f"tests/hard/{name}.in", n, c)
        naive_limit = "≈268M iter" if n == 28 else ("≈1B iter" if n == 30 else "TLE")
        if n <= 30:
            print(f"  [TLE-target] {name}  (N={n}, M={len(c)})  naïve={naive_limit}")
        else:
            print(f"  [Big N     ] {name}  (N={n}, M={len(c)})  ← ответ через verify_hard")

    print(f"\n✓ Сгенерировано {len(spec)} тяжёлых тестов в tests/hard/")
    print("  Запусти: python3 gen.py verify_hard — чтобы получить .ans файлы")


# ─── ВЕРИФИКАЦИЯ ТЯЖЁЛЫХ ТЕСТОВ через скомпилированный эталон ────────────────
def verify_hard():
    import glob
    for inp in sorted(glob.glob("tests/hard/*.in")):
        ans = inp.replace(".in", ".ans")
        t0 = time.time()
        result = subprocess.run(["./solution"], stdin=open(inp), capture_output=True, text=True)
        elapsed = time.time() - t0
        with open(ans, "w") as f:
            f.write(result.stdout)
        first_line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else "?"
        print(f"  {os.path.basename(inp):45s}  {elapsed*1000:6.0f}ms  {first_line}")


# ─── СТРЕСС-ТЕСТ ─────────────────────────────────────────────────────────────
def stress(iterations=500):
    """
    Запускает N итераций:
    - Генерирует случайный тест (маленький, чтобы наивы прошли)
    - Прогоняет все четыре решения: solution (Rust), solution_c (C),
      naive (Rust), naive_c (C)
    - Проверяет POSSIBLE/IMPOSSIBLE согласованность и корректность каждого ответа
    """
    ok_count = 0
    for it in range(iterations):
        rng = random.Random(it)
        n = rng.randint(2, 8)
        m = rng.randint(0, min(15, n*(n-1)))

        constraints = []
        for _ in range(m):
            kind = rng.choice(["DEP", "CONFLICT", "REQUIRE"])
            if kind in ("DEP", "CONFLICT"):
                a = rng.randint(0, n-1)
                b = rng.randint(0, n-1)
                while b == a:
                    b = rng.randint(0, n-1)
                constraints.append((kind, a, b))
            else:
                a = rng.randint(0, n-1)
                constraints.append(("REQUIRE", a))

        constraints = list(set(constraints))

        lines = [f"{n} {len(constraints)}"]
        for c in constraints:
            if c[0] == "DEP":
                lines.append(f"DEP {c[1]+1} {c[2]+1}")
            elif c[0] == "CONFLICT":
                lines.append(f"CONFLICT {c[1]+1} {c[2]+1}")
            else:
                lines.append(f"REQUIRE {c[1]+1}")
        inp_str = "\n".join(lines) + "\n"

        # Запуск всех четырёх решений
        r_sol   = subprocess.run(["./solution"],   input=inp_str, capture_output=True, text=True)
        r_sol_c = subprocess.run(["./solution_c"], input=inp_str, capture_output=True, text=True)
        r_naive   = subprocess.run(["./naive"],     input=inp_str, capture_output=True, text=True)
        r_naive_c = subprocess.run(["./naive_c"],   input=inp_str, capture_output=True, text=True)

        sol_out     = r_sol.stdout.strip()
        sol_c_out   = r_sol_c.stdout.strip()
        naive_out   = r_naive.stdout.strip()
        naive_c_out = r_naive_c.stdout.strip()

        sol_impossible     = (sol_out == "IMPOSSIBLE")
        sol_c_impossible   = (sol_c_out == "IMPOSSIBLE")
        naive_impossible   = (naive_out == "IMPOSSIBLE")
        naive_c_impossible = (naive_c_out == "IMPOSSIBLE")

        # 1. Согласованность: все четыре должны совпадать в вопросе POSSIBLE/IMPOSSIBLE
        for label, flag in [("solution (Rust)", sol_impossible),
                            ("solution_c (C)",  sol_c_impossible),
                            ("naive_c (C)",     naive_c_impossible)]:
            if flag != naive_impossible:
                print(f"\n✗ РАСХОЖДЕНИЕ {label}/naive на итерации {it}!")
                print("Вход:\n" + inp_str)
                binaries = {"solution (Rust)": sol_out, "solution_c (C)": sol_c_out,
                            "naive (Rust)": naive_out, "naive_c (C)": naive_c_out}
                for k, v in binaries.items():
                    print(f"  {k}: {v[:200]}")
                sys.exit(1)

        def check_solution(label, out):
            """Проверяет, что данное решение удовлетворяет всем ограничениям."""
            vals = {}
            for line in out.splitlines():
                idx, state = line.split(": ")
                vals[int(idx)-1] = (state == "ON")
            for c in constraints:
                violated = False
                if c[0] == "DEP":
                    a, b = c[1], c[2]
                    if vals[a] and not vals[b]: violated = True
                elif c[0] == "CONFLICT":
                    a, b = c[1], c[2]
                    if vals[a] and vals[b]: violated = True
                elif c[0] == "REQUIRE":
                    if not vals[c[1]]: violated = True
                if violated:
                    print(f"\n✗ НАРУШЕНИЕ ОГРАНИЧЕНИЯ [{label}] на итерации {it}!")
                    print("Вход:\n" + inp_str)
                    print(f"{label}:", out)
                    print("Нарушено:", c)
                    sys.exit(1)

        if not sol_impossible:
            # 2. Проверяем, что все четыре решения удовлетворяют ограничениям
            check_solution("solution (Rust)", sol_out)
            check_solution("solution_c (C)",  sol_c_out)
            check_solution("naive (Rust)",    naive_out)
            check_solution("naive_c (C)",     naive_c_out)

        ok_count += 1

    print(f"✓ Стресс-тест пройден: {ok_count}/{iterations} итераций без ошибок (solution Rust + C, naive Rust + C)")


# ─── ЗАМЕР ВРЕМЕНИ (эталон vs наив) ──────────────────────────────────────────
def benchmark():
    import glob

    BINARIES = [
        ("solution (Rust)", "./solution"),
        ("solution_c  (C)", "./solution_c"),
        ("naive   (Rust)",  "./naive"),
        ("naive_c     (C)", "./naive_c"),
    ]

    def run_one(binary, inp, timeout=10):
        """Запускает binary на inp, возвращает (result_line, elapsed_ms_str)."""
        try:
            t0 = time.time()
            r = subprocess.run([binary], stdin=open(inp),
                               capture_output=True, timeout=timeout, text=True)
            elapsed = (time.time() - t0) * 1000
            stdout = r.stdout.strip()
            if stdout:
                first = stdout.splitlines()[0]
                if "NAIVE_TLE" in first:
                    return first, "NAIVE_TLE"
                return first, f"{elapsed:6.0f} ms"
            # stdout пуст — процесс упал (паника, переполнение и т.п.)
            if r.returncode != 0:
                return f"CRASH({r.returncode})", f"{elapsed:6.0f} ms"
            return "(no output)", f"{elapsed:6.0f} ms"
        except subprocess.TimeoutExpired:
            return "TLE", ">10s"

    inputs = sorted(glob.glob("tests/hard/*.in"))

    # Ширина колонок
    name_w   = 30   # имя файла
    result_w = 12   # POSSIBLE/IMPOSSIBLE
    time_w   = 10   # время

    col_w = result_w + time_w + 1  # ширина содержимого одной колонки бинарника
    header_labels = [label for label, _ in BINARIES]

    # Разделитель: + для пересечений, - для горизонталей
    def make_sep():
        s = "+" + "-" * (name_w + 2)
        for _ in BINARIES:
            s += "+" + "-" * (col_w + 2)
        return s + "+"

    sep = make_sep()
    print()
    print(sep)
    header = f"| {'Тест':<{name_w}} "
    for label in header_labels:
        header += f"| {label:^{col_w}} "
    header += "|"
    print(header)
    print(sep)

    for inp in inputs:
        name = os.path.basename(inp).replace(".in", "")
        row = f"| {name:<{name_w}} "
        for _, binary in BINARIES:
            result, timing = run_one(binary, inp)
            cell = f"{result:<{result_w}} {timing:>{time_w}}"
            row += f"| {cell} "
        row += "|"
        print(row)

    print(sep)
    print()

# ─── ПАРСИНГ .in ФАЙЛА В СПИСОК ОГРАНИЧЕНИЙ ──────────────────────────────────
def parse_input(path):
    """Возвращает (n, constraints) где constraints — список кортежей."""
    with open(path) as f:
        lines = f.read().splitlines()
    n, m = map(int, lines[0].split())
    constraints = []
    for line in lines[1:m+1]:
        parts = line.split()
        if parts[0] == "DEP":
            constraints.append(("DEP", int(parts[1])-1, int(parts[2])-1))
        elif parts[0] == "CONFLICT":
            constraints.append(("CONFLICT", int(parts[1])-1, int(parts[2])-1))
        elif parts[0] == "REQUIRE":
            constraints.append(("REQUIRE", int(parts[1])-1))
    return n, constraints


def validate_output(out, n, constraints, expected_impossible):
    """
    Проверяет корректность вывода решения.
    Возвращает (ok: bool, reason: str).
    """
    got_impossible = (out == "IMPOSSIBLE")

    if expected_impossible and got_impossible:
        return True, ""
    if expected_impossible and not got_impossible:
        return False, "got POSSIBLE, expected IMPOSSIBLE"
    if not expected_impossible and got_impossible:
        return False, "got IMPOSSIBLE, expected POSSIBLE"

    # Проверяем, что ответ удовлетворяет всем ограничениям
    try:
        vals = {}
        for line in out.splitlines():
            idx, state = line.split(": ")
            vals[int(idx)-1] = (state == "ON")
        if len(vals) != n:
            return False, f"wrong number of lines: {len(vals)} != {n}"
    except Exception as e:
        return False, f"parse error: {e}"

    for c in constraints:
        if c[0] == "DEP":
            a, b = c[1], c[2]
            if vals[a] and not vals[b]:
                return False, f"DEP {a+1} {b+1} violated"
        elif c[0] == "CONFLICT":
            a, b = c[1], c[2]
            if vals[a] and vals[b]:
                return False, f"CONFLICT {a+1} {b+1} violated"
        elif c[0] == "REQUIRE":
            a = c[1]
            if not vals[a]:
                return False, f"REQUIRE {a+1} violated"
    return True, ""


# ─── ЗАПУСК ПРОСТЫХ ТЕСТОВ ───────────────────────────────────────────────────
def test_simple():
    import glob

    BINARIES = [
        ("solution (Rust)", "./solution"),
        ("solution_c  (C)", "./solution_c"),
        ("naive   (Rust)",  "./naive"),
        ("naive_c     (C)", "./naive_c"),
    ]

    def run_one(binary, inp, n, constraints, expected_impossible, timeout=10):
        try:
            t0 = time.time()
            r = subprocess.run([binary], stdin=open(inp),
                               capture_output=True, timeout=timeout, text=True)
            elapsed = (time.time() - t0) * 1000
            out = r.stdout.strip()
            ok, reason = validate_output(out, n, constraints, expected_impossible)
            status = "PASS" if ok else f"FAIL"
            return status, f"{elapsed:5.0f} ms", reason
        except subprocess.TimeoutExpired:
            return "TLE", ">10s", ""

    inputs = sorted(glob.glob("tests/simple/*.in"))

    name_w  = 32
    col_w   = 16

    def make_sep():
        s = "+" + "-" * (name_w + 2)
        for _ in BINARIES:
            s += "+" + "-" * (col_w + 2)
        return s + "+"

    sep = make_sep()
    print()
    print(sep)
    header = f"| {'Тест':<{name_w}} "
    for label, _ in BINARIES:
        header += f"| {label:^{col_w}} "
    header += "|"
    print(header)
    print(sep)

    total  = {label: 0 for label, _ in BINARIES}
    passed = {label: 0 for label, _ in BINARIES}
    failures = []

    for inp in inputs:
        ans_path = inp.replace(".in", ".ans")
        expected_impossible = open(ans_path).read().strip() == "IMPOSSIBLE"
        n, constraints = parse_input(inp)
        name = os.path.basename(inp).replace(".in", "")
        row = f"| {name:<{name_w}} "
        for label, binary in BINARIES:
            status, timing, reason = run_one(binary, inp, n, constraints, expected_impossible)
            cell = f"{status}  {timing}"
            row += f"| {cell:^{col_w}} "
            total[label] += 1
            if status == "PASS":
                passed[label] += 1
            elif status == "FAIL" and reason:
                failures.append(f"  [{label}] {name}: {reason}")
        row += "|"
        print(row)

    print(sep)

    # Итоговая строка
    summary = f"| {'ИТОГО':<{name_w}} "
    for label, _ in BINARIES:
        cell = f"{passed[label]}/{total[label]}"
        summary += f"| {cell:^{col_w}} "
    summary += "|"
    print(summary)
    print(sep)
    print()

    if failures:
        print("Детали ошибок:")
        for f in failures:
            print(f)
        print()


# ─── ТЕСТ ОДНОГО БИНАРНИКА ────────────────────────────────────────────────────────────────

def test_binary(binary):
    import glob

    label = os.path.basename(binary)
    name_w  = 32
    col_w   = 20

    def make_sep():
        return "+" + "-" * (name_w + 2) + "+" + "-" * (col_w + 2) + "+"

    sep = make_sep()

    # ─── СТАДИЯ 1: простые тесты ──────────────────────────────────────────
    print(f"\n[Этап 1] Простые тесты  ({label})")
    print(sep)
    header = f"| {'Тест':<{name_w}} | {label:^{col_w}} |"
    print(header)
    print(sep)

    total_s = passed_s = 0
    failures = []

    def run_simple(inp, timeout=10):
        n, constraints = parse_input(inp)
        ans_path = inp.replace(".in", ".ans")
        expected_impossible = open(ans_path).read().strip() == "IMPOSSIBLE"
        try:
            t0 = time.time()
            r = subprocess.run([binary], stdin=open(inp),
                               capture_output=True, timeout=timeout, text=True)
            elapsed = (time.time() - t0) * 1000
            out = r.stdout.strip()
            ok, reason = validate_output(out, n, constraints, expected_impossible)
            return ("PASS" if ok else "FAIL"), f"{elapsed:5.0f} ms", reason
        except subprocess.TimeoutExpired:
            return "TLE", ">10s", ""

    for inp in sorted(glob.glob("tests/simple/*.in")):
        name = os.path.basename(inp).replace(".in", "")
        status, timing, reason = run_simple(inp)
        cell = f"{status}  {timing}"
        print(f"| {name:<{name_w}} | {cell:^{col_w}} |")
        total_s += 1
        if status == "PASS":
            passed_s += 1
        elif reason:
            failures.append(f"  {name}: {reason}")

    print(sep)
    result_cell = f"{passed_s}/{total_s}"
    print(f"| {'ИТОГО':<{name_w}} | {result_cell:^{col_w}} |")
    print(sep)

    if failures:
        print("  Ошибки:")
        for f in failures:
            print(f)

    # ─── СТАДИЯ 2: тяжёлые тесты ─────────────────────────────────────────
    result_w = 12
    time_w   = 10
    hard_col_w = result_w + time_w + 1

    def make_hard_sep():
        return "+" + "-" * (name_w + 2) + "+" + "-" * (hard_col_w + 2) + "+"

    hard_sep = make_hard_sep()

    print(f"\n[Этап 2] Тяжёлые тесты / бенчмарк  ({label})")
    print(hard_sep)
    print(f"| {'Тест':<{name_w}} | {label:^{hard_col_w}} |")
    print(hard_sep)

    def run_hard(inp, timeout=10):
        try:
            t0 = time.time()
            r = subprocess.run([binary], stdin=open(inp),
                               capture_output=True, timeout=timeout, text=True)
            elapsed = (time.time() - t0) * 1000
            stdout = r.stdout.strip()
            if stdout:
                first = stdout.splitlines()[0]
                if "NAIVE_TLE" in first:
                    return first, "NAIVE_TLE"
                return first, f"{elapsed:6.0f} ms"
            if r.returncode != 0:
                return f"CRASH({r.returncode})", f"{elapsed:6.0f} ms"
            return "(no output)", f"{elapsed:6.0f} ms"
        except subprocess.TimeoutExpired:
            return "TLE", ">10s"

    for inp in sorted(glob.glob("tests/hard/*.in")):
        name = os.path.basename(inp).replace(".in", "")
        result, timing = run_hard(inp)
        cell = f"{result:<{result_w}} {timing:>{time_w}}"
        print(f"| {name:<{name_w}} | {cell} |")

    print(hard_sep)
    print()


# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "simple":
        print("Генерирую простые тесты...")
        gen_simple()
    elif cmd == "hard":
        print("Генерирую тяжёлые тесты...")
        gen_hard()
    elif cmd == "verify_hard":
        print("Верифицирую тяжёлые тесты через эталон...")
        verify_hard()
    elif cmd == "stress":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 500
        print(f"Запускаю стресс-тест ({n} итераций)...")
        stress(n)
    elif cmd == "benchmark":
        benchmark()
    elif cmd == "test":
        if len(sys.argv) < 3:
            print("Использование: python3 gen.py test <путь_к_бинарнику>")
            sys.exit(1)
        binary = sys.argv[2]
        if not binary.startswith("./") and not os.path.isabs(binary):
            binary = "./" + binary
        test_binary(binary)
    elif cmd == "test_simple":
        print("Запускаю простые тесты...")
        test_simple()
    elif cmd == "all":
        print("=== Простые тесты ==="); gen_simple()
        print("\n=== Тяжёлые тесты ==="); gen_hard()
    elif cmd == "run_all":
        # 1. Компиляция
        print("=" * 60)
        print("1/5  Компиляция...")
        print("=" * 60)
        cmds = [
            ("rustc -O solution.rs -o solution",   "solution (Rust)"),
            ("rustc naive.rs -o naive",             "naive    (Rust)"),
            ("gcc -O2 solution.c -o solution_c",   "solution (C)"),
            ("gcc -O2 naive.c -o naive_c",         "naive    (C)"),
        ]
        ok = True
        for cmd_str, label in cmds:
            r = subprocess.run(cmd_str.split(), capture_output=True, text=True)
            status = "OK" if r.returncode == 0 else "FAILED"
            print(f"  {label:20s}  {status}")
            if r.returncode != 0:
                print(r.stderr[:300])
                ok = False
        if not ok:
            print("\nКомпиляция завершилась с ошибками. Прерываю.")
            sys.exit(1)

        # 2. Простые тесты
        print()
        print("=" * 60)
        print("2/5  Генерация простых тестов...")
        print("=" * 60)
        gen_simple()

        # 3. Тяжёлые тесты
        print()
        print("=" * 60)
        print("3/5  Генерация тяжёлых тестов...")
        print("=" * 60)
        gen_hard()

        # 4. Верификация тяжёлых тестов
        print()
        print("=" * 60)
        print("4/5  Верификация тяжёлых тестов (./solution)...")
        print("=" * 60)
        verify_hard()

        # 5. Простые тесты — проверка всех решений
        print()
        print("=" * 60)
        print("5a/5  Простые тесты — проверка всех решений...")
        print("=" * 60)
        test_simple()

        # 5b. Бенчмарк на тяжёлых тестах
        print("=" * 60)
        print("5b/5  Бенчмарк тяжёлых тестов...")
        print("=" * 60)
        benchmark()
    else:
        print(__doc__)