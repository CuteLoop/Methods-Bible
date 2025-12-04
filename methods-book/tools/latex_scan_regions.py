#!/usr/bin/env python3
import subprocess
import re
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
MAIN_TEX = ROOT / "main.tex"

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "latex_errors.log"
REGIONS_FILE = LOG_DIR / "latex_problem_regions.jsonl"

# Errors we care about (you can add more)
ERROR_PATTERNS = [
    r"Missing \$ inserted\.",
    r"Bad math environment delimiter\.",
    r"\\begin\{aligned\} allowed only in math mode\.",
    r"Undefined control sequence\.",
]

ERROR_RE = re.compile("|".join(ERROR_PATTERNS))

def run_latex():
    print("[*] Running pdflatex...")
    proc = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", MAIN_TEX.name],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    LOG_FILE.write_text(proc.stdout, encoding="utf-8")
    print(f"[*] LaTeX log saved to {LOG_FILE}")
    return proc.stdout

def parse_errors(log_text):
    """
    Collect errors as small chunks:
    - error message line starting with '!'
    - the following line 'l.<num> <source>'
    - plus a bit of context above that so we can guess the file.
    """
    lines = log_text.splitlines()
    results = []

    for i, line in enumerate(lines):
        if line.startswith("!") and ERROR_RE.search(line):
            # scan forward for l.<num>
            for j in range(i + 1, min(i + 6, len(lines))):
                m = re.match(r"l\.(\d+)\s", lines[j])
                if m:
                    line_no = int(m.group(1))
                    # take 20 lines before error to find file name
                    context_start = max(0, i - 20)
                    context_chunk = "\n".join(lines[context_start:j+1])
                    results.append({"line": line_no, "context_chunk": context_chunk})
                    break
    return results

def guess_file(context_chunk):
    """
    Look for '(./themes/xxx.tex' or '(./exams/yyy.tex' in the context chunk.
    Use the last one found (closest to the error).
    """
    matches = re.findall(r"\((\./(?:themes|exams)/[^)]+\.tex)", context_chunk)
    if matches:
        return matches[-1][2:]  # strip "./"
    return "main.tex"  # fallback

def collect_regions(log_text, radius=10):
    base_errors = parse_errors(log_text)

    # Deduplicate by (file, line) so we don't request fixes twice
    seen = set()
    regions = []

    for err in base_errors:
        context_chunk = err["context_chunk"]
        file_rel = guess_file(context_chunk)
        key = (file_rel, err["line"])
        if key in seen:
            continue
        seen.add(key)

        tex_path = ROOT / file_rel
        if not tex_path.exists():
            print(f"[!] File {file_rel} not found, skipping error at line {err['line']}")
            continue

        lines = tex_path.read_text(encoding="utf-8").splitlines()
        center = err["line"]
        start = max(1, center - radius)
        end = min(len(lines), center + radius)

        raw_snippet = lines[start-1:end]  # 1-based to 0-based
        numbered_snippet = "\n".join(
            f"{i:5d}  {line}"
            for i, line in enumerate(lines[start-1:end], start=start)
        )

        regions.append(
            {
                "file": file_rel,
                "error_line": center,
                "start_line": start,
                "end_line": end,
                "snippet_raw": raw_snippet,
                "snippet_numbered": numbered_snippet,
            }
        )

    return regions

def main():
    log_text = run_latex()
    regions = collect_regions(log_text)

    with REGIONS_FILE.open("w", encoding="utf-8") as f:
        for r in regions:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[*] Found {len(regions)} problematic regions")
    print(f"[*] Saved to {REGIONS_FILE}")

if __name__ == "__main__":
    main()
