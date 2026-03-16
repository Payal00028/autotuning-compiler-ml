import pandas as pd
from sklearn.linear_model import LinearRegression
import joblib
import os

print("Training started...")
dataset_path = "data/dataset.csv"
if not os.path.exists(dataset_path):
    print("Dataset not found!")
    print("Waiting for data team to provide dataset.csv")
    exit()
df = pd.read_csv(dataset_path)
X = df[["code_size", "loop_count"]]
y = df["execution_time"]
model = LinearRegression()
model.fit(X, y)
joblib.dump(model, "ml/model.pkl")
print("Model trained and saved successfully!")