// ============================================================
//  НАИВНОЕ РЕШЕНИЕ — полный перебор 2^N конфигураций
//  Сложность: O(2^N * M)
//  Работает только при N ≤ ~20
// ============================================================
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef enum {
    DEP,
    CONFLICT,
    REQUIRE
} ConstraintKind;

typedef struct {
    ConstraintKind kind;
    int a;
    int b; // unused for REQUIRE
} Constraint;

static int check(unsigned long long state, const Constraint *constraints, int m) {
    for (int i = 0; i < m; i++) {
        const Constraint *c = &constraints[i];
        int on_a = (state >> c->a) & 1;
        int on_b = (state >> c->b) & 1;
        switch (c->kind) {
            case DEP:
                // A → B: не может быть A=true, B=false
                if (on_a && !on_b) return 0;
                break;
            case CONFLICT:
                if (on_a && on_b) return 0;
                break;
            case REQUIRE:
                if (!on_a) return 0;
                break;
        }
    }
    return 1;
}

int main(void) {
    int n, m;
    scanf("%d %d", &n, &m);

    Constraint *constraints = (Constraint *)malloc(m * sizeof(Constraint));
    if (!constraints) return 1;

    for (int i = 0; i < m; i++) {
        char kind[16];
        scanf("%s", kind);
        if (strcmp(kind, "DEP") == 0) {
            int a, b;
            scanf("%d %d", &a, &b);
            constraints[i].kind = DEP;
            constraints[i].a = a - 1;
            constraints[i].b = b - 1;
        } else if (strcmp(kind, "CONFLICT") == 0) {
            int a, b;
            scanf("%d %d", &a, &b);
            constraints[i].kind = CONFLICT;
            constraints[i].a = a - 1;
            constraints[i].b = b - 1;
        } else if (strcmp(kind, "REQUIRE") == 0) {
            int a;
            scanf("%d", &a);
            constraints[i].kind = REQUIRE;
            constraints[i].a = a - 1;
            constraints[i].b = 0;
        } else {
            fprintf(stderr, "Unknown constraint: %s\n", kind);
            free(constraints);
            return 1;
        }
    }

    // Перебираем все 2^N конфигураций
    unsigned long long total = 1ULL << n;
    int found = 0;

    for (unsigned long long mask = 0; mask < total; mask++) {
        if (check(mask, constraints, m)) {
            for (int i = 0; i < n; i++) {
                int on = (mask >> i) & 1;
                printf("%d: %s\n", i + 1, on ? "ON" : "OFF");
            }
            found = 1;
            break;
        }
    }

    if (!found) {
        printf("IMPOSSIBLE\n");
    }

    free(constraints);
    return 0;
}
