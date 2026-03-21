#include <stdio.h>
#include <string.h>

#define MAX_OPT 6

// Structure for optimization
typedef struct {
    char name[50];
    float score;
} Optimization;

// Function to sort optimizations based on score (descending)
void sortOptimizations(Optimization opt[], int n) {
    for(int i = 0; i < n - 1; i++) {
        for(int j = i + 1; j < n; j++) {
            if(opt[i].score < opt[j].score) {
                Optimization temp = opt[i];
                opt[i] = opt[j];
                opt[j] = temp;
            }
        }
    }
}

int main() {
    int loops, memoryAccess, branches;

    printf("Enter number of loops: ");
    scanf("%d", &loops);

    printf("Enter memory access intensity (1-10): ");
    scanf("%d", &memoryAccess);

    printf("Enter number of branches: ");
    scanf("%d", &branches);

    Optimization opt[MAX_OPT] = {
        {"Loop Unrolling", 0},
        {"Inline Expansion", 0},
        {"Constant Folding", 0},
        {"Dead Code Elimination", 0},
        {"Common Subexpression Elimination", 0},
        {"Loop Fusion", 0}
    };

    // Scoring logic (simple heuristic)
    opt[0].score = loops * 2;                          // Loop Unrolling
    opt[1].score = branches * 1.5;                     // Inline Expansion
    opt[2].score = 5;                                  // Constant Folding (always useful)
    opt[3].score = 4;                                  // Dead Code Elimination
    opt[4].score = memoryAccess * 1.8;                 // CSE
    opt[5].score = loops + memoryAccess;               // Loop Fusion

    // Sort optimizations
    sortOptimizations(opt, MAX_OPT);

    // Print top 3
    printf("\nTop 3 Recommended Optimizations:\n");
    for(int i = 0; i < 3; i++) {
        printf("%d. %s (Score: %.2f)\n", i + 1, opt[i].name, opt[i].score);
    }

    return 0;
}