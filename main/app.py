import os
import pickle
import re
import tempfile
from io import StringIO

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler


TARGET_COL = "best_flag"
MODEL_FILE = "model.pkl"
SCALER_FILE = "scaler.pkl"
META_FILE = "model_meta.pkl"


def remove_comments_preserve_layout(code: str) -> str:
    code = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), code, flags=re.S)
    code = re.sub(r"//.*?$", "", code, flags=re.M)
    return code


def extract_function_blocks(clean_code: str):
    header_pattern = re.compile(
        r"^\s*(?:[A-Za-z_]\w*[\s\*]+)+([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{",
        flags=re.M,
    )
    blocks = []
    for m in header_pattern.finditer(clean_code):
        name = m.group(1)
        if name in {"if", "for", "while", "switch"}:
            continue
        body_start = m.end()
        depth = 1
        i = body_start
        while i < len(clean_code) and depth > 0:
            ch = clean_code[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            i += 1
        if depth == 0:
            blocks.append((name, clean_code[body_start : i - 1]))
    return blocks


def detect_recursion(clean_code: str) -> int:
    for fn_name, fn_body in extract_function_blocks(clean_code):
        if re.search(rf"\b{re.escape(fn_name)}\s*\(", fn_body):
            return 1
    return 0


def count_globals(clean_code: str) -> int:
    lines = clean_code.splitlines()
    depth = 0
    global_lines = []
    for line in lines:
        if depth == 0:
            global_lines.append(line)
        depth += line.count("{") - line.count("}")
        depth = max(depth, 0)
    text = "\n".join(global_lines)
    pattern = re.compile(
        r"^\s*(?!#)(?:static\s+)?(?:const\s+)?(?:unsigned\s+|signed\s+)?(?:long\s+|short\s+)?"
        r"[A-Za-z_]\w*(?:\s+\*+|\s+)+[A-Za-z_]\w*(?:\s*=\s*[^;]+)?;",
        flags=re.M,
    )
    return len(pattern.findall(text))


def compute_nesting_depth(clean_code: str) -> int:
    depth = 0
    max_depth = 0
    for ch in clean_code:
        if ch == "{":
            depth += 1
            max_depth = max(max_depth, depth)
        elif ch == "}":
            depth = max(depth - 1, 0)
    return max_depth


def extract_features_from_c_text(raw: str) -> dict:
    lines = raw.splitlines()
    clean_code = remove_comments_preserve_layout(raw)
    comment_block = 0
    for m in re.finditer(r"/\*.*?\*/", raw, flags=re.S):
        comment_block += max(1, m.group(0).count("\n") + 1)
    comment_inline = len(re.findall(r"//.*?$", raw, flags=re.M))
    comments = comment_block + comment_inline

    loops = (
        len(re.findall(r"\bfor\b", clean_code))
        + len(re.findall(r"\bwhile\b", clean_code))
        + len(re.findall(r"\bdo\b", clean_code))
    )
    conditionals = len(re.findall(r"\bif\b", clean_code)) + len(re.findall(r"\bswitch\b", clean_code))
    complexity = (
        1
        + len(re.findall(r"\bif\b", clean_code))
        + len(re.findall(r"\bfor\b", clean_code))
        + len(re.findall(r"\bwhile\b", clean_code))
        + len(re.findall(r"\bcase\b", clean_code))
        + len(re.findall(r"\?", clean_code))
        + len(re.findall(r"&&|\|\|", clean_code))
    )
    function_calls = len(re.findall(r"\b([A-Za-z_]\w*)\s*\(", clean_code))

    return {
        "lines": len(lines),
        "chars": len(raw),
        "functions": len(extract_function_blocks(clean_code)),
        "loops": loops,
        "conditionals": conditionals,
        "recursion": detect_recursion(clean_code),
        "arrays": len(re.findall(r"\[[^\]]*\]", clean_code)),
        "pointers": len(re.findall(r"\*", clean_code)),
        "structs": len(re.findall(r"\bstruct\b", clean_code)),
        "globals": count_globals(clean_code),
        "function_calls": function_calls,
        "complexity": max(1, complexity),
        "nesting": compute_nesting_depth(clean_code),
        "malloc_usage": int(bool(re.search(r"\b(?:malloc|calloc|realloc|free)\s*\(", clean_code))),
        "stdio_usage": int(bool(re.search(r"#\s*include\s*<stdio\.h>", raw))),
        "comments": comments,
        "blank_lines": sum(1 for line in lines if not line.strip()),
        "O0_time": 0.0,
        "O1_time": 0.0,
        "O2_time": 0.0,
        "O3_time": 0.0,
    }


def load_dataset(csv_path: str) -> pd.DataFrame:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"dataset not found: {csv_path}")
    df = pd.read_csv(csv_path)
    if TARGET_COL not in df.columns:
        raise ValueError(f"'{TARGET_COL}' column missing in dataset")
    return df


def train_and_save(df: pd.DataFrame, save_dir: str = "."):
    feature_cols = [c for c in df.columns if c != TARGET_COL]
    x = df[feature_cols].copy()
    y = df[TARGET_COL].astype(str).copy()

    label_encoder = LabelEncoder()
    y_enc = label_encoder.fit_transform(y)

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y_enc,
        test_size=0.2,
        random_state=42,
        stratify=y_enc if len(set(y_enc)) > 1 else None,
    )

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    model = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(x_train_scaled, y_train)

    preds = model.predict(x_test_scaled)
    acc = accuracy_score(y_test, preds)
    cm = confusion_matrix(y_test, preds)
    report = classification_report(
        y_test,
        preds,
        target_names=label_encoder.classes_,
        zero_division=0,
        output_dict=False,
    )

    with open(os.path.join(save_dir, MODEL_FILE), "wb") as f:
        pickle.dump(model, f)
    with open(os.path.join(save_dir, SCALER_FILE), "wb") as f:
        pickle.dump(scaler, f)
    with open(os.path.join(save_dir, META_FILE), "wb") as f:
        pickle.dump({"feature_columns": feature_cols, "label_encoder": label_encoder}, f)

    return model, scaler, feature_cols, label_encoder, acc, cm, report


def load_artifacts(base_dir: str):
    model_path = os.path.join(base_dir, MODEL_FILE)
    scaler_path = os.path.join(base_dir, SCALER_FILE)
    meta_path = os.path.join(base_dir, META_FILE)
    if not (os.path.exists(model_path) and os.path.exists(scaler_path) and os.path.exists(meta_path)):
        return None

    with open(model_path, "rb") as f:
        model = pickle.load(f)
    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)
    with open(meta_path, "rb") as f:
        meta = pickle.load(f)
    return model, scaler, meta["feature_columns"], meta["label_encoder"]


def plot_target_distribution(df: pd.DataFrame):
    counts = df[TARGET_COL].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(counts.index.astype(str), counts.values)
    ax.set_title("Target Distribution")
    ax.set_xlabel("best_flag")
    ax.set_ylabel("count")
    st.pyplot(fig)


def plot_correlation_heatmap(df: pd.DataFrame):
    numeric_df = df.select_dtypes(include=["number"])
    corr = numeric_df.corr()
    fig, ax = plt.subplots(figsize=(10, 7))
    img = ax.imshow(corr.values, aspect="auto")
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=90, fontsize=8)
    ax.set_yticklabels(corr.columns, fontsize=8)
    ax.set_title("Feature Correlation Heatmap")
    fig.colorbar(img, ax=ax, fraction=0.046, pad=0.04)
    st.pyplot(fig)


def plot_histograms(df: pd.DataFrame):
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.5))
    for idx, col in enumerate(["loops", "lines", "functions"]):
        if col in df.columns:
            axes[idx].hist(df[col].dropna(), bins=20)
            axes[idx].set_title(f"{col} histogram")
            axes[idx].set_xlabel(col)
            axes[idx].set_ylabel("count")
    fig.tight_layout()
    st.pyplot(fig)


def plot_time_boxplots(df: pd.DataFrame):
    time_cols = [c for c in ["O0_time", "O1_time", "O2_time", "O3_time"] if c in df.columns]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.boxplot([df[c].dropna() for c in time_cols], labels=time_cols)
    ax.set_title("Execution Time Boxplots")
    ax.set_ylabel("time")
    st.pyplot(fig)


def c_upload_prediction(feature_columns, scaler, model, label_encoder):
    st.subheader("Upload C Program")
    st.caption("Upload a `.c` file to extract features and predict the recommended optimization flag.")
    uploaded = st.file_uploader("Upload .c file", type=["c"])
    if uploaded is None:
        return

    raw_text = uploaded.read().decode("utf-8", errors="ignore")
    feats = extract_features_from_c_text(raw_text)
    row = {}
    for col in feature_columns:
        row[col] = feats.get(col, 0.0)

    st.write("Extracted features:")
    st.dataframe(pd.DataFrame([row]))

    if st.button("Predict from Uploaded C File"):
        x_input = pd.DataFrame([row], columns=feature_columns)
        x_scaled = scaler.transform(x_input)
        pred = model.predict(x_scaled)[0]
        label = label_encoder.inverse_transform([pred])[0]
        st.success(f"Recommended Optimization Flag: -{label}")


def show_about_project():
    st.subheader("About Project")
    st.markdown(
        """
**Project Title:** Auto-Tuning Compiler  
**Team Name:** Avengers

**Team Members:**
- Payal Maleha
- Gaurav Singh
- Ritik Bhandari

**Motivation:**  
Manual optimization flag selection is hard and often inconsistent. This project uses machine learning to predict
the most suitable GCC optimization flag from static code features.

**Approach:**  
Generate a dataset from C programs, extract program features, benchmark optimization levels, train a classifier,
and serve predictions through an interactive Streamlit application.
"""
    )


def main():
    st.set_page_config(page_title="Auto-Tuning Compiler ML App", layout="wide")
    st.title("Auto-Tuning Compiler using Machine Learning")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_path = os.path.join(base_dir, "dataset.csv")

    try:
        df = load_dataset(dataset_path)
    except Exception as exc:
        st.error(str(exc))
        return

    model_bundle = load_artifacts(base_dir)
    trained_in_session = False

    if model_bundle is None:
        st.info("Model files not found. Training model now...")
        model, scaler, feature_columns, label_encoder, acc, cm, report = train_and_save(df, base_dir)
        trained_in_session = True
    else:
        model, scaler, feature_columns, label_encoder = model_bundle
        # Compute fresh metrics for display
        _, _, _, _, acc, cm, report = train_and_save(df, base_dir)

    section = st.sidebar.radio(
        "Navigate",
        ["EDA Dashboard", "Model Training", "Upload C Program", "About Project"],
    )

    if section == "EDA Dashboard":
        st.header("EDA Dashboard")
        st.subheader("Dataset Preview")
        st.dataframe(df.head(20))
        st.write(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")

        st.subheader("Missing Values")
        missing_df = pd.DataFrame({"column": df.columns, "missing_count": df.isna().sum().values})
        st.dataframe(missing_df)

        st.subheader("Target Distribution")
        plot_target_distribution(df)

        st.subheader("Feature Correlation Heatmap")
        plot_correlation_heatmap(df)

        st.subheader("Histograms (loops, lines, functions)")
        plot_histograms(df)

        st.subheader("Boxplots for Execution Times")
        plot_time_boxplots(df)

    elif section == "Model Training":
        st.header("Model Training")
        if trained_in_session:
            st.success("Model trained and saved in this session.")
        else:
            st.info("Using saved model files. Metrics shown are from current retraining.")

        st.write(f"Accuracy: {acc:.4f}")

        st.subheader("Confusion Matrix")
        fig, ax = plt.subplots(figsize=(5, 4))
        im = ax.imshow(cm, aspect="auto")
        ax.set_title("Confusion Matrix")
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        st.pyplot(fig)

        st.subheader("Classification Report")
        st.text(report)
        st.caption(f"Saved: {MODEL_FILE}, {SCALER_FILE}, {META_FILE}")

    elif section == "Upload C Program":
        c_upload_prediction(feature_columns, scaler, model, label_encoder)

    elif section == "About Project":
        show_about_project()


if __name__ == "__main__":
    main()
