
# Methods Bible – Applied Math Exam & Methods Book

This repo scaffolds a **LaTeX book** for your Methods in Applied Mathematics course:

- Organized **by theme** (Complex Analysis, Fourier Analysis, ODE, PDE).
- Also organized **by exam** with canonical problem files.
- Can optionally use the **OpenAI API + Batch** to auto-generate:
  - Section plans (what examples to cover).
  - Inquiry-based worked examples.
  - Full, Chicago-style expository solutions.

The idea: this becomes your **personal “Methods Bible”** with:
- A clean LaTeX book.
- Structured, reusable problem files.
- Inquiry-based, guided learning content.

---

## Repo layout

After running the initializer, you’ll have something like:

```text
Methods-Bible/
  init_methods_book.py        # main project bootstrap script
  shared_prompts.py           # reusable prompt templates for plan + examples
  prompts_for_sections.py     # interactive / CLI prompting helper (optional)
  README.md

  methods-book/
    main.tex                  # LaTeX book driver
    figures/                  # for TikZ / PDF figures
    themes/
      complex_analysis.tex
      fourier_analysis.tex
      ode.tex
      pde.tex
    exams/
      exam1.tex               # example exam chapter
    problems/
      exams/
        exam1/
          ex1_prob01.tex      # canonical solved problem file

    plans/                    # auto-generated section plans (JSON)
      complex-analysis-...json
      ...
    openai_examples_requests.jsonl  # Batch API input for all examples
    openai_examples_results.jsonl   # Batch API output

    Makefile                 # `make` → main.pdf
    .github/
      workflows/
        latex.yml            # GitHub Actions build

    venv/                    # (optional) Python virtualenv if you create one
```

> The `plans/` directory and the JSONL files are only created when you run with `--with-openai`.

---

## 1. Bootstrapping the project (Linux recommended)

### 1.1. Create & activate a virtual environment

From the repo root:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install Python dependencies (minimal):

```bash
pip install openai
```

If you prefer, create a `requirements.txt` like:

```text
openai>=1.0.0
```

and then:

```bash
pip install -r requirements.txt
```

### 1.2. Make sure LaTeX is installed

On Ubuntu / Debian:

```bash
sudo apt-get update
sudo apt-get install -y \
  texlive-latex-recommended \
  texlive-latex-extra \
  texlive-fonts-recommended \
  make
```

On other systems, install a TeX Live distribution and `make` via your package manager.

---

## 2. Creating the LaTeX skeleton

### Option A – Pure LaTeX skeleton (no OpenAI)

From repo root:

```bash
source venv/bin/activate   # if using venv
python init_methods_book.py --root methods-book
```

This will create:

* `methods-book/main.tex`
* `methods-book/themes/*.tex` with simple `\chapter` / `\section` + TODO comments.
* `methods-book/problems/exams/exam1/ex1_prob01.tex`
* `methods-book/exams/exam1.tex`
* `methods-book/Makefile`
* `methods-book/.github/workflows/latex.yml`

Compile the PDF:

```bash
cd methods-book
make           # or: pdflatex main.tex; pdflatex main.tex
```

### Option B – With OpenAI (plans + Batch-generated examples)

Set your API key:

```bash
export OPENAI_API_KEY="sk-..."
```

Optionally choose a model (defaults to `gpt-5.1`):

```bash
export METHODS_BOOK_MODEL="gpt-5.1"
```

Then run:

```bash
source venv/bin/activate
python init_methods_book.py --root methods-book --with-openai
```

This does:

1. **Scaffold everything** (`main.tex`, `themes/`, `exams/`, `problems/`, `Makefile`, Actions).

2. **Phase 1 – Plans (Responses API)**
   For each `(chapter, section)` in `THEME_SPECS`:

   * Calls `build_plan_json_prompt(chapter_title, section_title)` (from `shared_prompts.py`).
   * Asks for:

     * 1–3 paragraph narrative.
     * 3–7 example ideas with titles, summaries, and difficulty variants.
   * Saves each plan as JSON under `methods-book/plans/<slug>.json`.

3. **Phase 2 – Examples (Batch API)**
   For all examples across all sections:

   * Builds one big JSONL file `openai_examples_requests.jsonl` with entries like:

     * `custom_id = example::<chapter>::<section>::<index>`
     * `body.input = build_example_triplet_prompt(...)`
   * Submits a Batch job to `/v1/responses`.
   * Polls until it completes.
   * Downloads results to `openai_examples_results.jsonl`.
   * Each example response is expected to contain markers:

     ```text
     %%% INQUIRY START %%%
     ... LaTeX for inquiry-based problem ...
     %%% INQUIRY END %%%

     %%% SOLUTION START %%%
     ... LaTeX for full problem + solution ...
     %%% SOLUTION END %%%
     ```

4. **Phase 3 – Assemble themed chapters**
   For each `themes/*.tex`:

   * Writes `\chapter{...}`.
   * For each section:

     * Writes `\section{Section Title}`.
     * Inserts the plan narrative as `%` comments.
     * Then, for each example:

       * Adds the inquiry-based LaTeX.
       * Adds the full solution LaTeX.

You can then `cd methods-book && make` to compile the book.

---

## 3. How the 3-Phase workflow is designed

### Phase 1 – Planning (section level)

Implemented in `shared_prompts.py`:

```python
build_plan_json_prompt(chapter_title, section_title) -> str
```

* The prompt asks for:

  * A narrative description of the section.
  * 3–7 **example plans** (title, summary, technique, variants).
* The response is **JSON**, parsed and stored under `methods-book/plans/`.

Each plan looks roughly like:

```json
{
  "section_title": "Phase Space Dynamics for Conservative and Perturbed Systems",
  "narrative": "This section studies ...",
  "examples": [
    {
      "title": "Linear Harmonic Oscillator",
      "summary": "Phase portrait, energy level sets, etc.",
      "key_techniques": ["phase portrait", "linearization"],
      "variants": ["undamped", "damped", "forced"]
    },
    ...
  ]
}
```

### Phase 2 – Inquiry + Solution (example level, Batch)

Also in `shared_prompts.py`:

```python
build_example_triplet_prompt(chapter_title, section_title, example_title, example_summary)
```

For each example in each plan:

* We build one prompt that asks for **both**:

  * An **inquiry-based worksheet** version (guided questions + hints).
  * A full **problem + solution** exposition.

The prompt tells the model to wrap the outputs in the 4 markers shown above so the batch parser can split them.

The Batch job is triggered by `init_methods_book.py` when `--with-openai` is used.

### Phase 3 – Assembly into LaTeX chapters

`init_methods_book.py`:

* Reads `plans/*.json` and `openai_examples_results.jsonl`.
* For each chapter/section:

  * Writes section narrative as comments.
  * Inserts each example’s inquiry block + full solution block under that section.

You can always edit the final `.tex` files by hand.

---

## 4. Manual / interactive usage with `prompts_for_sections.py`

Sometimes you’ll want to work on a single section or a single example manually.

`prompts_for_sections.py` uses the same underlying ideas but in a **CLI-friendly way**:

```bash
# Just print the planning prompt (copy into Playground or API)
python prompts_for_sections.py plan \
    --section "Phase Space Dynamics for Conservative and Perturbed Systems"

# Actually call OpenAI and print the JSON plan
python prompts_for_sections.py plan \
    --section "Phase Space Dynamics for Conservative and Perturbed Systems" \
    --run

# Generate inquiry-based LaTeX for a specific example (and view in terminal)
python prompts_for_sections.py inquiry \
    --section "Phase Space Dynamics for Conservative and Perturbed Systems" \
    --example "Damped harmonic oscillator with small nonlinear perturbation" \
    --run

# Generate full problem+solution LaTeX
python prompts_for_sections.py solution \
    --section "Phase Space Dynamics for Conservative and Perturbed Systems" \
    --example "Damped harmonic oscillator with small nonlinear perturbation" \
    --run
```

You can paste that LaTeX into the appropriate `themes/*.tex` file if you’re doing a one-off manual refinement.

---

## 5. GitHub Actions workflow

The repo includes `.github/workflows/latex.yml` so that:

* On each `push` or PR to `main` / `master`, GitHub:

  * Installs TeX Live.
  * Runs `pdflatex main.tex` twice.
  * Uploads `main.pdf` as a build artifact named `methods-book-pdf`.

Usage:

* Push your changes to GitHub.
* Open the Actions tab.
* Download the latest `methods-book-pdf` artifact.

> The CI build does **not** call OpenAI. It just compiles whatever LaTeX files are in the repo.

---

## 6. Adding or regenerating topics

### Add a new section/topic

1. Edit `THEME_SPECS` in `init_methods_book.py`:

   * Add a new entry in `subsections` for the relevant chapter.
2. Delete any old plan/result for that section if needed:

   * `rm methods-book/plans/<slug>.json` (if it exists).
3. Re-run:

   ```bash
   source venv/bin/activate
   export OPENAI_API_KEY=...
   python init_methods_book.py --root methods-book --with-openai
   ```

   * The script will:

     * Keep existing chapters.
     * Generate plans/examples **only** for the new sections that don’t have `.tex` yet.

### Regenerate a specific section

If you want to fully redo one section:

1. Delete its LaTeX and plan:

   ```bash
   rm methods-book/themes/<chapter>.tex     # or edit by hand
   rm methods-book/plans/<slug>.json
   ```

2. Re-run `init_methods_book.py --with-openai`. It will:

   * Recreate the plan.
   * Rebuild the Batch job for all examples.
   * Reassemble the chapter.

(Or do it more surgically by editing the plan JSON and rerunning only the batch part in a custom script.)

---

## 7. How to contribute

Contributions and collaboration are welcome, especially from people who:

* Like **inquiry-based learning** for math methods.
* Enjoy curating **good examples** and **hint structures**.
* Want to clean up expository LaTeX.

### Guidelines

1. **Issues & ideas**

   * Use GitHub Issues to propose:

     * New sections / chapters.
     * Better example families (e.g., more physical applications, PDE case studies).
     * Improvements to the prompt design.

2. **Pull requests**

   * Try to keep PRs focused:

     * One PR for LaTeX content changes.
     * One PR for script / infra changes.
   * If you touch prompts or the batch pipeline:

     * Add a short note in the PR about **cost impact** and **expected token volume**.

3. **LaTeX style**

   * Write in full sentences.
   * Prefer standard notation and Chicago-style exposition.
   * Keep inquiry-based problems and final solutions clearly separated.

4. **Prompt editing**

   * If you edit `shared_prompts.py`:

     * Keep the 3-phase structure: PLAN / INQUIRY / SOLUTION.
     * Keep the marker lines for batch parsing:

       * `%%% INQUIRY START %%%`, `%%% INQUIRY END %%%`
       * `%%% SOLUTION START %%%`, `%%% SOLUTION END %%%`

5. **Local testing**

   * Before pushing:

     ```bash
     source venv/bin/activate
     cd methods-book
     make
     ```
   * Make sure `main.pdf` compiles with no errors.

---

If you want, we can next add a small `requirements.txt` and a `Makefile` target like `make plan` / `make batch` that just reruns phases 1–2 without touching the LaTeX scaffolding.
