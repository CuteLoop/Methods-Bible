Nice, the beast compiles and now we get to *feed it more problems* 😈

Here’s a fresh README you can drop in `Methods-Bible/README.md`, plus a concrete workflow for “how do I add solved problems from past exams?” using the structure you already have.

---

````markdown
# Methods Bible 📖

A living, 800+ page LaTeX “bible” for **Methods of Applied Mathematics**: ODEs, PDEs, Fourier analysis, complex analysis, plus a growing archive of **exam-style problems with solutions**.

The repo has two main layers:

- **`methods-book/`** – the LaTeX book (chapters, figures, problems, exams, tools).
- **`src/` + `tests/`** – Python tooling to scaffold content, run OpenAI batches, and keep the book consistent.

---

## 1. Repository Layout

```text
Methods-Bible/
├── methods-book/           # The LaTeX project ("Methods Bible" book)
│   ├── main.tex            # Top-level book file
│   ├── Makefile            # Build commands (pdflatex)
│   ├── themes/             # Main chapters (ODE, PDE, Fourier, Complex, ...)
│   ├── problems/           # Thematic problem sets / exercises
│   ├── exams/              # Past exams and exam-style collections
│   ├── figures/            # TikZ / image assets
│   ├── tools/              # LaTeX tooling (scan regions, patch with OpenAI, etc.)
│   └── tests/              # Tests for LaTeX tooling
├── src/                    # Python utilities + OpenAI batch drivers
│   ├── init_methods_book.py
│   ├── prompts_for_sections.py
│   ├── shared_prompts.py
│   └── __init__.py
├── tests/                  # Python tests for src/ tools
├── docs/                   # (Optional) extra docs / notes
├── requirements.txt        # Python dependencies
└── venv/                   # Local virtualenv (ignored in git)
````

---

## 2. Setup

### 2.1. Python environment

From repo root:

```bash
cd ~/Github/Methods-Bible
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run tests:

```bash
pytest
```

* At **repo root** → tests for `src/`.
* Inside **`methods-book/`** → tests for LaTeX tools (`tools/`).

### 2.2. Building the book (LaTeX)

From `methods-book/`:

```bash
cd methods-book
make          # runs pdflatex (twice) on main.tex
```

Artifacts:

* `main.pdf` – the full book.
* `logs/` (if present) – LaTeX logs / outputs.
* Auxiliary files like `main.aux`, `main.log`, etc.

---

## 3. Tooling: How the “scan + fix + patch” pipeline works

The LaTeX is big. Instead of hand-fixing every warning, we have a small workflow to:

1. **Scan** LaTeX files for problematic regions (errors, overfull boxes, broken environments).
2. **Prepare prompts** for OpenAI (mini coding model).
3. **Receive a patch** in `git diff` format.
4. **Apply patch** and re-run tests/LaTeX.

The Python entrypoints live in `methods-book/tools/` (LaTeX layer) and `src/` (OpenAI/batch orchestration).

### 3.1. Typical workflow

1. **Compile and capture LaTeX warnings**

   ```bash
   cd methods-book
   make > logs/latex_build.log 2>&1
   ```

2. **Scan LaTeX for regions to fix**
   (Example CLI – adapt to your exact tool name, e.g. `latex_scan_regions.py`):

   ```bash
   python tools/latex_scan_regions.py \
       --log logs/latex_build.log \
       --root . \
       --output logs/regions.json
   ```

   This should produce a JSON file describing “regions” like:

   ```json
   [
     {
       "file": "themes/pde.tex",
       "start_line": 4881,
       "end_line": 4897,
       "issue": "Bad math environment delimiter"
     },
     ...
   ]
   ```

3. **Generate an OpenAI request batch**

   From repo root:

   ```bash
   cd ..
   python -m src.init_methods_book \
       make-openai-batch \
       --regions methods-book/logs/regions.json \
       --output methods-book/openai_examples_requests_roundN.jsonl
   ```

   This creates prompts that:

   * show the region,
   * ask the model to fix LaTeX,
   * request a **`git diff` style patch** as output.

4. **Send batch to OpenAI, get results**

   * Upload `openai_examples_requests_roundN.jsonl`.
   * Download `openai_examples_results_roundN.jsonl` into `methods-book/`.

5. **Apply patches**

   ```bash
   cd methods-book
   python tools/apply_openai_patches.py \
       --results openai_examples_results_roundN.jsonl
   ```

   This script should:

   * parse the `git diff`-style outputs,
   * sanity-check them,
   * apply them using `patch` (or equivalent).

6. **Rebuild and re-test**

   ```bash
   make
   pytest      # from repo root and/or methods-book
   ```

Rinse and repeat until LaTeX + tests are happy.

---

## 4. Adding Solved Problems from Past Exams

You have an 800-page bible; now you want to **grow a serious problems/solutions archive**. Here’s a clean, repeatable workflow that fits the current structure.

### 4.1. Where do exam problems live?

We’ll use:

* `methods-book/exams/` – exam collections, organized by course/term.
* `methods-book/problems/` – thematic/curated problem sets that may reuse exam problems by topic.

Suggested naming:

```text
methods-book/exams/
  MATH116_F24_Test3.tex
  MATH116_F24_Test2.tex
  MATH589_FA25_Midterm1.tex
  ...
```

Inside each file:

* Use consistent environments (whatever you already have in `main.tex`), e.g.:

  ```latex
  \begin{problem}[MATH 116 – Fall 2024 – Test 3 – Q1]
  ...
  \end{problem}

  \begin{solution}
  ...
  \end{solution}
  ```

* Label problems in a machine-friendly way:

  ```latex
  \begin{problem}[Optimization with exponential demand]
  \label{prob:116-F24-T3-1}
  ...
  \end{problem}
  ```

  Now you can reference it anywhere:

  ```latex
  See Problem~\ref{prob:116-F24-T3-1} for a classic example.
  ```

### 4.2. Include exams into the book

In `main.tex`, add a dedicated part (if not already):

```latex
\part{Exam Problems and Solutions}

\chapter{MATH 116 – Past Exams}
\input{exams/MATH116_F24_Test1}
\input{exams/MATH116_F24_Test2}
\input{exams/MATH116_F24_Test3}

\chapter{MATH 589 – Past Exams}
\input{exams/MATH589_FA25_Midterm1}
% ...
```

This keeps:

* **Main topics** in `themes/`.
* **Exam archive** in `exams/`, included in a clean, predictable place.

### 4.3. Workflow for adding a *new* past exam (with solutions)

Suppose you have an old PDF / Word / handwritten exam that you’ve solved.

1. **Create a new LaTeX file in `exams/`**

   Example:

   ```bash
   cd methods-book
   touch exams/MATH589_FA25_Midterm1.tex
   ```

2. **Use the problem/solution environment**

   Inside `MATH589_FA25_Midterm1.tex`:

   ```latex
   \chapter*{MATH 589 – Fall 2025 – Midterm 1}
   \addcontentsline{toc}{chapter}{MATH 589 – Fall 2025 – Midterm 1}

   \begin{problem}[Green's function for a simple ODE]
   \label{prob:589-FA25-M1-1}
   Consider the boundary value problem
   \[
       -u''(x) = f(x), \quad 0 < x < 1,
   \]
   with boundary conditions $u(0)=u(1)=0$.
   \begin{enumerate}
       \item Derive the Green's function $G(x,\xi)$.
       \item Write the solution in terms of $G$ and $f$.
   \end{enumerate}
   \end{problem}

   \begin{solution}
   % Your fully worked solution goes here.
   % You can reuse notation and results from the main text.
   ...
   \end{solution}
   ```

3. **Wire it into `main.tex`**

   Add to the appropriate chapter:

   ```latex
   \chapter{MATH 589 – Past Exams}
   \input{exams/MATH589_FA25_Midterm1}
   ```

4. **Compile & test**

   ```bash
   cd methods-book
   make
   ```

   If LaTeX complains about overfull boxes or small syntax mistakes, you can either fix them by hand or feed to the **scan + patch** pipeline.

---

## 5. Re-using exam problems by theme

Often, you’ll want:

* “Here’s a Green’s function problem from Exam X.”
* “Here’s an ODE stability problem from Test Y.”

You can **re-import** exam problems into thematic problem sets in `problems/`.

Example: create `problems/ode_exam_problems.tex`:

```latex
\chapter{ODE Problems from Past Exams}

We collect some ODE problems that originally appeared in MATH 589 exams.

\begin{problem}[From MATH 589 FA25 Midterm 1, Problem~\ref{prob:589-FA25-M1-1}]
\label{prob:ode-green-from-exam}
% You may either:
% (a) copy the statement, OR
% (b) summarize / slightly rephrase it.
...
\end{problem}

\begin{solution}
% Option 1: copy the exam solution
% Option 2: rewrite a more polished solution
...
\end{solution}
```

Then in `main.tex` you include:

```latex
\chapter{ODE – Additional Problems}
\input{problems/ode_exam_problems}
```

This lets you:

* Keep **exam provenance** (labels, references).
* Curate polished problem sets for study, separate from the raw exam booklet.

---

## 6. How to Collaborate

Whether it’s just Future-You or other humans, here’s the collaboration model.

### 6.1. Branching & commits

* **Main branch**: stable, compiles, tests pass.

* For new work:

  ```bash
  git checkout -b feature/add-ode-exam-problems
  ```

* Try to keep commits focused:

  * `Add MATH589 FA25 Midterm 1 exam file`
  * `Wire FA25 Midterm 1 exam into main.tex`
  * `Fix overfull boxes in PDE chapter`

### 6.2. Before opening a PR (or merging)

From repo root:

```bash
pytest
```

From `methods-book/`:

```bash
make           # ensure LaTeX compiles
pytest         # if you modify LaTeX tools
```

No red tests, and `main.pdf` builds → good to go.

### 6.3. Style

* **LaTeX**

  * Use existing environments (`problem`, `solution`, `theorem`, etc.).
  * Label things systematically: `prob:course-term-exam-problemNumber`.
  * Avoid super-wide inline math; move long formulas to `\[ ... \]`.

* **Python**

  * PEP 8-ish.
  * Add tests for new tooling under `tests/` or `methods-book/tests/`.
  * If a tool writes files, make it testable (e.g., take a directory argument and use `tmp_path` in tests).

---

## 7. TL;DR for adding a new batch of solved exam problems

1. Create a new file under `methods-book/exams/`:

   ```bash
   exams/MATH116_F24_Test3.tex
   ```

2. Transcribe each problem and its solution into `\begin{problem}...\end{problem}` and `\begin{solution}...\end{solution}` blocks with good labels.

3. Include that file from `main.tex` under the appropriate part/chapter.

4. Rebuild:

   ```bash
   cd methods-book
   make
   ```

5. If LaTeX is fussy, optionally run the **scan → OpenAI → patch** loop to clean up errors or ugly spots.

---

If you want, next step I can:

* draft a **template exam file** you can copy-paste for every new exam, and
* a tiny helper script that scaffolds `exams/MATH116_F24_Test3.tex` with a header + `\chapter*{...}` + a commented “drop problems here” section.
