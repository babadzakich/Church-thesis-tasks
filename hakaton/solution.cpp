// ============================================================
//  ЭТАЛОННОЕ РЕШЕНИЕ — 2-SAT + алгоритм Тарьяна
//  Сложность: O(N + M)
//  Компиляция: g++ -O2 -std=c++17 solution.cpp -o solution_cpp
// ============================================================
#include <iostream>
#include <vector>
#include <string>
#include <optional>
#include <algorithm>
#include <utility>

using namespace std;

// ------ Тарьян SCC -------------------------------------------
struct Tarjan {
    int                  n;
    vector<vector<int>>  graph;
    vector<int>          disc, low, scc;
    vector<bool>         on_stack;
    vector<int>          stk;
    int                  scc_count = 0;
    int                  timer     = 0;

    explicit Tarjan(int n, vector<vector<int>> g)
        : n(n), graph(move(g)),
          disc(n, -1), low(n), scc(n), on_stack(n, false) {}

    // Итеративный DFS — избегаем переполнения системного стека при N=10^5
    void dfs(int start) {
        disc[start] = low[start] = timer++;
        stk.push_back(start);
        on_stack[start] = true;

        // Явный стек: {вершина, индекс следующего соседа}
        vector<pair<int,int>> call;
        call.emplace_back(start, 0);

        while (!call.empty()) {
            auto& [u, idx] = call.back();
            if (idx < (int)graph[u].size()) {
                int w = graph[u][idx++];
                if (disc[w] == -1) {
                    disc[w] = low[w] = timer++;
                    stk.push_back(w);
                    on_stack[w] = true;
                    call.emplace_back(w, 0);
                } else if (on_stack[w]) {
                    low[u] = min(low[u], disc[w]);
                }
            } else {
                call.pop_back();
                if (!call.empty()) {
                    int parent = call.back().first;
                    low[parent] = min(low[parent], low[u]);
                }
                // u — корень SCC?
                if (low[u] == disc[u]) {
                    while (true) {
                        int w = stk.back(); stk.pop_back();
                        on_stack[w] = false;
                        scc[w] = scc_count;
                        if (w == u) break;
                    }
                    ++scc_count;
                }
            }
        }
    }

    vector<int> run() {
        for (int v = 0; v < n; ++v)
            if (disc[v] == -1) dfs(v);
        return move(scc);
    }
};

// ------ 2-SAT ------------------------------------------------
// Переменные: i → xi = 2i,  ¬xi = 2i+1
struct TwoSat {
    int                 n;
    vector<vector<int>> graph;

    explicit TwoSat(int n) : n(n), graph(2 * n) {}

    static int pos(int i) { return 2 * i; }
    static int neg(int i) { return 2 * i + 1; }
    static int NOT(int v) { return v ^ 1; }

    // Импликация a → b  (и контрпозиция ¬b → ¬a)
    void add_impl(int a, int b) {
        graph[a].push_back(b);
        graph[NOT(b)].push_back(NOT(a));
    }

    // DEP i j:      xi  →  xj
    void add_dep(int i, int j)      { add_impl(pos(i), pos(j)); }

    // CONFLICT i j: xi  → ¬xj  и  xj → ¬xi
    void add_conflict(int i, int j) {
        add_impl(pos(i), neg(j));
        add_impl(pos(j), neg(i));
    }

    // REQUIRE i:    ¬xi →  xi
    void add_require(int i)         { add_impl(neg(i), pos(i)); }

    // Возвращает optional<vector<bool>>:
    //   nullopt            — решения нет (IMPOSSIBLE)
    //   vector<bool> vals  — vals[i] = true означает сервис i ON
    optional<vector<bool>> solve() {
        auto scc = Tarjan(2 * n, graph).run();

        for (int i = 0; i < n; ++i)
            if (scc[pos(i)] == scc[neg(i)])
                return nullopt;

        // xi = TRUE  ⟺  scc[xi] < scc[¬xi]
        //
        // Тарьян нумерует SCC в ОБРАТНОМ топологическом порядке:
        //   scc = 0 — это сток (последний в топ. порядке).
        //   Меньший номер → «позже» в топ. порядке.
        // ¬xi должен стоять «раньше» xi (быть источником),
        // значит иметь БОЛЬШИЙ номер → xi = TRUE ⟺ scc[xi] < scc[¬xi].
        vector<bool> result(n);
        for (int i = 0; i < n; ++i)
            result[i] = scc[pos(i)] < scc[neg(i)];
        return result;
    }
};

// ------ main -------------------------------------------------
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    TwoSat sat(n);

    for (int q = 0; q < m; ++q) {
        string kind;
        cin >> kind;
        if (kind == "DEP") {
            int a, b; cin >> a >> b;
            sat.add_dep(a - 1, b - 1);
        } else if (kind == "CONFLICT") {
            int a, b; cin >> a >> b;
            sat.add_conflict(a - 1, b - 1);
        } else if (kind == "REQUIRE") {
            int a; cin >> a;
            sat.add_require(a - 1);
        }
    }

    auto result = sat.solve();
    if (!result) {
        cout << "IMPOSSIBLE\n";
    } else {
        for (int i = 0; i < n; ++i)
            cout << (i + 1) << ": " << ((*result)[i] ? "ON" : "OFF") << "\n";
    }
    return 0;
}