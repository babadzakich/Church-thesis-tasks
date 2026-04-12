// ============================================================
//  НАИВНОЕ РЕШЕНИЕ — полный перебор 2^N конфигураций
//  Сложность: O(2^N * M)
//  Работает только при N ≤ ~20
// ============================================================
use std::io::{self, BufRead, Write, BufWriter};

#[derive(Debug)]
enum Constraint {
    Dep(usize, usize),       // если A включён → B включён
    Conflict(usize, usize),  // A и B не могут быть включены вместе
    Require(usize),          // A обязательно включён
}

fn check(state: u64, constraints: &[Constraint]) -> bool {
    let on = |i: usize| (state >> i) & 1 == 1;

    for c in constraints {
        match c {
            Constraint::Dep(a, b) => {
                // A → B: не может быть A=true, B=false
                if on(*a) && !on(*b) { return false; }
            }
            Constraint::Conflict(a, b) => {
                if on(*a) && on(*b) { return false; }
            }
            Constraint::Require(a) => {
                if !on(*a) { return false; }
            }
        }
    }
    true
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

    let mut constraints = Vec::with_capacity(m);

    for _ in 0..m {
        let line = lines.next().unwrap().unwrap();
        let mut parts = line.split_whitespace();
        let kind = parts.next().unwrap();
        match kind {
            "DEP" => {
                let a: usize = parts.next().unwrap().parse::<usize>().unwrap() - 1;
                let b: usize = parts.next().unwrap().parse::<usize>().unwrap() - 1;
                constraints.push(Constraint::Dep(a, b));
            }
            "CONFLICT" => {
                let a: usize = parts.next().unwrap().parse::<usize>().unwrap() - 1;
                let b: usize = parts.next().unwrap().parse::<usize>().unwrap() - 1;
                constraints.push(Constraint::Conflict(a, b));
            }
            "REQUIRE" => {
                let a: usize = parts.next().unwrap().parse::<usize>().unwrap() - 1;
                constraints.push(Constraint::Require(a));
            }
            _ => panic!("Unknown constraint: {}", kind),
        }
    }

    // Перебираем все 2^N конфигураций
    let total = 1u64 << n;
    let mut found = false;

    for mask in 0..total {
        if check(mask, &constraints) {
            for i in 0..n {
                let on = (mask >> i) & 1 == 1;
                writeln!(out, "{}: {}", i + 1, if on { "ON" } else { "OFF" }).unwrap();
            }
            found = true;
            break;
        }
    }

    if !found {
        writeln!(out, "IMPOSSIBLE").unwrap();
    }
}