#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 🌍 Global variable
int operationCount = 0;

// 📦 Struct for product
typedef struct {
    int id;
    char name[50];
    float price;
} Product;

// 🔁 Recursive Binary Search
int binarySearch(Product arr[], int left, int right, int target) {
    if (left > right)
        return -1;

    int mid = (left + right) / 2;

    if (arr[mid].id == target)
        return mid;
    else if (arr[mid].id > target)
        return binarySearch(arr, left, mid - 1, target);
    else
        return binarySearch(arr, mid + 1, right, target);
}

// 🔄 Comparator for qsort
int comparePrice(const void *a, const void *b) {
    Product *p1 = (Product *)a;
    Product *p2 = (Product *)b;

    if (p1->price > p2->price) return 1;
    else if (p1->price < p2->price) return -1;
    return 0;
}

// 🧠 Hash Node
typedef struct HashNode {
    int key;
    Product value;
    struct HashNode *next;
} HashNode;

// 🔢 Hash Function
int hash(int key, int size) {
    return key % size;
}

// 📥 Insert into Hash Table
void insert(HashNode **table, int size, Product p) {
    int idx = hash(p.id, size);

    HashNode *newNode = (HashNode *)malloc(sizeof(HashNode));
    newNode->key = p.id;
    newNode->value = p;
    newNode->next = table[idx];

    table[idx] = newNode;
}

// 🔍 Search in Hash Table
Product *search(HashNode **table, int size, int key) {
    int idx = hash(key, size);

    HashNode *temp = table[idx];
    while (temp) {
        if (temp->key == key)
            return &temp->value;
        temp = temp->next;
    }
    return NULL;
}

// 📊 Display products
void displayProducts(Product arr[], int n) {
    printf("\nProduct List:\n");
    for (int i = 0; i < n; i++) {
        printf("ID: %d | Name: %s | Price: %.2f\n",
               arr[i].id, arr[i].name, arr[i].price);
    }
}

// 🔁 Function using pointers + loops
void updatePrices(Product *arr, int n) {
    for (int i = 0; i < n; i++) {
        arr[i].price *= 1.1; // increase 10%
        operationCount++;
    }
}

// 🚀 Main
int main() {

    int n = 5;

    // 📦 Array of struct
    Product products[5] = {
        {101, "Laptop", 50000},
        {102, "Phone", 20000},
        {103, "Tablet", 30000},
        {104, "Monitor", 15000},
        {105, "Keyboard", 2000}
    };

    // 🔁 Loop
    printf("Original Data:\n");
    displayProducts(products, n);

    // 🔄 Sorting
    qsort(products, n, sizeof(Product), comparePrice);
    printf("\nAfter Sorting by Price:\n");
    displayProducts(products, n);

    // 🔁 Update using pointer
    updatePrices(products, n);
    printf("\nAfter Price Update:\n");
    displayProducts(products, n);

    // 🔍 Recursion (Binary Search)
    int searchId = 103;
    int index = binarySearch(products, 0, n - 1, searchId);

    if (index != -1)
        printf("\nFound Product ID %d at index %d\n", searchId, index);
    else
        printf("\nProduct not found\n");

    // 🧠 Hash Table
    HashNode **table = (HashNode **)calloc(n, sizeof(HashNode *));

    for (int i = 0; i < n; i++) {
        insert(table, n, products[i]);
    }

    // 🔍 Hash search
    Product *p = search(table, n, 104);

    if (p)
        printf("\nHash Search Found: %s (%.2f)\n", p->name, p->price);
    else
        printf("\nNot found in hash table\n");

    printf("\nTotal Operations: %d\n", operationCount);

    return 0;
}