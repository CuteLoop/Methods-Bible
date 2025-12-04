#!/usr/bin/env python3
"""
Initialize a LaTeX "Methods in Applied Mathematics" book project.

Creates folder structure and starter files:

    methods-book/
      main.tex
      figures/
      themes/
        complex_analysis.tex
        fourier_analysis.tex
        ode.tex
        pde.tex
      problems/
        exams/
          exam1/
            ex1_prob01.tex
      exams/
        exam1.tex
      Makefile
      .github/
        workflows/
          latex.yml
      plans/
        <slug>.json                 # section-level plans from OpenAI (phase 1)
      openai_examples_requests.jsonl
      openai_examples_results.jsonl

If --with-openai is passed, we do a 3-phase content pipeline:

  1) For each (chapter, section) in THEME_SPECS:
        - Call OpenAI Responses API with build_plan_json_prompt(...)
        - Store the resulting JSON plan in plans/<slug>.json
        - Each plan has 3–7 example descriptions.

  2) For ALL examples across ALL sections:
        - Build a JSONL file of Batch requests using
          build_example_triplet_prompt(...)
        - Submit batch to /v1/responses with model=gpt-5.1 (configurable).
        - Poll until completion and download results; if truncated, run up to
          two more continuation rounds with new Batches.

  3) Assemble LaTeX chapter files themes/*.tex:
        - For each chapter:
            \chapter{Title}
            \section{Section Title}
            % narrative from plan
            % and for each example:
            %   inquiry-based version
            %   full solution version
"""

import argparse
import json
import os
import re
import time
from pathlib import Path
from textwrap import dedent

from shared_prompts import (
    build_plan_json_prompt,
    build_example_triplet_prompt,
)

# -------------------------------
# Configuration of topics
# -------------------------------

THEME_SPECS = [
    {
        "filename": "complex_analysis.tex",
        "chapter_title": "Complex Analysis",
        "subsections": [
            "Complex Variables and Complex-valued Functions",
            "Analytic Functions and Integration along Contours",
            "Residue Calculus",
            "Extreme-, Stationary- and Saddle-Point Methods (*)",
        ],
    },
    {
        "filename": "fourier_analysis.tex",
        "chapter_title": "Fourier Analysis",
        "subsections": [
            "The Fourier Transform and Inverse Fourier Transform",
            "Properties of the 1-D Fourier Transform",
            "Dirac's delta-function",
            "Closed-form Representation for Select Fourier Transforms",
            "Fourier Series: Introduction",
            "Properties of the Fourier Series",
            "Riemann–Lebesgue Lemma",
            "Gibbs Phenomenon",
            "Laplace Transform",
            "From Differential to Algebraic Equations with FT, FS and LT",
        ],
    },
    {
        "filename": "ode.tex",
        "chapter_title": "Ordinary Differential Equations",
        "subsections": [
            "ODEs: Simple Cases",
            "Direct Methods for Solving Linear ODEs",
            "Linear Dynamics via the Green Function",
            "Linear Static Problems",
            "Sturm–Liouville (Spectral) Theory",
            "Phase Space Dynamics for Conservative and Perturbed Systems",
        ],
    },
    {
        "filename": "pde.tex",
        "chapter_title": "Partial Differential Equations",
        "subsections": [
            "First-Order PDE: Method of Characteristics",
            "Classification of Linear Second-Order PDEs",
            "Elliptic PDEs: Method of Green Function",
            "Waves in a Homogeneous Medium: Hyperbolic PDE (*)",
            "Diffusion Equation",
            "Boundary Value Problems: Fourier Method",
            "Case Study: Burgers' Equation (*)",
        ],
    },
]

# Default model; override with env var if you want.
MODEL_NAME = os.environ.get("METHODS_BOOK_MODEL", "gpt-5.1")

# How many rounds of batch continuation we allow (total rounds = 3 by default)
MAX_ROUNDS = 3


# -------------------------------
# OpenAI helpers (optional)
# -------------------------------

def get_openai_client():
    """Return an OpenAI client if OPENAI_API_KEY is set, otherwise None."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[INFO] OPENAI_API_KEY not set; skipping OpenAI content generation.")
        return None
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        print("[INFO] 'openai' package not installed; run `pip install openai`.")
        return None
    client = OpenAI()  # key picked from env
    return client


def extract_output_text(resp) -> str:
    """
    Extract text from a *direct* Responses API object (client.responses.create).

    The SDK returns Pydantic models; we first normalize using model_dump()
    to a plain dict, then walk resp["output"][...]["content"][...].
    """
    # Normalize to dict
    if isinstance(resp, dict):
        data = resp
    elif hasattr(resp, "model_dump"):
        data = resp.model_dump()
    else:
        # very defensive fallback
        data = getattr(resp, "__dict__", {})

    output_list = data.get("output", [])
    if not isinstance(output_list, list):
        return ""

    chunks: list[str] = []

    for msg in output_list:
        # msg is already a plain dict from model_dump()
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue
        for item in content:
            if item.get("type") != "output_text":
                continue
            text_obj = item.get("text")
            if isinstance(text_obj, dict):
                val = text_obj.get("value") or text_obj.get("content") or ""
                if val:
                    chunks.append(val)
            elif isinstance(text_obj, str):
                chunks.append(text_obj)

    return "\n".join(chunks).strip()


def response_to_text(resp) -> str:
    """
    Backward-compatible alias used elsewhere in the script.
    Works for direct Responses API calls.
    """
    return extract_output_text(resp)


def extract_output_text_from_response_obj(body: dict) -> str:
    """
    Extract plain text from a Responses API 'body' object as returned inside
    the Batch JSONL lines.

    body is already a plain dict coming from json.loads(line)["response"]["body"].
    We walk body["output"][...]["content"][...], concatenating "output_text".
    """
    output_list = body.get("output", [])
    if not isinstance(output_list, list):
        return ""

    chunks: list[str] = []

    for msg in output_list:
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue
        for item in content:
            if item.get("type") != "output_text":
                continue
            text_field = item.get("text")
            if isinstance(text_field, dict):
                val = (
                    text_field.get("value")
                    or text_field.get("content")
                    or ""
                )
            else:
                val = text_field if isinstance(text_field, str) else ""
            if val:
                chunks.append(val)

    return "\n".join(chunks).strip()


# -------------------------------
# Utility helpers
# -------------------------------

def write_if_missing(path: Path, content: str):
    """Write content to path if it does not already exist."""
    if path.exists():
        print(f"[SKIP] {path} (already exists)")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"[OK]   Created {path}")


def slugify(text: str) -> str:
    """Make a filesystem-friendly slug from a string."""
    s = text.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-") or "section"


def extract_block(full_text: str, start_marker: str, end_marker: str) -> str:
    """
    Return the substring of full_text between start_marker and end_marker.
    If not found, return "".
    """
    try:
        i = full_text.index(start_marker) + len(start_marker)
        j = full_text.index(end_marker, i)
        return full_text[i:j].strip()
    except ValueError:
        return ""


# -------------------------------
# PHASE 1: Section-level plans
# -------------------------------

def generate_section_plans(root: Path, client):
    """
    For each (chapter_title, section_title) in THEME_SPECS:

      - If a plan JSON already exists under plans/, load it.
      - Otherwise, call OpenAI once with build_plan_json_prompt(...) and save.

    Returns:
      plans_by_section: dict keyed by (chapter_title, section_title) -> plan_dict
    """
    plans_dir = root / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    plans_by_section: dict[tuple[str, str], dict] = {}

    for spec in THEME_SPECS:
        chapter_title = spec["chapter_title"]
        for section_title in spec["subsections"]:
            key = (chapter_title, section_title)
            slug = slugify(f"{chapter_title}-{section_title}")
            plan_path = plans_dir / f"{slug}.json"

            if plan_path.exists():
                print(f"[INFO] Using cached plan for section '{section_title}'")
                data = json.loads(plan_path.read_text(encoding="utf-8"))
                plans_by_section[key] = data
                continue

            if client is None:
                print(f"[WARN] No OpenAI client; cannot generate plan for '{section_title}'.")
                continue

            print(f"[INFO] Generating plan for section '{section_title}' ...")
            prompt = build_plan_json_prompt(chapter_title, section_title)
            resp = client.responses.create(
                model=MODEL_NAME,
                reasoning={"effort": "medium"},
                input=prompt,
                # Generous budget so plan JSON can include multiple examples with good detail
                max_output_tokens=4000,
            )
            text = response_to_text(resp)
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                print(f"[ERROR] Failed to parse JSON plan for section '{section_title}'.")
                print("Raw response (first 500 chars):")
                print(text[:500])
                continue

            plans_by_section[key] = data
            plan_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"[OK]   Saved plan to {plan_path}")

    return plans_by_section


# -------------------------------
# PHASE 2: Helper – parse one results file
# -------------------------------

def parse_round_results(
    results_path: Path,
    round_idx: int,
    combined_text_by_id: dict[str, str],
    example_state_by_id: dict[str, dict],
) -> list[str]:
    """
    Parse one round of Batch results from 'results_path'.

    - Appends new text segments to combined_text_by_id[custom_id].
    - Updates example_state_by_id[custom_id] with:
        {
          "completed": bool,
          "incomplete_reason": dict | None,
          "status_code": int,
        }
    - Returns a list of custom_ids that are STILL incomplete after this round.
    """
    incomplete_ids: list[str] = []

    print(f"[INFO] Parsing round {round_idx} results from {results_path} ...")

    with results_path.open("r", encoding="utf-8") as f:
        for line in f:
            raw_line = line.strip()
            if not raw_line:
                continue

            obj = json.loads(raw_line)
            custom_id = obj.get("custom_id")
            if not custom_id:
                continue

            resp = obj.get("response")
            err = obj.get("error")

            if not resp:
                print(f"[WARN] [round {round_idx}] No 'response' for {custom_id}; error={err}")
                example_state_by_id[custom_id] = {
                    "completed": False,
                    "incomplete_reason": {"reason": "no_response", "error": err},
                    "status_code": None,
                }
                incomplete_ids.append(custom_id)
                continue

            status_code = resp.get("status_code", 0)
            body = resp.get("body") or {}
            body_status = body.get("status")
            incomplete_details = body.get("incomplete_details")

            full_text_segment = extract_output_text_from_response_obj(body)

            print(
                f"[DEBUG] [round {round_idx}] ---- Parsing result for custom_id={custom_id} ----"
            )
            print(
                f"[DEBUG] [round {round_idx}] status_code={status_code}, "
                f"body.status={body_status}, incomplete_details={incomplete_details}"
            )
            print(
                f"[DEBUG] [round {round_idx}] full_text_segment (first 200 chars): "
                f"{full_text_segment[:200].replace('\n', ' ')}"
            )

            prev = combined_text_by_id.get(custom_id, "")
            if prev:
                combined = prev + "\n" + full_text_segment
            else:
                combined = full_text_segment
            combined = combined.strip()
            combined_text_by_id[custom_id] = combined

            # Check for markers in the combined text across all rounds so far.
            combined_text = combined

            has_inq_start = "%%% INQUIRY START %%%" in combined_text
            has_inq_end = "%%% INQUIRY END %%%" in combined_text
            has_sol_start = "%%% SOLUTION START %%%" in combined_text
            has_sol_end = "%%% SOLUTION END %%%" in combined_text

            print(
                f"[DEBUG] [round {round_idx}] markers in combined_text? "
                f"INQ_START={has_inq_start}, INQ_END={has_inq_end}, "
                f"SOL_START={has_sol_start}, SOL_END={has_sol_end}"
            )

            if has_inq_start and has_inq_end and has_sol_start and has_sol_end:
                # This example is now complete.
                example_state_by_id[custom_id] = {
                    "completed": True,
                    "incomplete_reason": None,
                    "status_code": status_code,
                }
            else:
                # Still incomplete (maybe hit max_output_tokens).
                example_state_by_id[custom_id] = {
                    "completed": False,
                    "incomplete_reason": incomplete_details
                    or {"reason": "markers_missing"},
                    "status_code": status_code,
                }
                incomplete_ids.append(custom_id)
                print(
                    f"[DEBUG] [round {round_idx}] Example {custom_id} still incomplete "
                    f"due to {incomplete_details}."
                )

    return incomplete_ids


# -------------------------------
# PHASE 2: Batch examples (inquiry + solution)
# -------------------------------

def run_example_batch(root: Path, client, plans_by_section: dict, max_rounds: int = MAX_ROUNDS):
    """
    Multi-round Batch pipeline.

    Round 1:
      - For each example in all section plans, build a /v1/responses request using
        build_example_triplet_prompt(...).
      - Submit as a Batch (or reuse existing results JSONL).
      - Parse results; some examples may be incomplete.

    Rounds 2..max_rounds:
      - For examples still incomplete, build "continuation" prompts that show the
        existing partial text and ask the model to continue the solution ONLY,
        without repeating, and to close with %%% SOLUTION END %%%.

    At the end:
      - For each example with both blocks complete, extract inquiry+solution.
    """
    # Helper: where to store requests/results for each round
    def round_paths(root_dir: Path, round_idx: int) -> tuple[Path, Path]:
        if round_idx == 1:
            req = root_dir / "openai_examples_requests.jsonl"
            res = root_dir / "openai_examples_results.jsonl"
        else:
            req = root_dir / f"openai_examples_requests_round{round_idx}.jsonl"
            res = root_dir / f"openai_examples_results_round{round_idx}.jsonl"
        return req, res

    # Build mapping from custom_id -> metadata
    spec_by_custom_id: dict[str, dict] = {}
    for spec in THEME_SPECS:
        chapter_title = spec["chapter_title"]
        for section_title in spec["subsections"]:
            key = (chapter_title, section_title)
            plan = plans_by_section.get(key)
            if not plan:
                print(f"[WARN] No plan for section '{section_title}', skipping examples.")
                continue
            examples = plan.get("examples", [])
            for idx, ex in enumerate(examples):
                ex_title = ex.get("title", f"Example {idx+1}")
                ex_summary = ex.get("summary", "")
                custom_id = f"example::{slugify(chapter_title)}::{slugify(section_title)}::{idx}"
                spec_by_custom_id[custom_id] = {
                    "chapter_title": chapter_title,
                    "section_title": section_title,
                    "ex_index": idx,
                    "ex_title": ex_title,
                    "ex_summary": ex_summary,
                }

    if not spec_by_custom_id:
        print("[INFO] No examples found in plans; skipping Batch example generation.")
        return {}

    # Accumulated state across rounds
    combined_text_by_id: dict[str, str] = {}
    example_state_by_id: dict[str, dict] = {}

    remaining_ids = list(spec_by_custom_id.keys())

    for round_idx in range(1, max_rounds + 1):
        if not remaining_ids:
            print(f"[INFO] All examples completed before round {round_idx}.")
            break

        print(
            f"[INFO] === Batch round {round_idx}: "
            f"{len(remaining_ids)} examples to run / parse ==="
        )

        requests_path, results_path = round_paths(root, round_idx)

        # Build requests JSONL for THIS round only
        with requests_path.open("w", encoding="utf-8") as f:
            for custom_id in remaining_ids:
                meta = spec_by_custom_id[custom_id]
                chapter_title = meta["chapter_title"]
                section_title = meta["section_title"]
                ex_title = meta["ex_title"]
                ex_summary = meta["ex_summary"]

                if round_idx == 1:
                    # Original full prompt for inquiry + solution
                    prompt = build_example_triplet_prompt(
                        chapter_title=chapter_title,
                        section_title=section_title,
                        example_title=ex_title,
                        example_summary=ex_summary,
                    )
                else:
                    # CONTINUATION PROMPT: we already have some partial text
                    existing_text = combined_text_by_id.get(custom_id, "").strip()
                    if not existing_text:
                        prompt = build_example_triplet_prompt(
                            chapter_title=chapter_title,
                            section_title=section_title,
                            example_title=ex_title,
                            example_summary=ex_summary,
                        )
                    else:
                        prompt = dedent(
                            f"""
                            You previously began generating a LaTeX problem with this marker protocol:

                            %%% INQUIRY START %%%
                            (inquiry-based LaTeX problem & hints)
                            %%% INQUIRY END %%%
                            %%% SOLUTION START %%%
                            (full worked solution)
                            %%% SOLUTION END %%%

                            The following is the content generated so far. It may already include the
                            entire INQUIRY block and the beginning of the SOLUTION block, but it was
                            cut off before the solution finished (or before the closing marker).

                            --- BEGIN EXISTING CONTENT ---
                            {existing_text}
                            --- END EXISTING CONTENT ---

                            Your task:
                            - Continue the LaTeX *from exactly where it was cut off*.
                            - Do NOT repeat any sentences already present.
                            - Do NOT regenerate the INQUIRY block if it is already present.
                            - Focus on FINISHING the solution so that the final combined text will
                              contain the closing marker:

                              %%% SOLUTION END %%%

                            Output ONLY the new LaTeX content that should be appended after the
                            existing text, nothing else.
                            """
                        ).strip()

                obj = {
                    "custom_id": custom_id,
                    "method": "POST",
                    "url": "/v1/responses",
                    "body": {
                        "model": MODEL_NAME,
                        "reasoning": {"effort": "medium"},
                        "input": prompt,
                        # Very generous budget to reduce truncation for long math solutions
                        "max_output_tokens": 8000,
                    },
                }
                f.write(json.dumps(obj) + "\n")

        if results_path.exists():
            print(f"[INFO] Found existing results for round {round_idx} at {results_path}; reusing them.")
        else:
            if client is None:
                print(
                    f"[ERROR] No OpenAI client and no existing results file for round {round_idx}."
                )
                break

            print(f"[INFO] Uploading batch input file for round {round_idx} to OpenAI...")
            batch_file = client.files.create(
                file=open(requests_path, "rb"),
                purpose="batch",
            )
            print(f"[INFO] [round {round_idx}] Uploaded file id: {batch_file.id}")

            print(f"[INFO] Creating batch job on /v1/responses for round {round_idx}...")
            batch_job = client.batches.create(
                input_file_id=batch_file.id,
                endpoint="/v1/responses",
                completion_window="24h",
            )
            batch_id = batch_job.id
            print(
                f"[INFO] [round {round_idx}] Batch job id: {batch_id} | status: {batch_job.status}"
            )

            while True:
                job = client.batches.retrieve(batch_id)
                status = job.status
                counts = getattr(job, "request_counts", None)
                if counts:
                    print(
                        f"[INFO] [round {round_idx}] Batch status: {status} "
                        f"({counts.completed}/{counts.total} requests completed)"
                    )
                else:
                    print(f"[INFO] [round {round_idx}] Batch status: {status}")

                if status == "completed":
                    break
                if status in {"failed", "cancelled", "expired"}:
                    print(
                        f"[ERROR] [round {round_idx}] Batch job did not complete successfully "
                        f"(status: {status})."
                    )
                    return {}

                time.sleep(10)

            output_file_id = job.output_file_id
            if not output_file_id:
                print(f"[ERROR] [round {round_idx}] No output_file_id for completed batch.")
                return {}

            print(
                f"[INFO] [round {round_idx}] Downloading batch results (file id: {output_file_id})..."
            )
            result_stream = client.files.content(output_file_id)
            with results_path.open("wb") as f:
                f.write(result_stream.read())
            print(f"[INFO] [round {round_idx}] Results saved to {results_path}")

        remaining_ids = parse_round_results(
            results_path,
            round_idx,
            combined_text_by_id,
            example_state_by_id,
        )

        if not remaining_ids:
            print(f"[INFO] All examples completed after round {round_idx}.")
            break
        else:
            print(
                f"[INFO] After round {round_idx}, {len(remaining_ids)} examples "
                f"are still incomplete; will attempt continuation."
            )

    # Build final example_outputs
    example_outputs: dict[tuple[str, str, int], dict] = {}

    for custom_id, meta in spec_by_custom_id.items():
        combined = combined_text_by_id.get(custom_id, "").strip()
        if not combined:
            print(f"[WARN] No text at all for {custom_id}; skipping.")
            continue

        state = example_state_by_id.get(custom_id, {})
        completed = state.get("completed", False)
        if not completed:
            print(
                f"[WARN] Example {custom_id} is still incomplete after {max_rounds} rounds "
                f"(reason={state.get('incomplete_reason')}); using whatever text we have."
            )

        inquiry_block = extract_block(
            combined,
            "%%% INQUIRY START %%%",
            "%%% INQUIRY END %%%",
        )
        solution_block = extract_block(
            combined,
            "%%% SOLUTION START %%%",
            "%%% SOLUTION END %%%",
        )

        if not inquiry_block and "%%% INQUIRY START %%%" in combined:
            print(f"[WARN] Could not neatly extract INQUIRY for {custom_id}.")
        if not solution_block and "%%% SOLUTION START %%%" in combined:
            print(f"[WARN] Could not neatly extract SOLUTION for {custom_id}.")

        key = (meta["chapter_title"], meta["section_title"], meta["ex_index"])
        example_outputs[key] = {
            "title": meta["ex_title"],
            "inquiry": inquiry_block,
            "solution": solution_block if solution_block else combined,
        }

    return example_outputs


# -------------------------------
# PHASE 3: Assemble themed LaTeX files
# -------------------------------

def generate_themes_with_openai(root: Path, use_openai: bool):
    """
    Create themes/*.tex.

    If use_openai=False: create simple stubs with TODO comments.

    If use_openai=True:
      - Phase 1: section plans
      - Phase 2: example batch
      - Phase 3: assemble chapters with sections + narrative + examples.
    """
    themes_dir = root / "themes"
    themes_dir.mkdir(parents=True, exist_ok=True)

    if not use_openai:
        print("[INFO] OpenAI disabled; writing simple stub chapters.")
        for spec in THEME_SPECS:
            path = themes_dir / spec["filename"]
            if path.exists():
                print(f"[INFO] Overwriting stub chapter {path} with fresh stub content.")
            lines = [f"\\chapter{{{spec['chapter_title']}}}\n\n"]
            for title in spec["subsections"]:
                lines.append(f"\\section{{{title}}}\n")
                lines.append(
                    "% TODO (Madeline + Joel): use prompts_for_sections.py "
                    "and shared_prompts.py to design a plan, inquiry-based "
                    "examples, and full solutions for this topic.\n\n"
                )
            path.write_text("".join(lines), encoding="utf-8")
            print(f"[OK]   Wrote {path}")
        return

    client = get_openai_client()
    if client is None:
        print("[INFO] No OpenAI client; falling back to stub chapters.")
        return generate_themes_with_openai(root, use_openai=False)

    print("[INFO] === Phase 1: generating / loading section plans ===")
    plans_by_section = generate_section_plans(root, client)

    print("[INFO] === Phase 2: Batch examples (inquiry + solution) ===")
    example_outputs = run_example_batch(root, client, plans_by_section)

    print("[INFO] === Phase 3: assembling LaTeX themed chapters ===")
    for spec in THEME_SPECS:
        chapter_title = spec["chapter_title"]
        chapter_filename = spec["filename"]
        path = themes_dir / chapter_filename

        if path.exists():
            print(f"[INFO] Overwriting chapter file {path} with generated content.")

        lines: list[str] = [f"\\chapter{{{chapter_title}}}\n\n"]

        for section_title in spec["subsections"]:
            lines.append(f"\\section{{{section_title}}}\n")

            plan = plans_by_section.get((chapter_title, section_title))
            if plan:
                narrative = plan.get("narrative", "").strip()
                if narrative:
                    lines.append("% --- Narrative plan (auto-generated) ---\n")
                    for ln in narrative.splitlines():
                        if ln.strip():
                            lines.append(f"% {ln}\n")
                        else:
                            lines.append("%\n")
                    lines.append("\n")
            else:
                lines.append("% TODO: Add narrative / plan for this section.\n\n")

            if plan and plan.get("examples"):
                examples = plan["examples"]
                for idx, ex in enumerate(examples):
                    ex_rec = example_outputs.get((chapter_title, section_title, idx))
                    if not ex_rec:
                        lines.append(
                            f"% TODO: No generated content yet for example {idx+1} "
                            f"('{ex.get('title','Example')}').\n\n"
                        )
                        continue

                    title = ex_rec["title"]
                    inquiry_block = ex_rec["inquiry"].strip()
                    solution_block = ex_rec["solution"].strip()

                    if inquiry_block:
                        lines.append(
                            f"% ===== Example {idx+1}: {title} (inquiry-based) =====\n"
                        )
                        lines.append(inquiry_block + "\n\n")

                    lines.append(
                        f"% ===== Example {idx+1}: {title} (full solution) =====\n"
                    )
                    lines.append(solution_block + "\n\n")
            else:
                lines.append(
                    "% TODO: Use prompts_for_sections.py to design examples and "
                    "add them here.\n\n"
                )

        path.write_text("".join(lines), encoding="utf-8")
        print(f"[OK]   Wrote {path}")


# -------------------------------
# Other project scaffolding
# -------------------------------

def generate_main_tex(root: Path):
    """Create main.tex with your book skeleton and includes for the themes."""
    main_tex = dedent(
        r"""
        %========================================
        %  Classical Math Textbook Template
        %========================================
        \documentclass[12pt,oneside]{book}

        %----------------------------------------
        % Encoding, language, fonts
        %----------------------------------------
        \usepackage[utf8]{inputenc}
        \usepackage[T1]{fontenc}
        \usepackage[english]{babel}
        \usepackage{lmodern}
        \usepackage{microtype}

        %----------------------------------------
        % Page layout
        %----------------------------------------
        \usepackage{geometry}
        \geometry{
          a4paper,
          margin=1in
        }

        \usepackage{setspace}
        \onehalfspacing

        %----------------------------------------
        % Math packages
        %----------------------------------------
        \usepackage{amsmath,amssymb,amsthm}
        \usepackage{mathtools}

        \numberwithin{equation}{chapter}

        % Common shortcuts
        \newcommand{\R}{\mathbb{R}}
        \newcommand{\C}{\mathbb{C}}
        \newcommand{\N}{\mathbb{N}}
        \newcommand{\Z}{\mathbb{Z}}
        \newcommand{\dd}{\,\mathrm{d}}
        \newcommand{\e}{\mathrm{e}}
        \newcommand{\ii}{\mathrm{i}}

        %----------------------------------------
        % Theorem-like environments
        %----------------------------------------
        \theoremstyle{plain}
        \newtheorem{theorem}{Theorem}[chapter]
        \newtheorem{lemma}[theorem]{Lemma}
        \newtheorem{proposition}[theorem]{Proposition}
        \newtheorem{corollary}[theorem]{Corollary}

        \theoremstyle{definition}
        \newtheorem{definition}[theorem]{Definition}
        \newtheorem{example}[theorem]{Example}

        \theoremstyle{remark}
        \newtheorem{remark}[theorem]{Remark}

        % Problems embedded in the text (worked examples)
        \theoremstyle{definition}
        \newtheorem{problem}{Problem}[chapter]

        % Exercises at the end of sections, numbered by section
        \newtheorem{exercise}{Exercise}[section]

        % Classical "Solution." environment
        \newenvironment{solution}{%
          \begin{proof}[Solution]%
        }{%
          \end{proof}%
        }

        %----------------------------------------
        % Graphics, lists, hyperlinks
        %----------------------------------------
        \usepackage{graphicx}
        \graphicspath{{figures/}}

        \usepackage{enumitem}
        \setlist{nosep}

        \usepackage[hidelinks]{hyperref}

        %----------------------------------------
        % Title info
        %----------------------------------------
        \title{%
          \Huge Methods in Applied Mathematics\\[0.5em]
          \Large A Personal Textbook and Problem Notebook
        }
        \author{Your Name}
        \date{\today}

        %========================================
        % Document
        %========================================
        \begin{document}

        \frontmatter
        \maketitle
        \tableofcontents

        \chapter*{Preface}

        This book is intended as both a classical textbook and a personal
        notebook for studying mathematical methods at the graduate level.
        It is organized in two complementary ways:

        \begin{itemize}
          \item \emph{By topic}, following the core course outline
                (complex analysis, Fourier analysis, differential equations).
          \item \emph{By exam and problem}, which you can develop later
                in separate chapters or appendices.
        \end{itemize}

        \mainmatter

        %========================================
        % Part I: Applied Analysis
        %========================================
        \part{Applied Analysis}

        \include{themes/complex_analysis}
        \include{themes/fourier_analysis}

        %========================================
        % Part II: Differential Equations
        %========================================
        \part{Differential Equations}

        \include{themes/ode}
        \include{themes/pde}

        %========================================
        % Back matter
        %========================================
        \backmatter

        \chapter*{Summary of Topics}

        Here you can keep a running list of topics, theorems, and page
        references for exam review, plus a mapping between exam problems
        and the thematic sections where they naturally belong.

        \end{document}
        """
    ).lstrip("\n")

    write_if_missing(root / "main.tex", main_tex)


def generate_basic_dirs(root: Path):
    """Create basic directory structure like figures/ and skeleton problem/exam dirs."""
    (root / "figures").mkdir(parents=True, exist_ok=True)
    (root / "problems" / "exams").mkdir(parents=True, exist_ok=True)
    (root / "exams").mkdir(parents=True, exist_ok=True)


def generate_mock_exam(root: Path):
    """
    Create a tiny mock Exam 1 and one problem, to illustrate the structure:

    problems/exams/exam1/ex1_prob01.tex
    exams/exam1.tex
    """
    prob_path = root / "problems" / "exams" / "exam1" / "ex1_prob01.tex"
    prob_content = dedent(
        r"""
        % problems/exams/exam1/ex1_prob01.tex
        \begin{problem}[Exam 1, Problem 1: Warm-up ODE]\label{prob:ex1-1-warmup-ode}
        Solve the initial value problem
        \[
          y'(t) = -2 y(t), \qquad y(0) = 1.
        \]
        \end{problem}

        \begin{solution}
        This is a linear first-order ODE with constant coefficients.
        We can solve by inspection or separation of variables.

        Separating variables,
        \[
          \frac{y'}{y} = -2
        \]
        and integrating gives
        \[
          \ln|y(t)| = -2t + C.
        \]
        Exponentiating,
        \[
          y(t) = C_1 e^{-2t}.
        \]
        Imposing the initial condition $y(0)=1$ yields $C_1 = 1$, so
        \[
          y(t) = e^{-2t}.
        \]
        \end{solution}
        """
    ).lstrip("\n")

    exam_chapter_path = root / "exams" / "exam1.tex"
    exam_chapter_content = dedent(
        r"""
        % exams/exam1.tex
        \chapter{Exam 1 – Sample Problems}

        \section*{Original Exam Statement}
        % TODO: paste or summarize the original exam statement here.

        \section{Solved Problems}
        % Each problem is stored canonically under problems/exams/exam1.
        \input{problems/exams/exam1/ex1_prob01}
        """
    ).lstrip("\n")

    write_if_missing(prob_path, prob_content)
    write_if_missing(exam_chapter_path, exam_chapter_content)


def generate_makefile(root: Path):
    """Create a simple Makefile for building main.pdf."""
    makefile_path = root / "Makefile"
    makefile_content = (
        "MAIN=main\n"
        "LATEX=pdflatex\n"
        "\n"
        ".PHONY: all pdf clean\n"
        "\n"
        "all: pdf\n"
        "\n"
        "pdf:\n"
        "\t$(LATEX) $(MAIN).tex\n"
        "\t$(LATEX) $(MAIN).tex\n"
        "\n"
        "clean:\n"
        "\trm -f $(MAIN).aux $(MAIN).log $(MAIN).out $(MAIN).toc \\\n"
        "\t       $(MAIN).bbl $(MAIN).blg $(MAIN).lof $(MAIN).lot\n"
    )

    write_if_missing(makefile_path, makefile_content)


def generate_github_actions(root: Path):
    """Create a minimal GitHub Actions workflow to build the LaTeX PDF."""
    workflow_dir = root / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    workflow_path = workflow_dir / "latex.yml"

    workflow_content = dedent(
        r"""
        name: Build LaTeX

        on:
          push:
            branches: [ main, master ]
          pull_request:

        jobs:
          build:
            runs-on: ubuntu-latest

            steps:
              - name: Checkout repository
                uses: actions/checkout@v4

              - name: Install TeX Live
                run: |
                  sudo apt-get update
                  sudo apt-get install -y \
                    texlive-latex-recommended \
                    texlive-latex-extra \
                    texlive-fonts-recommended

              - name: Build main.pdf
                run: |
                  pdflatex main.tex
                  pdflatex main.tex

              - name: Upload PDF artifact
                uses: actions/upload-artifact@v4
                with:
                  name: methods-book-pdf
                  path: main.pdf
        """
    ).lstrip("\n")

    write_if_missing(workflow_path, workflow_content)


# -------------------------------
# Main CLI
# -------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Initialize Methods-in-Applied-Math LaTeX book skeleton."
    )
    parser.add_argument(
        "--root",
        type=str,
        default="methods-book",
        help="Root directory for the project (default: methods-book)",
    )
    parser.add_argument(
        "--with-openai",
        action="store_true",
        help="Use OpenAI to plan sections and Batch API to generate examples.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Project root: {root}")

    generate_basic_dirs(root)
    generate_main_tex(root)
    generate_mock_exam(root)
    generate_makefile(root)
    generate_github_actions(root)
    generate_themes_with_openai(root, use_openai=args.with_openai)

    print("\n[DONE] Skeleton created.")
    print("Next steps:")
    print(f"  - cd {root} and run `make` or `pdflatex main.tex`.")
    print("  - Inspect `themes/` for generated chapters.")
    print("  - Use `plans/` JSON files and `prompts_for_sections.py` for further refinement.")


if __name__ == "__main__":
    main()
