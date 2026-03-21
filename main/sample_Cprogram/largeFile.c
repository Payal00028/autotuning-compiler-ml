#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SIZE 50000   // large dataset

// 🌍 Global variables
int operations = 0;

// 📦 Struct
typedef struct {
    int id;
    char name[50];
    float value;
} Record;

// 🔁 Recursive function (sum)
long long recursiveSum(int *arr, int n) {
    if (n <= 0) return 0;
    return arr[n - 1] + recursiveSum(arr, n - 1);
}

// 🔄 Comparator
int compare(const void *a, const void *b) {
    Record *r1 = (Record *)a;
    Record *r2 = (Record *)b;
    return r1->value - r2->value;
}

// 🧠 Hash Node
typedef struct Node {
    int key;
    Record data;
    struct Node *next;
} Node;

// 🔢 Hash function
int hash(int key) {
    return key % SIZE;
}

// 📥 Insert into hash
void insert(Node **table, Record r) {
    int idx = hash(r.id);
    Node *newNode = (Node *)malloc(sizeof(Node));
    newNode->key = r.id;
    newNode->data = r;
    newNode->next = table[idx];
    table[idx] = newNode;
}

// 🔍 Search in hash
Record *search(Node **table, int key) {
    int idx = hash(key);
    Node *temp = table[idx];

    while (temp) {
        if (temp->key == key)
            return &temp->data;
        temp = temp->next;
    }
    return NULL;
}

// 📊 Generate large dataset
void generateData(Record *arr, int n) {
    for (int i = 0; i < n; i++) {
        arr[i].id = i + 1;
        sprintf(arr[i].name, "Item_%d", i);
        arr[i].value = rand() % 10000;
    }
}

// 🔁 Process data
void processData(Record *arr, int n) {
    for (int i = 0; i < n; i++) {
        if (arr[i].value > 5000)
            arr[i].value *= 1.2;
        else
            arr[i].value *= 0.8;
        operations++;
    }
}

// 📁 File writing (simulate 150KB+ input)
void writeToFile(Record *arr, int n) {
    FILE *fp = fopen("large_data.txt", "w");

    for (int i = 0; i < n; i++) {
        fprintf(fp, "%d %s %.2f\n", arr[i].id, arr[i].name, arr[i].value);
    }

    fclose(fp);
}

// 📁 File reading
void readFromFile() {
    FILE *fp = fopen("large_data.txt", "r");
    char buffer[100];

    printf("\nReading sample from file:\n");

    for (int i = 0; i < 5 && fgets(buffer, sizeof(buffer), fp); i++) {
        printf("%s", buffer);
    }

    fclose(fp);
}

// 🚀 Main
int main() {

    // 📦 Dynamic allocation (large memory)
    Record *data = (Record *)malloc(SIZE * sizeof(Record));

    // 🧠 Hash table
    Node **table = (Node **)calloc(SIZE, sizeof(Node *));

    // 🔢 Generate large dataset
    generateData(data, SIZE);

    // 🔁 Process data
    processData(data, SIZE);

    // 🔄 Sort data
    qsort(data, SIZE, sizeof(Record), compare);

    // 📥 Insert into hash
    for (int i = 0; i < SIZE; i++) {
        insert(table, data[i]);
    }

    // 🔍 Search example
    int key = 25000;
    Record *found = search(table, key);

    if (found)
        printf("Found: %s -> %.2f\n", found->name, found->value);

    // 🔁 Recursion usage
    int sample[10];
    for (int i = 0; i < 10; i++) sample[i] = i;

    printf("Recursive Sum: %lld\n", recursiveSum(sample, 10));

    // 📁 File operations (large file)
    writeToFile(data, SIZE);
    readFromFile();

    printf("\nTotal operations: %d\n", operations);

    // 🧹 Free memory
    free(data);
    free(table);

    return 0;
}