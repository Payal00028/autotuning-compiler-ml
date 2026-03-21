import argparse
import csv
import math
import os
import re
import shutil
import statistics
import subprocess
import tempfile
import time
from collections import Counter
from typing import Dict, List, Optional, Tuple


CSV_COLUMNS = [
    "lines",
    "chars",
    "functions",
    "loops",
    "conditionals",
    "recursion",
    "arrays",
    "pointers",
    "structs",
    "globals",
    "function_calls",
    "complexity",
    "nesting",
    "malloc_usage",
    "stdio_usage",
    "comments",
    "blank_lines",
    "O0_time",
    "O1_time",
    "O2_time",
    "O3_time",
    "best_flag",
]

FLAGS = ["-O0", "-O1", "-O2", "-O3"]
RUNS_PER_FLAG = 7
WARMUP_RUNS = 1
MIN_STABLE_TIME = 0.0005
TIMEOUT_SECONDS = 2.5
FAST_REPEAT_FACTOR = 500
MAX_CV = 0.5
IMPROVEMENT_THRESHOLD = 0.01

INPUT_PATTERNS = [
    r"\bscanf\s*\(",
    r"\bfscanf\s*\(",
    r"\bsscanf\s*\(",
    r"\bfgets\s*\(",
    r"\bgets\s*\(",
    r"\bgetchar\s*\(",
    r"\bread\s*\(",
]

KEYWORD_EXCLUSION = {
    "if",
    "for",
    "while",
    "switch",
    "return",
    "sizeof",
    "else",
    "case",
    "do",
}


def remove_comments_preserve_layout(code: str) -> str:
    code = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), code, flags=re.S)
    code = re.sub(r"//.*?$", "", code, flags=re.M)
    return code


def compute_nesting_depth(clean_code: str) -> int:
    depth = 0
    max_depth = 0
    for ch in clean_code:
        if ch == "{":
            depth += 1
            max_depth = max(max_depth, depth)
        elif ch == "}":
            depth = max(0, depth - 1)
    return max_depth


def extract_function_blocks(clean_code: str) -> List[Tuple[str, str]]:
    header_pattern = re.compile(
        r"^\s*(?:[A-Za-z_]\w*[\s\*]+)+([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{",
        flags=re.M,
    )
    blocks: List[Tuple[str, str]] = []
    for match in header_pattern.finditer(clean_code):
        name = match.group(1)
        if name in {"if", "for", "while", "switch"}:
            continue
        body_start = match.end()
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


def extract_function_names(clean_code: str) -> List[str]:
    return [name for name, _ in extract_function_blocks(clean_code)]


def detect_recursion(clean_code: str) -> int:
    try:
        blocks = extract_function_blocks(clean_code)
        if not blocks:
            return 0
        for fn_name, fn_body in blocks:
            if re.search(rf"\b{re.escape(fn_name)}\s*\(", fn_body):
                return 1
        return 0
    except Exception:
        return 0


def approx_cyclomatic(clean_code: str) -> int:
    token_counts = [
        len(re.findall(r"\bif\b", clean_code)),
        len(re.findall(r"\bfor\b", clean_code)),
        len(re.findall(r"\bwhile\b", clean_code)),
        len(re.findall(r"\bcase\b", clean_code)),
        len(re.findall(r"\?", clean_code)),
        len(re.findall(r"&&|\|\|", clean_code)),
    ]
    return max(1, 1 + sum(token_counts))


def count_function_calls(clean_code: str) -> int:
    calls = re.findall(r"\b([A-Za-z_]\w*)\s*\(", clean_code)
    return sum(1 for call in calls if call not in KEYWORD_EXCLUSION)


def count_globals(clean_code: str) -> int:
    lines = clean_code.splitlines()
    depth = 0
    global_lines: List[str] = []
    for line in lines:
        if depth == 0:
            global_lines.append(line)
        depth += line.count("{") - line.count("}")
        depth = max(depth, 0)
    global_text = "\n".join(global_lines)
    pattern = re.compile(
        r"^\s*(?!#)(?:static\s+)?(?:const\s+)?(?:unsigned\s+|signed\s+)?(?:long\s+|short\s+)?"
        r"[A-Za-z_]\w*(?:\s+\*+|\s+)+[A-Za-z_]\w*(?:\s*=\s*[^;]+)?;",
        flags=re.M,
    )
    return len(pattern.findall(global_text))


def sanitize_feature(name: str, value: int) -> int:
    if value < 0:
        return 0
    if name in {"pointers", "arrays", "function_calls", "complexity"}:
        return min(value, 1_000_000)
    return value


def extract_features(file_path: str) -> Dict[str, int]:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()

    lines = raw.splitlines()
    clean_code = remove_comments_preserve_layout(raw)

    comment_block = 0
    for match in re.finditer(r"/\*.*?\*/", raw, flags=re.S):
        comment_block += max(1, match.group(0).count("\n") + 1)
    comment_inline = len(re.findall(r"//.*?$", raw, flags=re.M))
    comments = comment_block + comment_inline

    loops = (
        len(re.findall(r"\bfor\b", clean_code))
        + len(re.findall(r"\bwhile\b", clean_code))
        + len(re.findall(r"\bdo\b", clean_code))
    )
    conditionals = len(re.findall(r"\bif\b", clean_code)) + len(re.findall(r"\bswitch\b", clean_code))
    recursion = detect_recursion(clean_code)
    functions = len(extract_function_names(clean_code))

    features = {
        "lines": len(lines),
        "chars": len(raw),
        "functions": functions,
        "loops": loops,
        "conditionals": conditionals,
        "recursion": recursion,
        "arrays": len(re.findall(r"\[[^\]]*\]", clean_code)),
        "pointers": len(re.findall(r"\*", clean_code)),
        "structs": len(re.findall(r"\bstruct\b", clean_code)),
        "globals": count_globals(clean_code),
        "function_calls": count_function_calls(clean_code),
        "complexity": approx_cyclomatic(clean_code),
        "nesting": compute_nesting_depth(clean_code),
        "malloc_usage": int(bool(re.search(r"\b(?:malloc|calloc|realloc|free)\s*\(", clean_code))),
        "stdio_usage": int(bool(re.search(r"#\s*include\s*<stdio\.h>", raw))),
        "comments": comments,
        "blank_lines": sum(1 for line in lines if not line.strip()),
    }
    for key in list(features.keys()):
        features[key] = sanitize_feature(key, int(features[key]))
    return features


def detect_input_need(file_content: str) -> bool:
    return any(re.search(pattern, file_content) for pattern in INPUT_PATTERNS)


def parse_scanf_formats(file_content: str) -> List[str]:
    result: List[str] = []
    for match in re.finditer(r"\bscanf\s*\(\s*\"((?:\\.|[^\"])*)\"", file_content):
        result.append(match.group(1))
    return result


def generate_input(file_content: str) -> List[Tuple[str, str]]:
    if not detect_input_need(file_content):
        return [("no_input_needed", "")]

    formats = parse_scanf_formats(file_content)
    if formats:
        text = " ".join(formats)
        ints = len(re.findall(r"%[0-9\.\-\+\*]*[diuoxX]", text))
        floats = len(re.findall(r"%[0-9\.\-\+\*]*[fFeEgGaA]", text))
        strings = len(re.findall(r"%[0-9\.\-\+\*]*s", text))
        chars = len(re.findall(r"%[0-9\.\-\+\*]*c", text))
        tokens: List[str] = (["10"] * ints) + (["3.14"] * floats) + (["hello"] * strings) + (["a"] * chars)
        if tokens:
            return [
                ("scanf_inferred", " ".join(tokens) + "\n"),
                ("generic_numbers", "10 20 30\n"),
                ("multiline_numbers", "5\n10 20 30 40 50\n"),
            ]

    if re.search(r"\bfgets\s*\(", file_content) or re.search(r"\bgets\s*\(", file_content):
        return [
            ("string_lines", "hello\nworld\n"),
            ("mixed_lines", "5\n10 20 30 40 50\n"),
            ("single_word", "hello\n"),
        ]

    return [
        ("generic_numbers", "10 20 30\n"),
        ("multiline_numbers", "5\n10 20 30 40 50\n"),
        ("strings_lines", "hello\nworld\n"),
    ]


def compile_program(c_file: str, flag: str, exe_path: str, cc: str) -> Tuple[bool, str]:
    cmd = [cc, c_file, flag, "-o", exe_path]
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=25,
        )
    except subprocess.TimeoutExpired:
        return False, "compile timeout"
    if proc.returncode != 0:
        return False, proc.stderr.strip() or proc.stdout.strip() or "compile failed"
    return True, ""


def run_once(exe_path: str, input_data: str, timeout_s: float) -> Tuple[bool, float, str]:
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            [exe_path],
            input=input_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout_s,
        )
        elapsed = time.perf_counter() - start
        if proc.returncode != 0:
            return False, elapsed, proc.stderr.strip() or proc.stdout.strip() or "runtime error"
        return True, elapsed, ""
    except subprocess.TimeoutExpired:
        return False, time.perf_counter() - start, "timeout"
    except Exception as exc:
        return False, time.perf_counter() - start, str(exc)


def run_multiple_times(
    exe_path: str,
    input_data: str,
    runs: int = RUNS_PER_FLAG,
    warmup_runs: int = WARMUP_RUNS,
    timeout_s: float = TIMEOUT_SECONDS,
) -> Tuple[bool, List[float], str]:
    total_runs = runs + warmup_runs
    measurements: List[float] = []
    for idx in range(total_runs):
        ok, elapsed, err = run_once(exe_path, input_data, timeout_s)
        if not ok:
            return False, [], err
        if idx >= warmup_runs:
            measurements.append(elapsed)
    return True, measurements, ""


def run_repeated_batch(exe_path: str, input_data: str, repeat_factor: int, timeout_s: float) -> Tuple[bool, float, str]:
    start = time.perf_counter()
    for _ in range(repeat_factor):
        ok, _, err = run_once(exe_path, input_data, timeout_s)
        if not ok:
            return False, 0.0, err
    total = time.perf_counter() - start
    return True, total / float(repeat_factor), ""


def detect_outliers(times: List[float]) -> List[float]:
    if len(times) <= 4:
        return times[:]
    ordered = sorted(times)
    trimmed = ordered[1:-1]
    if len(trimmed) < 3:
        return trimmed
    median = statistics.median(trimmed)
    mad = statistics.median([abs(x - median) for x in trimmed]) or 1e-12
    filtered = [x for x in trimmed if abs(x - median) / mad <= 6.0]
    return filtered if len(filtered) >= 3 else trimmed


def compute_stable_time(times: List[float]) -> Tuple[bool, float, float, float]:
    if len(times) < 3:
        return False, 0.0, 0.0, 0.0
    cleaned = detect_outliers(times)
    if len(cleaned) < 3:
        return False, 0.0, 0.0, 0.0

    mean_t = statistics.mean(cleaned)
    median_t = statistics.median(cleaned)
    stdev_t = statistics.pstdev(cleaned)
    cv = stdev_t / mean_t if mean_t > 0 else float("inf")

    if not math.isfinite(cv) or cv > MAX_CV:
        return False, mean_t, median_t, cv
    stable = 0.5 * mean_t + 0.5 * median_t
    return True, stable, median_t, cv


def determine_best_flag(flag_times: Dict[str, float], threshold: float = IMPROVEMENT_THRESHOLD) -> str:
    ordered = sorted(flag_times.items(), key=lambda kv: kv[1])
    if len(ordered) < 2:
        return "uncertain"
    best_flag, best_time = ordered[0]
    _, second_time = ordered[1]
    if best_time <= 0 or second_time <= 0:
        return "uncertain"
    improvement = (second_time - best_time) / second_time
    if improvement < threshold:
        return "uncertain"
    return best_flag.replace("-", "")


def measure_flag_time(
    exe_path: str,
    inputs: List[Tuple[str, str]],
) -> Tuple[bool, float, str, int, str]:
    last_error = "unknown error"
    for retry_idx, (strategy, input_data) in enumerate(inputs):
        ok, times, err = run_multiple_times(exe_path, input_data)
        if not ok:
            last_error = err
            continue

        stable_ok, stable_time, _, _ = compute_stable_time(times)
        if not stable_ok:
            last_error = "unstable_variance"
            continue

        if stable_time < MIN_STABLE_TIME:
            batch_ok, batch_time, batch_err = run_repeated_batch(
                exe_path=exe_path,
                input_data=input_data,
                repeat_factor=FAST_REPEAT_FACTOR,
                timeout_s=TIMEOUT_SECONDS,
            )
            if not batch_ok:
                last_error = batch_err
                continue
            stable_time = batch_time
            if stable_time < MIN_STABLE_TIME:
                last_error = "too_fast_after_repeat"
                continue
        return True, stable_time, strategy, retry_idx, ""
    return False, 0.0, "failed_all_strategies", max(0, len(inputs) - 1), last_error


def find_program_dir(base_dir: str) -> str:
    preferred = os.path.join(base_dir, "programs")
    fallback = os.path.join(base_dir, "Dataset")
    if os.path.isdir(preferred):
        return preferred
    if os.path.isdir(fallback):
        return fallback
    return preferred


def build_dataset(program_dir: str, output_csv: str, failed_log: str, cc: str) -> None:
    c_files = [
        os.path.join(program_dir, name)
        for name in os.listdir(program_dir)
        if name.lower().endswith(".c") and os.path.isfile(os.path.join(program_dir, name))
    ]
    c_files.sort()
    if not c_files:
        print(f"[ERROR] No .c files found in: {program_dir}")
        return

    stats = {
        "total": len(c_files),
        "success": 0,
        "skip_failed": 0,
        "skip_fast": 0,
        "skip_unstable": 0,
        "skip_uncertain": 0,
    }
    label_dist: Counter[str] = Counter()

    with open(output_csv, "w", newline="", encoding="utf-8") as out_csv, open(
        failed_log, "w", encoding="utf-8"
    ) as out_fail:
        writer = csv.DictWriter(out_csv, fieldnames=CSV_COLUMNS)
        writer.writeheader()

        for idx, c_file in enumerate(c_files, start=1):
            name = os.path.basename(c_file)
            print(f"[{idx}/{len(c_files)}] Processing: {name}")
            try:
                with open(c_file, "r", encoding="utf-8", errors="ignore") as src:
                    file_content = src.read()
                features = extract_features(c_file)
                input_candidates = generate_input(file_content)
                flag_times: Dict[str, float] = {}
                flag_retry: Dict[str, int] = {}
                flag_strategy: Dict[str, str] = {}

                skip_reason = ""
                with tempfile.TemporaryDirectory(prefix="auto_tune_") as temp_dir:
                    for flag in FLAGS:
                        exe_name = f"{os.path.splitext(name)[0]}_{flag.replace('-', '')}.exe"
                        exe_path = os.path.join(temp_dir, exe_name)

                        ok_compile, compile_err = compile_program(c_file, flag, exe_path, cc)
                        if not ok_compile:
                            skip_reason = f"compile_fail:{flag}:{compile_err}"
                            break

                        ok_time, stable_time, strategy, retries, run_err = measure_flag_time(exe_path, input_candidates)
                        if not ok_time:
                            skip_reason = f"run_fail:{flag}:{run_err}"
                            if run_err == "too_fast_after_repeat":
                                stats["skip_fast"] += 1
                            elif run_err == "unstable_variance":
                                stats["skip_unstable"] += 1
                            else:
                                stats["skip_failed"] += 1
                            break

                        flag_times[flag] = stable_time
                        flag_retry[flag] = retries
                        flag_strategy[flag] = strategy

                if skip_reason:
                    out_fail.write(f"{name} | {skip_reason}\n")
                    print(f"  -> skipped ({skip_reason})")
                    continue

                best_flag = determine_best_flag(flag_times, threshold=IMPROVEMENT_THRESHOLD)
                if best_flag == "uncertain":
                    stats["skip_uncertain"] += 1
                    out_fail.write(f"{name} | uncertain_best_flag | {flag_times}\n")
                    print("  -> skipped (uncertain_best_flag)")
                    continue

                row = {
                    "lines": features["lines"],
                    "chars": features["chars"],
                    "functions": features["functions"],
                    "loops": features["loops"],
                    "conditionals": features["conditionals"],
                    "recursion": features["recursion"],
                    "arrays": features["arrays"],
                    "pointers": features["pointers"],
                    "structs": features["structs"],
                    "globals": features["globals"],
                    "function_calls": features["function_calls"],
                    "complexity": features["complexity"],
                    "nesting": features["nesting"],
                    "malloc_usage": features["malloc_usage"],
                    "stdio_usage": features["stdio_usage"],
                    "comments": features["comments"],
                    "blank_lines": features["blank_lines"],
                    "O0_time": f"{flag_times['-O0']:.10f}",
                    "O1_time": f"{flag_times['-O1']:.10f}",
                    "O2_time": f"{flag_times['-O2']:.10f}",
                    "O3_time": f"{flag_times['-O3']:.10f}",
                    "best_flag": best_flag,
                }
                writer.writerow(row)
                stats["success"] += 1
                label_dist[best_flag] += 1

                retry_txt = ", ".join(f"{k}:{v}" for k, v in flag_retry.items())
                strategy_txt = ", ".join(f"{k}:{v}" for k, v in flag_strategy.items())
                print(f"  -> done | best={best_flag} | retries[{retry_txt}] | strategies[{strategy_txt}]")
            except Exception as exc:
                stats["skip_failed"] += 1
                out_fail.write(f"{name} | exception | {exc}\n")
                print("  -> skipped (exception)")

    print("\n[SUMMARY]")
    print(f"Total programs: {stats['total']}")
    print(f"Successfully processed: {stats['success']}")
    print(f"Skipped failed/crashed: {stats['skip_failed']}")
    print(f"Skipped too fast: {stats['skip_fast']}")
    print(f"Skipped unstable variance: {stats['skip_unstable']}")
    print(f"Skipped uncertain labels: {stats['skip_uncertain']}")
    print(f"Final dataset size: {stats['success']}")
    print("Best-flag distribution:")
    print(f"  O0: {label_dist.get('O0', 0)}")
    print(f"  O1: {label_dist.get('O1', 0)}")
    print(f"  O2: {label_dist.get('O2', 0)}")
    print(f"  O3: {label_dist.get('O3', 0)}")


def resolve_compiler() -> Optional[str]:
    for name in ["gcc", "clang", "cc"]:
        if shutil.which(name):
            return name
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate high-quality compiler auto-tuning dataset from C programs.")
    parser.add_argument("--program-dir", default=None, help="Directory containing .c files (default: programs/ then Dataset/).")
    parser.add_argument("--output", default="dataset.csv", help="Output dataset CSV path.")
    parser.add_argument("--failed-log", default="failed.log", help="Failure log path.")
    parser.add_argument("--cc", default=None, help="C compiler command (gcc/clang).")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    program_dir = os.path.abspath(args.program_dir) if args.program_dir else find_program_dir(base_dir)
    output_csv = os.path.abspath(args.output)
    failed_log = os.path.abspath(args.failed_log)
    compiler = args.cc or resolve_compiler()

    if not compiler:
        print("[ERROR] No compiler found in PATH. Install gcc/clang or pass --cc.")
        return
    if not os.path.isdir(program_dir):
        print(f"[ERROR] Program directory does not exist: {program_dir}")
        return

    print(f"[INFO] Program directory: {program_dir}")
    print(f"[INFO] Compiler: {compiler}")
    print(f"[INFO] Output CSV: {output_csv}")
    print(f"[INFO] Failure log: {failed_log}")
    build_dataset(program_dir, output_csv, failed_log, compiler)
    print("[INFO] Dataset generation finished.")


if __name__ == "__main__":
    main()
