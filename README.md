# Auto-Tuning Compiler Using Machine Learning

An end-to-end ML project that recommends the best GCC optimization flag (`-O0`, `-O1`, `-O2`, `-O3`) for C programs based on extracted static code features and measured runtime behavior.

## What This Project Does

- Builds a dataset from C source files by:
  - extracting structural/code features (loops, functions, conditionals, pointers, nesting, etc.)
  - benchmarking each program across optimization levels
  - labeling each sample with the best-performing flag
- Trains a classifier (Random Forest) to predict the best optimization flag.
- Serves predictions through a Streamlit app using:
  - manual feature input
  - direct `.c` file upload and automatic feature extraction

## Project Structure

- `Data_Creation/dataset_builder.py` - Generates labeled dataset from C programs.
- `Data_Creation/Dataset/` - Source C files used for dataset creation.
- `main/train_model.py` - Trains and saves model artifacts.
- `main/app.py` - Streamlit UI for EDA, training metrics, and predictions.
- `main/dataset.csv` - Training dataset (already generated in this repo).
- `main/model.pkl`, `main/scaler.pkl`, `main/model_meta.pkl` - Saved model artifacts.

## Requirements

- Python 3.10+ (recommended)
- `streamlit`
- `pandas`
- `scikit-learn`
- `matplotlib`
- For dataset generation: a C compiler in PATH (`gcc`, `clang`, or `cc`)

Install Python dependencies:

```bash
pip install streamlit pandas scikit-learn matplotlib
```

## Run the Streamlit App

From the `main` directory:

```bash
python -m streamlit run app.py
```

Then open the local URL shown by Streamlit (usually `http://localhost:8501`).

## Generate Dataset (Optional)

From the `Data_Creation` directory:

```bash
python dataset_builder.py
```

Useful options:

```bash
python dataset_builder.py --program-dir Dataset --output dataset.csv --failed-log failed.log --cc gcc
```

## Train Model (Optional)

From the `main` directory:

```bash
python train_model.py
```

This saves:
- `model.pkl`
- `scaler.pkl`
- `model_meta.pkl`

## Notes

- The app can auto-train if model files are missing.
- Prediction output is the recommended optimization flag label for GCC.
