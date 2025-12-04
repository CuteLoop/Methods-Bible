#!/usr/bin/env python3
import json
from pathlib import Path
import difflib
import subprocess
from textwrap import dedent

from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
REGIONS_FILE = LOG_DIR / "latex_problem_regions.jsonl"
PATCH_FILE = LOG_DIR / "latex_fixes.patch"

client = OpenAI()  # expects OPENAI_API_KEY in env

SYSTEM_PROMPT = """You are an expert LaTeX editor for a graduate-level applied mathematics textbook.

You receive a short excerpt from a .tex file, with line numbers.
Your tasks:

- Find and fix LaTeX syntax errors: missing $, unclosed environments, bad math delimiters,
  mismatched \\begin/\\end, stray braces, etc.
- Preserve the mathematical content and notation.
- Make MINIMAL local edits so the snippet would compile.
- Do NOT change labels \\label{...} or references \\eqref{...}.
- Do NOT reorder or delete large blocks of text unless necessary to fix LaTeX syntax.

Return ONLY the corrected snippet, without any line numbers, without commentary, so it can be pasted back into the file.
"""

def load_regions():
    regions = []
    with REGIONS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            regions.append(obj)
    return regions

def call_model(file_rel, region):
    numbered = region["snippet_numbered"]
    line = region["error_line"]

    user_prompt = dedent(f"""
    The following LaTeX snippet is from `{file_rel}` around line {line}.

    It has one or more LaTeX syntax errors (e.g. "Bad math environment delimiter", "Missing $ inserted", etc.).

    Here is the snippet WITH line numbers (do not include the numbers in your output):

    ```latex
    {numbered}
    ```

    Please return the corrected snippet ONLY, without line numbers and without commentary.
    """)

    resp = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    # Adapt to /v1/responses shape
    out = resp.output[0].content[0].text
    return out.strip("\n")

def make_patch_for_region(file_rel, region, fixed_snippet_text):
    tex_path = ROOT / file_rel
    all_lines = tex_path.read_text(encoding="utf-8").splitlines()

    start = region["start_line"]
    end = region["end_line"]

    old_block = all_lines[start-1:end]
    new_block = fixed_snippet_text.splitlines()

    patch_lines = list(
        difflib.unified_diff(
            old_block,
            new_block,
            fromfile=f"a/{file_rel}",
            tofile=f"b/{file_rel}",
            fromfiledate="",
            tofiledate="",
            lineterm="",
            n=3,
        )
    )

    # The unified_diff we created is relative; we need to add correct hunk header offsets.
    # Quick trick: let difflib build a full-file diff by splicing the block into the file.
    # But to keep it simple, we’ll compute a full-file diff instead of block-only.

    # Build "whole file" versions:
    new_all_lines = all_lines.copy()
    new_all_lines[start-1:end] = new_block

    full_patch = list(
        difflib.unified_diff(
            all_lines,
            new_all_lines,
            fromfile=f"a/{file_rel}",
            tofile=f"b/{file_rel}",
            lineterm="",
        )
    )
    return "\n".join(full_patch) + "\n"

def main():
    regions = load_regions()
    if not regions:
        print("[*] No regions found in logs/latex_problem_regions.jsonl")
        return

    all_patches = []

    for r in regions:
        file_rel = r["file"]
        print(f"[*] Fixing {file_rel} around line {r['error_line']}...")
        fixed = call_model(file_rel, r)
        patch = make_patch_for_region(file_rel, r, fixed)
        all_patches.append(patch)

    combined_patch = "\n".join(all_patches)
    PATCH_FILE.write_text(combined_patch, encoding="utf-8")
    print(f"[*] Combined patch written to {PATCH_FILE}")

    # Optional: automatically apply patch with git
    print("[*] Applying patch with git apply...")
    proc = subprocess.run(
        ["git", "apply", str(PATCH_FILE)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if proc.returncode != 0:
        print("[!] git apply failed:\n", proc.stdout)
    else:
        print("[*] git apply succeeded. Review with `git diff` and run `make` again.")

if __name__ == "__main__":
    main()
