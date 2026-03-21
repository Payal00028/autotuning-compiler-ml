#include <stdio.h>
#include <stdlib.h>

// 🌍 Global variable
int globalCounter = 0;

// 📦 Struct
struct Student {
    int id;
    char name[50];
};

// 🔁 Recursive function (factorial)
int factorial(int n) {
    if (n <= 1)
        return 1;
    return n * factorial(n - 1);
}

// 🔢 Function using array + pointer
void processArray(int *arr, int size) {
    printf("\nArray Elements:\n");
    for (int i = 0; i < size; i++) {
        printf("%d ", *(arr + i));  // pointer usage
    }
    printf("\n");
}

// 🧠 Function with conditionals + loops
void analyzeNumber(int num) {
    if (num % 2 == 0)
        printf("%d is Even\n", num);
    else
        printf("%d is Odd\n", num);

    // loop inside function
    printf("Counting to %d: ", num);
    for (int i = 1; i <= num; i++) {
        printf("%d ", i);
    }
    printf("\n");
}

// 🧩 Function using struct
void displayStudent(struct Student s) {
    printf("\nStudent Info:\n");
    printf("ID: %d\n", s.id);
    printf("Name: %s\n", s.name);
}

// 🔄 Function calls another function
void performOperations(int *arr, int size, int num) {
    processArray(arr, size);
    analyzeNumber(num);
    printf("Factorial of %d = %d\n", num, factorial(num));
}

int main() {

    // 📊 Array
    int arr[5] = {1, 2, 3, 4, 5};

    // 🧵 Pointer
    int *ptr = arr;

    // 📦 Struct variable
    struct Student s1;
    s1.id = 101;
    sprintf(s1.name, "Gaurav");

    // 🔁 Loop
    for (int i = 0; i < 3; i++) {
        globalCounter++;  // using global variable
    }

    printf("Global Counter: %d\n", globalCounter);

    // 📞 Function calls
    performOperations(ptr, 5, 5);

    displayStudent(s1);

    // 🔀 While loop
    int i = 0;
    printf("\nWhile Loop Output:\n");
    while (i < 3) {
        printf("i = %d\n", i);
        i++;
    }

    // 🔁 Do-while loop
    int j = 0;
    printf("\nDo-While Output:\n");
    do {
        printf("j = %d\n", j);
        j++;
    } while (j < 3);

    return 0;
}