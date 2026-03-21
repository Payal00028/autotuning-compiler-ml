import argparse
import os
import pickle

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler


TARGET_COL = "best_flag"


def load_dataset(csv_path: str) -> pd.DataFrame:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found: {csv_path}")
    df = pd.read_csv(csv_path)
    if TARGET_COL not in df.columns:
        raise ValueError(f"'{TARGET_COL}' column is missing in dataset")
    return df


def split_features_target(df: pd.DataFrame):
    feature_cols = [c for c in df.columns if c not in [TARGET_COL]]
    x = df[feature_cols].copy()
    y = df[TARGET_COL].astype(str).copy()
    return x, y, feature_cols


def train_pipeline(df: pd.DataFrame, random_state: int = 42):
    x, y, feature_cols = split_features_target(df)

    # Encode labels for classifier
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)

    # Split train/test
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y_encoded,
        test_size=0.2,
        random_state=random_state,
        stratify=y_encoded if len(set(y_encoded)) > 1 else None,
    )

    # Scale features
    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    # Train model
    model = RandomForestClassifier(
        n_estimators=300,
        random_state=random_state,
        class_weight="balanced",
    )
    model.fit(x_train_scaled, y_train)

    # Evaluate
    y_pred = model.predict(x_test_scaled)
    acc = accuracy_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(
        y_test,
        y_pred,
        target_names=label_encoder.classes_,
        zero_division=0,
    )

    artifacts = {
        "model": model,
        "scaler": scaler,
        "label_encoder": label_encoder,
        "feature_columns": feature_cols,
        "target_column": TARGET_COL,
    }
    metrics = {
        "accuracy": acc,
        "confusion_matrix": cm,
        "classification_report": report,
    }
    return artifacts, metrics


def save_artifacts(artifacts: dict, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)

    model_path = os.path.join(out_dir, "model.pkl")
    scaler_path = os.path.join(out_dir, "scaler.pkl")
    meta_path = os.path.join(out_dir, "model_meta.pkl")

    with open(model_path, "wb") as f:
        pickle.dump(artifacts["model"], f)

    with open(scaler_path, "wb") as f:
        pickle.dump(artifacts["scaler"], f)

    # Save label encoder and feature order for app prediction
    with open(meta_path, "wb") as f:
        pickle.dump(
            {
                "label_encoder": artifacts["label_encoder"],
                "feature_columns": artifacts["feature_columns"],
                "target_column": artifacts["target_column"],
            },
            f,
        )

    return model_path, scaler_path, meta_path


def main():
    parser = argparse.ArgumentParser(description="Train Auto-Tuning Compiler ML model.")
    parser.add_argument("--dataset", default="dataset.csv", help="Path to dataset CSV.")
    parser.add_argument("--out-dir", default=".", help="Directory to save model/scaler files.")
    args = parser.parse_args()

    df = load_dataset(args.dataset)
    artifacts, metrics = train_pipeline(df)
    model_path, scaler_path, meta_path = save_artifacts(artifacts, args.out_dir)

    print("Training finished")
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print("Confusion Matrix:")
    print(metrics["confusion_matrix"])
    print("Classification Report:")
    print(metrics["classification_report"])
    print(f"Saved model: {model_path}")
    print(f"Saved scaler: {scaler_path}")
    print(f"Saved metadata: {meta_path}")


if __name__ == "__main__":
    main()
