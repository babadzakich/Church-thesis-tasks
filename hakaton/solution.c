// ============================================================
//  ЭТАЛОННОЕ РЕШЕНИЕ — 2-SAT + алгоритм Тарьяна
//  Сложность: O(N + M)
// ============================================================
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// ------ Динамический массив (вектор) -------------------------
typedef struct {
    int *data;
    int  size;
    int  cap;
} Vec;

static void vec_init(Vec *v) {
    v->data = NULL;
    v->size = 0;
    v->cap  = 0;
}

static void vec_push(Vec *v, int x) {
    if (v->size == v->cap) {
        v->cap = v->cap ? v->cap * 2 : 4;
        v->data = realloc(v->data, v->cap * sizeof(int));
    }
    v->data[v->size++] = x;
}

static void vec_free(Vec *v) {
    free(v->data);
    v->data = NULL;
    v->size = v->cap = 0;
}

// ------ Тарьян SCC -------------------------------------------
typedef struct {
    int      n;
    Vec     *graph;
    int     *disc;
    int     *low;
    int     *on_stack;
    int     *stack;
    int      stack_top;
    int     *scc;
    int      scc_count;
    int      timer;
} Tarjan;

static Tarjan *tarjan_new(int n, Vec *graph) {
    Tarjan *t = malloc(sizeof(Tarjan));
    t->n         = n;
    t->graph     = graph;
    t->disc      = malloc(n * sizeof(int));
    t->low       = malloc(n * sizeof(int));
    t->on_stack  = calloc(n, sizeof(int));
    t->stack     = malloc(n * sizeof(int));
    t->stack_top = 0;
    t->scc       = malloc(n * sizeof(int));
    t->scc_count = 0;
    t->timer     = 0;
    memset(t->disc, -1, n * sizeof(int));
    return t;
}

static void tarjan_free(Tarjan *t) {
    free(t->disc);
    free(t->low);
    free(t->on_stack);
    free(t->stack);
    free(t->scc);
    free(t);
}

// Пара (вершина, индекс соседа) для итеративного DFS
typedef struct { int v; int idx; } Frame;

static void tarjan_dfs(Tarjan *t, int start) {
    t->disc[start] = t->timer;
    t->low[start]  = t->timer;
    t->timer++;
    t->stack[t->stack_top++] = start;
    t->on_stack[start] = 1;

    // Явный стек вызовов
    Frame *call_stack = malloc(t->n * sizeof(Frame));
    int    cs_top = 0;
    call_stack[cs_top++] = (Frame){start, 0};

    while (cs_top > 0) {
        Frame *f = &call_stack[cs_top - 1];
        int u = f->v;

        Vec *nbrs = &t->graph[u];
        if (f->idx < nbrs->size) {
            int w = nbrs->data[f->idx++];
            if (t->disc[w] == -1) {
                // Не посещён — "рекурсивный вызов"
                t->disc[w] = t->timer;
                t->low[w]  = t->timer;
                t->timer++;
                t->stack[t->stack_top++] = w;
                t->on_stack[w] = 1;
                call_stack[cs_top++] = (Frame){w, 0};
            } else if (t->on_stack[w]) {
                // Обратное ребро — обновляем low
                if (t->disc[w] < t->low[u])
                    t->low[u] = t->disc[w];
            }
        } else {
            // Все соседи обработаны
            cs_top--;
            if (cs_top > 0) {
                int parent = call_stack[cs_top - 1].v;
                if (t->low[u] < t->low[parent])
                    t->low[parent] = t->low[u];
            }
            // Если u — корень SCC
            if (t->low[u] == t->disc[u]) {
                while (1) {
                    int w = t->stack[--t->stack_top];
                    t->on_stack[w] = 0;
                    t->scc[w] = t->scc_count;
                    if (w == u) break;
                }
                t->scc_count++;
            }
        }
    }

    free(call_stack);
}

// Запускает Тарьяна для всех вершин, возвращает массив scc[]
static int *tarjan_run(int n, Vec *graph) {
    Tarjan *t = tarjan_new(n, graph);
    for (int v = 0; v < n; v++) {
        if (t->disc[v] == -1)
            tarjan_dfs(t, v);
    }
    int *scc = t->scc;
    t->scc = NULL; // передаём владение
    tarjan_free(t);
    return scc;
}

// ------ 2-SAT ------------------------------------------------
// Переменные: i → xi = 2i, ¬xi = 2i+1
static inline int var_pos(int i) { return 2 * i; }
static inline int var_neg(int i) { return 2 * i + 1; }
static inline int var_not(int v) { return v ^ 1; }

typedef struct {
    int  n;
    Vec *graph; // размер 2*n
} TwoSat;

static TwoSat *twosat_new(int n) {
    TwoSat *s = malloc(sizeof(TwoSat));
    s->n     = n;
    s->graph = malloc(2 * n * sizeof(Vec));
    for (int i = 0; i < 2 * n; i++)
        vec_init(&s->graph[i]);
    return s;
}

static void twosat_free(TwoSat *s) {
    for (int i = 0; i < 2 * s->n; i++)
        vec_free(&s->graph[i]);
    free(s->graph);
    free(s);
}

// Импликация: a → b (и контрпозиция ¬b → ¬a)
static void add_impl(TwoSat *s, int a, int b) {
    vec_push(&s->graph[a], b);
    vec_push(&s->graph[var_not(b)], var_not(a));
}

// DEP i j: xi → xj
static void add_dep(TwoSat *s, int i, int j) {
    add_impl(s, var_pos(i), var_pos(j));
}

// CONFLICT i j: xi → ¬xj  и  xj → ¬xi
static void add_conflict(TwoSat *s, int i, int j) {
    add_impl(s, var_pos(i), var_neg(j));
    add_impl(s, var_pos(j), var_neg(i));
}

// REQUIRE i: ¬xi → xi
static void add_require(TwoSat *s, int i) {
    add_impl(s, var_neg(i), var_pos(i));
}

// Возвращает malloc-массив bool или NULL если IMPOSSIBLE
static int *twosat_solve(TwoSat *s) {
    int n = s->n;
    int *scc = tarjan_run(2 * n, s->graph);

    // Проверяем: xi и ¬xi не должны быть в одной SCC
    for (int i = 0; i < n; i++) {
        if (scc[var_pos(i)] == scc[var_neg(i)]) {
            free(scc);
            return NULL;
        }
    }

    // xi = true ⟺ scc[xi] < scc[¬xi]
    // (Тарьян нумерует SCC в обратном топологическом порядке:
    //  scc с меньшим номером - ближе к стоку; ¬xi должен стоять
    //  раньше xi в топ. порядке, то есть иметь больший номер)
    int *result = malloc(n * sizeof(int));
    for (int i = 0; i < n; i++)
        result[i] = scc[var_pos(i)] < scc[var_neg(i)];

    free(scc);
    return result;
}

// ------ main ------------------------------------------------
int main(void) {
    int n, m;
    scanf("%d %d", &n, &m);

    TwoSat *sat = twosat_new(n);

    for (int q = 0; q < m; q++) {
        char kind[16];
        scanf("%s", kind);
        if (strcmp(kind, "DEP") == 0) {
            int a, b;
            scanf("%d %d", &a, &b);
            add_dep(sat, a - 1, b - 1);
        } else if (strcmp(kind, "CONFLICT") == 0) {
            int a, b;
            scanf("%d %d", &a, &b);
            add_conflict(sat, a - 1, b - 1);
        } else if (strcmp(kind, "REQUIRE") == 0) {
            int a;
            scanf("%d", &a);
            add_require(sat, a - 1);
        }
    }

    int *vals = twosat_solve(sat);
    if (vals == NULL) {
        printf("IMPOSSIBLE\n");
    } else {
        for (int i = 0; i < n; i++)
            printf("%d: %s\n", i + 1, vals[i] ? "ON" : "OFF");
        free(vals);
    }

    twosat_free(sat);
    return 0;
}
