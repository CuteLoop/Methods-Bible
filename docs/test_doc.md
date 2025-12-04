Nice, we’re at the “lock this in so it never breaks again” stage 😎
Let’s treat `init_methods_book.py` like a tiny library and write a spec + test plan.

---

## 1. Document the features (spec)

Think of these as *user stories* / features that your tests will guard.

### 1.1 CLI + top-level behavior

* **F1 – CLI interface**

  * `python init_methods_book.py --root methods-book`
    creates (if missing) the basic LaTeX book skeleton.
  * `--with-openai` toggles whether the OpenAI pipeline runs for themes.

* **F2 – Idempotent scaffolding**

  * Running the script twice does **not** overwrite existing files except:

    * `themes/*.tex` when `--with-openai` is used (these are intentionally regenerated).
  * Existing main.tex / exams / Makefile / workflow are preserved.

---

### 1.2 Filesystem scaffolding (no OpenAI)

* **F3 – Directory structure**

  * Creates, under `root`:

    * `figures/`
    * `problems/exams/`
    * `exams/`
    * `.github/workflows/`
    * `themes/` (inside `generate_themes_with_openai`)

* **F4 – `main.tex` skeleton**

  * A classical book skeleton with:

    * `\documentclass[12pt,oneside]{book}`
    * theorem environments, `problem`, `exercise`, `solution`.
    * `\include{themes/complex_analysis}`, etc.

* **F5 – Mock exam**

  * Creates:

    * `problems/exams/exam1/ex1_prob01.tex` with a simple ODE problem + solution.
    * `exams/exam1.tex` that `\input`s that problem.

* **F6 – Makefile**

  * Creates a `Makefile` with:

    * `pdf` target that runs `pdflatex main.tex` twice.
    * `clean` target that removes common aux files.

* **F7 – GitHub Actions workflow**

  * `.github/workflows/latex.yml` that:

    * Installs TeX Live.
    * Builds `main.pdf`.
    * Uploads `main.pdf` as an artifact.

* **F8 – Themes without OpenAI**

  * If `use_openai=False` *or* no OPENAI client:

    * Creates `themes/complex_analysis.tex`, `themes/fourier_analysis.tex`, `themes/ode.tex`, `themes/pde.tex`.
    * Each file has a `\chapter{...}` and `\section{...}` per subsection.
    * Each section has a `% TODO ...` comment.

---

### 1.3 OpenAI: Section plans (Phase 1)

* **F9 – Plan caching**

  * Plans are stored under `plans/<slug>.json`, where slug is based on `chapter_title + section_title`.
  * If a plan file already exists, it is loaded and **no** OpenAI call is made for that section.

* **F10 – Plan generation**

  * When a plan file does not exist:

    * `build_plan_json_prompt(chapter, section)` is used to create the prompt.
    * `client.responses.create(...)` is called with:

      * `model=MODEL_NAME`
      * `reasoning={"effort": "medium"}`
      * `max_output_tokens=4000`
    * The response is parsed with `response_to_text`, then `json.loads`.
    * The resulting JSON must have at least:

      * `"narrative"` (string)
      * `"examples"` (list of example specs: each has `title`, `summary`).

* **F11 – Plan dictionary**

  * `generate_section_plans` returns `plans_by_section[(chapter_title, section_title)] = plan_dict`.

---

### 1.4 OpenAI: Examples via Batch (Phase 2)

* **F12 – Custom ID mapping**

  * For every example in every plan:

    * A unique `custom_id` is built:

      * `example::<chapter-slug>::<section-slug>::<index>`
    * `spec_by_custom_id` contains:

      * `chapter_title`, `section_title`, `ex_index`, `ex_title`, `ex_summary`.

* **F13 – Round 1 Batch file**

  * `openai_examples_requests.jsonl` is created with one JSON object per example:

    * `{"custom_id": ..., "method": "POST", "url": "/v1/responses", "body": {...}}`
  * For round 1:

    * `body["input"]` = `build_example_triplet_prompt(...)`.
    * `max_output_tokens = 8000`.

* **F14 – Using existing Batch results**

  * If `openai_examples_results.jsonl` already exists, the script **does not** create a new batch; it parses the existing results.

* **F15 – Multi-round continuation**

  * Up to `max_rounds` (default 3).
  * For round `r>1`:

    * Only incomplete examples are included in `openai_examples_requests_round{r}.jsonl`.
    * If we have previous partial text for an example, we send a special continuation prompt that:

      * Shows the existing content.
      * Asks only to continue, not to repeat, and to finish with `%%% SOLUTION END %%%`.
    * `max_output_tokens = 8000` again.

* **F16 – Parsing batch output**

  * `parse_round_results`:

    * Reads each line of `results_path`.
    * Extracts `response["body"]`, and from there concatenates all `output_text` chunks.
    * Appends the new text to `combined_text_by_id[custom_id]`.
    * Checks for presence of markers in **combined** text:

      * `%%% INQUIRY START %%%`, `%%% INQUIRY END %%%`,
        `%%% SOLUTION START %%%`, `%%% SOLUTION END %%%`.
    * If all markers present:

      * Marks example as `completed=True`.
    * Otherwise:

      * Marks as `completed=False` with `incomplete_reason`.
      * Adds `custom_id` to `incomplete_ids`.

* **F17 – Final example_outputs**

  * After all rounds (or earlier if everything done):

    * For each example, `combined_text_by_id[custom_id]` is split:

      * `inquiry` = between `% INQUIRY START %%%` and `% INQUIRY END %%%`.
      * `solution` = between `% SOLUTION START %%%` and `% SOLUTION END %%%`.
    * If `solution_block` is empty but markers exist, the whole combined text is used as `solution`.
    * `example_outputs[(chapter, section, ex_index)] = {"title", "inquiry", "solution"}`.

---

### 1.5 OpenAI: Assembling LaTeX themes (Phase 3)

* **F18 – Chapter LaTeX structure**

  * For each theme spec:

    * Create `themes/<filename>` with:

      * `\chapter{chapter_title}` at top.
      * For each subsection:

        * `\section{section_title}`.

* **F19 – Narrative comments**

  * For each section where a plan exists:

    * If `plan["narrative"]` is nonempty:

      * It is written as `%`-prefixed lines under `% --- Narrative plan (auto-generated) ---`.

* **F20 – Examples in themes**

  * For each example (by index):

    * If `example_outputs[(chapter, section, idx)]` exists:

      * If `inquiry` nonempty:

        * Write comment `% ===== Example k: Title (inquiry-based) =====` followed by `inquiry` LaTeX.
      * Always write comment `% ===== Example k: Title (full solution) =====` followed by `solution` LaTeX.
    * Otherwise:

      * Write `% TODO: No generated content yet for example...`.

---

## 2. Test plan (TDD-style checklist)

Use `pytest` with `tmp_path` fixtures and mocks for OpenAI parts.

### 2.1 Unit tests – utilities & helpers

1. **test_slugify_basic**

   * Input: `"Complex Variables and Complex-valued Functions"`.
   * Expect: `"complex-variables-and-complex-valued-functions"`.

2. **test_extract_block_happy_path**

   * Input string contains `"%%% INQUIRY START %%% foo %%% INQUIRY END %%%"`.
   * Expect: `"foo"`.

3. **test_extract_block_missing_markers_returns_empty**

   * Start or end marker missing → returns `""`.

4. **test_write_if_missing_creates_and_is_idempotent**

   * First call: file is created with content.
   * Second call: content unchanged.

5. **test_extract_output_text_handles_plain_dict**

   * Give a fake dict `{"output": [{"content": [{"type": "output_text", "text": {"value": "hello"}}]}]}`.
   * Expect `"hello"`.

6. **test_extract_output_text_handles_sdk_like_object**

   * Make a tiny fake class with `model_dump()` returning the above dict.
   * `extract_output_text(fake_obj)` returns `"hello"`.

7. **test_extract_output_text_from_response_obj_basic**

   * Same as 5 but using `extract_output_text_from_response_obj`.

---

### 2.2 Unit tests – section plans

8. **test_generate_section_plans_uses_cache_if_exists**

   * Create a `plans/` directory with one JSON file for a given `(chapter, section)` key.
   * Mock `client` to raise if called.
   * Call `generate_section_plans`; assert:

     * Returned dict has the cached entry.
     * Client was never used.

9. **test_generate_section_plans_calls_openai_for_missing_plan**

   * Use `tmp_path` as root (empty `plans/`).
   * Provide a fake client whose `.responses.create()` returns an object whose `model_dump()` yields:

     * `{"output": [{"content": [{"type": "output_text", "text": {"value": '{"narrative":"foo","examples":[{"title":"E1","summary":"bar"}]}'}}]}]}`.
   * Call `generate_section_plans`.
   * Assert:

     * `plans_dir` contains json files.
     * `plans_by_section[(chapter, section)]` has keys `"narrative"` and `"examples"`.
     * File content is valid JSON.

10. **test_generate_section_plans_handles_bad_json**

    * Fake client returns a non-JSON string (`"not json"`).
    * Expect:

      * The offending section is **not** present in `plans_by_section`.
      * No file is written.
      * (Optionally) capture logs to see the error message.

---

### 2.3 Unit tests – parse_round_results

You don’t need real OpenAI here; you feed a handcrafted `results_path`.

11. **test_parse_round_results_marks_complete_when_all_markers_present**

    * JSONL line with:

      * `custom_id`: "example::complex-analysis::x::0"
      * `response.body.output` containing `%%% INQUIRY START %%% ... %%% INQUIRY END %%%` and `%%% SOLUTION START %%% ... %%% SOLUTION END %%%`.
      * `body.status = "completed"`, `incomplete_details = None`.
    * Call `parse_round_results`.
    * Expect:

      * `combined_text_by_id[custom_id]` contains the segment.
      * `example_state_by_id[custom_id]["completed"] is True`.
      * Returned `incomplete_ids` is empty.

12. **test_parse_round_results_marks_incomplete_when_missing_solution_end**

    * As above, but omit `%%% SOLUTION END %%%`.
    * Expect:

      * `completed` False.
      * `incomplete_ids == [custom_id]`.

13. **test_parse_round_results_handles_missing_response**

    * JSONL line with `"response": null` and some `"error"` dict.
    * Expect:

      * `example_state_by_id[custom_id]["completed"] is False`.
      * Reason contains `"no_response"`.

---

### 2.4 Unit / integration tests – run_example_batch (mocked)

Here you want to isolate `run_example_batch` and feed it tiny plans + fake results.

14. **test_run_example_batch_single_round_complete**

    * Setup:

      * `plans_by_section` has one section, one example.
      * Create a fake `openai_examples_results.jsonl` with a complete example (all markers).
    * Call `run_example_batch(..., client=None, max_rounds=1)`.
    * Expect:

      * `example_outputs` has one entry for `(chapter, section, 0)`.
      * `example_outputs[...]` has non-empty `inquiry` and `solution`.

15. **test_run_example_batch_two_rounds_for_incomplete_example**

    * Setup:

      * Round 1 results file where the example has only INQUIRY and SOLUTION START (no END).
      * Round 2 results file where it contains only the continuation with `%%% SOLUTION END %%%`.
      * Use `max_rounds=2`.
    * Call `run_example_batch`.
    * Expect:

      * Combined text has full inquiry and solution with END marker.
      * Example marked complete.
    * For this, you can:

      * Manually create `openai_examples_results.jsonl` (round 1).
      * Manually create `openai_examples_results_round2.jsonl` (round 2).

16. **test_run_example_batch_stops_at_max_rounds**

    * Three rounds allowed, but all three result files still missing `%%% SOLUTION END %%%`.
    * Expect:

      * Example appears in `example_outputs` but with `solution` = combined raw text and incomplete warning printed.

---

### 2.5 Integration tests – themes & LaTeX

These check that files are wired correctly.

17. **test_generate_themes_with_openai_stub_when_no_client**

    * Monkeypatch `get_openai_client` to return `None`.
    * Call `generate_themes_with_openai(root, use_openai=True)`.
    * Expect:

      * `themes/*.tex` exist.
      * Each has `\chapter{}` and `\section{}` lines and `% TODO` text.

18. **test_generate_themes_with_openai_uses_plans_and_examples**

    * Monkeypatch:

      * `get_openai_client` → a dummy object (not used).
      * `generate_section_plans` → returns a small fake dict with one chapter + section + plan.
      * `run_example_batch` → returns a dict with one example having `inquiry` and `solution`.
    * Call `generate_themes_with_openai(root, use_openai=True)`.
    * Expect in the relevant `themes/<file>.tex`:

      * `% --- Narrative plan (auto-generated) ---` and commented narrative.
      * `% ===== Example 1: ... (inquiry-based) =====` and the inquiry block.
      * `% ===== Example 1: ... (full solution) =====` and the solution block.

19. **test_main_creates_full_skeleton_without_openai**

    * Run `main()` with `--root` pointing to a temporary directory and **no** `--with-openai`.
    * Easiest is to call the functions directly (or use `subprocess` on the script).
    * Expect:

      * `main.tex`, `Makefile`, exam files, workflow, `themes/*.tex` exist.
      * Running `pdflatex main.tex` (if TeX installed in your environment) produces `main.pdf` without LaTeX errors.
      * (You can skip the actual `pdflatex` in CI and just assert the includes are consistent.)

20. **test_main_with_openai_fallbacks_to_stub_if_no_key**

    * Make sure `OPENAI_API_KEY` is not set.
    * Call `main()` with `--with-openai`.
    * Expect:

      * Same behavior as `use_openai=False`: stub `themes/*.tex` created, no crash.

---

### 2.6 Optional: “meta” tests

If you want to be really extra:

21. **test_main_is_idempotent**

    * Run `main()` twice on the same `tmp_path` root (with or without OpenAI mocked out).
    * Expect:

      * Files that should not be overwritten (`main.tex`, exam files, Makefile, workflow) stay identical (compare hashes).
      * `themes/*.tex` may change only if you intentionally regenerate them; you can choose to allow overwrite or not.

22. **test_cli_argument_parsing_defaults**

    * Simulate `sys.argv = ["init_methods_book.py"]` and ensure root defaults to `"methods-book"` and `with_openai=False`.

---

## 3. How to TDD this in practice

A possible workflow for you:

1. **Create `tests/` directory** with `test_init_methods_book.py`.
2. Start with the **pure filesystem + utility tests** (F3–F8 + utilities). No OpenAI, no mocking.
3. Add tests for **plan caching + parsing** (F9–F11) using a fake client.
4. Add tests for **parse_round_results** and **run_example_batch** using hand-crafted JSONL files.
5. Finally, test **`generate_themes_with_openai` + `main()`** with heavy mocking of OpenAI-dependent functions.

This keeps you in a nice TDD loop:
**(write test → run → watch it fail → patch script / refactor → run again → green).**

If you want, next step I can write a concrete `pytest` file with a few of these tests fully implemented so you can drop it into `tests/` and iterate from there.
