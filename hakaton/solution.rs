// ============================================================
//  ЭТАЛОННОЕ РЕШЕНИЕ — 2-SAT + алгоритм Тарьяна
//  Сложность: O(N + M)
// ============================================================
use std::io::{self, BufRead, Write, BufWriter};

// ------ Тарьян SCC -------------------------------------------
struct Tarjan {
    n:     usize,
    graph: Vec<Vec<usize>>,
    disc:  Vec<i32>,   // время открытия (-1 = не посещён)
    low:   Vec<i32>,
    on_stack: Vec<bool>,
    stack: Vec<usize>,
    scc:   Vec<usize>, // scc[v] = номер компоненты
    scc_count: usize,
    timer: i32,
}

impl Tarjan {
    fn new(n: usize, graph: Vec<Vec<usize>>) -> Self {
        Tarjan {
            n, graph,
            disc:     vec![-1; n],
            low:      vec![0;  n],
            on_stack: vec![false; n],
            stack:    Vec::new(),
            scc:      vec![0; n],
            scc_count: 0,
            timer:    0,
        }
    }

    fn dfs(&mut self, v: usize) {
        self.disc[v] = self.timer;
        self.low[v]  = self.timer;
        self.timer   += 1;
        self.stack.push(v);
        self.on_stack[v] = true;

        // Итеративный DFS
        // Используем явный стек: (вершина, индекс следующего соседа)
        let mut call_stack: Vec<(usize, usize)> = vec![(v, 0)];

        while let Some((u, idx)) = call_stack.last_mut() {
            let u = *u;
            let neighbors = &self.graph[u];
            if *idx < neighbors.len() {
                let w = neighbors[*idx];
                *idx += 1;
                if self.disc[w] == -1 {
                    // Не посещён — рекурсивный вызов
                    self.disc[w] = self.timer;
                    self.low[w]  = self.timer;
                    self.timer   += 1;
                    self.stack.push(w);
                    self.on_stack[w] = true;
                    call_stack.push((w, 0));
                } else if self.on_stack[w] {
                    // Обратное ребро — обновляем low
                    let dw = self.disc[w];
                    self.low[u] = self.low[u].min(dw);
                }
            } else {
                // Все соседи обработаны
                call_stack.pop();
                if let Some(&(parent, _)) = call_stack.last() {
                    let lu = self.low[u];
                    self.low[parent] = self.low[parent].min(lu);
                }
                // Если u — корень SCC
                if self.low[u] == self.disc[u] {
                    while let Some(w) = self.stack.pop() {
                        self.on_stack[w] = false;
                        self.scc[w] = self.scc_count;
                        if w == u { break; }
                    }
                    self.scc_count += 1;
                }
            }
        }
    }

    fn run(mut self) -> Vec<usize> {
        for v in 0..self.n {
            if self.disc[v] == -1 {
                self.dfs(v);
            }
        }
        self.scc
    }
}

// ------ 2-SAT ------------------------------------------------
// Переменные: 0..n-1 → xi = 2i, ¬xi = 2i+1
fn var_pos(i: usize) -> usize { 2 * i }
fn var_neg(i: usize) -> usize { 2 * i + 1 }
fn var_not(v: usize) -> usize { v ^ 1 }

struct TwoSat {
    n:     usize,
    graph: Vec<Vec<usize>>,
}

impl TwoSat {
    fn new(n: usize) -> Self {
        TwoSat { n, graph: vec![vec![]; 2 * n] }
    }

    // Импликация: a → b
    fn add_impl(&mut self, a: usize, b: usize) {
        self.graph[a].push(b);
        // Контрпозиция: ¬b → ¬a (автоматически)
        self.graph[var_not(b)].push(var_not(a));
    }

    // DEP i j: если включён i → включён j  (xi → xj)
    fn add_dep(&mut self, i: usize, j: usize) {
        self.add_impl(var_pos(i), var_pos(j));
    }

    // CONFLICT i j: ¬(xi ∧ xj) → xi → ¬xj
    fn add_conflict(&mut self, i: usize, j: usize) {
        self.add_impl(var_pos(i), var_neg(j));
        self.add_impl(var_pos(j), var_neg(i));
    }

    // REQUIRE i: ¬xi → xi
    fn add_require(&mut self, i: usize) {
        self.add_impl(var_neg(i), var_pos(i));
    }

    fn solve(self) -> Option<Vec<bool>> {
        let n = self.n;
        let scc = Tarjan::new(2 * n, self.graph).run();

        // Проверка: xi и ¬xi не должны быть в одной SCC
        for i in 0..n {
            if scc[var_pos(i)] == scc[var_neg(i)] {
                return None;
            }
        }

        // xi = true, если SCC(xi) < SCC(¬xi)
        //
        // Тарьян нумерует SCC в ОБРАТНОМ топологическом порядке:
        //   SCC с номером 0 — это сток (последний в топ. порядке).
        //   Чем выше номер — тем раньше в топ. порядке (источник).
        //
        // xi должен быть TRUE, если ¬xi "раньше" xi в топ. порядке,
        // то есть ¬xi имеет БОЛЬШИЙ номер Тарьяна.
        // Следовательно: xi = TRUE ⟺ scc[xi] < scc[¬xi]
        let result = (0..n)
            .map(|i| scc[var_pos(i)] < scc[var_neg(i)])
            .collect();
        Some(result)
    }
}

fn main() {
    let stdin  = io::stdin();
    let stdout = io::stdout();
    let mut out = BufWriter::new(stdout.lock());

    let mut lines = stdin.lock().lines();
    let first = lines.next().unwrap().unwrap();
    let mut it = first.split_whitespace();
    let n: usize = it.next().unwrap().parse().unwrap();
    let m: usize = it.next().unwrap().parse().unwrap();

    let mut sat = TwoSat::new(n);

    for _ in 0..m {
        let line = lines.next().unwrap().unwrap();
        let mut parts = line.split_whitespace();
        let kind = parts.next().unwrap();
        match kind {
            "DEP" => {
                let a: usize = parts.next().unwrap().parse::<usize>().unwrap() - 1;
                let b: usize = parts.next().unwrap().parse::<usize>().unwrap() - 1;
                sat.add_dep(a, b);
            }
            "CONFLICT" => {
                let a: usize = parts.next().unwrap().parse::<usize>().unwrap() - 1;
                let b: usize = parts.next().unwrap().parse::<usize>().unwrap() - 1;
                sat.add_conflict(a, b);
            }
            "REQUIRE" => {
                let a: usize = parts.next().unwrap().parse::<usize>().unwrap() - 1;
                sat.add_require(a);
            }
            _ => panic!("Unknown constraint: {}", kind),
        }
    }

    match sat.solve() {
        None => writeln!(out, "IMPOSSIBLE").unwrap(),
        Some(vals) => {
            for (i, &v) in vals.iter().enumerate() {
                writeln!(out, "{}: {}", i + 1, if v { "ON" } else { "OFF" }).unwrap();
            }
        }
    }
}