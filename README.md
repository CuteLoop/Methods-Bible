
# Methods Bible – Methods in Applied Mathematics

This repo is a personal **Methods in Applied Mathematics** textbook + solved‐problems notebook.

It is organized in **two main ways**:

1. **By topic** – core themes (complex analysis, Fourier analysis, ODEs, PDEs).
2. **By exam** – solved problems organized by exam and problem number.

There is also a small automation layer to:
- scaffold the LaTeX project (`init_methods_book.py`), and  
- generate topic content via a 3-phase OpenAI workflow (`prompts_for_sections.py`).

> **Note:** The workflow is designed and tested with a **Linux** environment in mind
> (e.g. Ubuntu). Other platforms can work, but commands may need adaptation
> (especially package installation).

---

## 1. Repository layout

After running the initializer, the directory tree looks like:

```text
methods-book/
  main.tex
  Makefile
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

  .github/
    workflows/
      latex.yml
````

* `main.tex` – master LaTeX file; includes all thematic chapters and exams.
* `themes/*.tex` – chapters by **theme**:

  * `complex_analysis.tex`
  * `fourier_analysis.tex`
  * `ode.tex`
  * `pde.tex`
* `exams/*.tex` – chapters by **exam** (e.g. `exam1.tex`).
* `problems/exams/examN/*.tex` – individual problems + solutions per exam.
* `Makefile` – build helper (`make` → `main.pdf`).
* `.github/workflows/latex.yml` – GitHub Actions workflow to build the PDF on push.

---

## 2. Requirements

### 2.1 System (Linux recommended)

On **Ubuntu/Debian**–like systems:

```bash
  sudo apt-get update
  sudo apt-get install -y \
    python3 python3-venv python3-pip \
    make \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended

```

You need:

* Python ≥ 3.9
* `make`
* A LaTeX distribution with standard packages

### 2.2 Python packages

Python dependencies are listed in `requirements.txt` (at minimum it should contain `openai`):


You can add more tools later (e.g. `black`, `isort`, etc.).

---

## 3. Bootstrapping the project

The idea:

1. Clone repo
2. Create & activate a virtual environment
3. Install Python dependencies
4. Initialize the LaTeX project structure
5. Build the PDF

### 3.1 Clone and set up `venv`

From your terminal:

```bash
# 1) Clone the repo
git clone https://github.com/your-user/Methods-Bible.git
cd Methods-Bible

# 2) Create a virtual environment
python3 -m venv venv

# 3) Activate the virtual environment
source venv/bin/activate
# (Your prompt should now show (venv) ...)

# 4) Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

> If you’re on a non-Linux system, the `source venv/bin/activate` command may need
> to be adapted (e.g. `venv\Scripts\activate` on Windows PowerShell).

### 3.2 Initialize the LaTeX project

With the virtual environment active and from the repo root:

```bash
# Simple skeleton (stubs in themes/*.tex)
python3 init_methods_book.py --root methods-book
```

Or, to **auto-populate** all themed chapters using OpenAI:

```bash
export OPENAI_API_KEY="your-key-here"

python3 init_methods_book.py --root methods-book --with-openai
```

This will create `methods-book/` with:

* `main.tex`
* `themes/*.tex` (either stubs with TODOs or OpenAI-generated examples)
* `figures/`
* `problems/exams/exam1/ex1_prob01.tex`
* `exams/exam1.tex`
* `Makefile`
* `.github/workflows/latex.yml`

### 3.3 Build the PDF (locally)

```bash
cd methods-book
make
# or, if you prefer:
pdflatex main.tex
pdflatex main.tex
```

The output is `methods-book/main.pdf`.

---

## 4. How the LaTeX is organized

### 4.1 By theme (`themes/`)

Each themed chapter is a standalone `\chapter{...}` file, included from `main.tex`:

```tex
% Part I: Applied Analysis
\part{Applied Analysis}

\include{themes/complex_analysis}
\include{themes/fourier_analysis}

% Part II: Differential Equations
\part{Differential Equations}

\include{themes/ode}
\include{themes/pde}
```

When initialized **without** OpenAI, each section has a stub like:

```tex
\section{Phase Space Dynamics for Conservative and Perturbed Systems}
% TODO (Madeline + Joel): invent an OpenAI prompt for this topic,
% generate rough examples, and then write the curated theory,
% problems, and solutions here.
```

Later, these stubs are replaced by content generated via the 3-phase workflow.

### 4.2 By exam (`exams/` and `problems/exams/`)

Exams live in `exams/examN.tex` and include per‐problem files from `problems/exams/examN/`. For example:

```tex
% exams/exam1.tex
\chapter{Exam 1 – Sample Problems}

\section*{Original Exam Statement}
% TODO: paste or summarize the original exam statement here.

\section{Solved Problems}
\input{problems/exams/exam1/ex1_prob01}
```

Each problem file typically contains:

```tex
\begin{problem}[Exam 1, Problem 1: Warm-up ODE]\label{prob:ex1-1-warmup-ode}
Solve the initial value problem
\[
  y'(t) = -2 y(t), \qquad y(0) = 1.
\]
\end{problem}

\begin{solution}
... full solution ...
\end{solution}
```

`main.tex` includes exams as a separate part:

```tex
\part{Exams and Problem Collections}
\include{exams/exam1}
% TODO: add \include{exams/exam2}, etc.
```

---

## 5. GitHub Actions: automatic LaTeX build

The workflow `.github/workflows/latex.yml` builds `main.pdf` on GitHub for every push/PR to `main` or `master`.

No extra configuration is required:

1. Push your changes:

   ```bash
   git add .
   git commit -m "Update methods content"
   git push
   ```

2. GitHub will:

   * Install TeX Live on an Ubuntu runner.
   * Run `pdflatex main.tex` twice.
   * Upload `main.pdf` as an artifact named `methods-book-pdf`.

Download the PDF from the **Actions** tab.

---

## 6. Generating new topic content (3-phase workflow)

To systematically populate each topic/section, use:

* `prompts_for_sections.py` (at repo root, next to `init_methods_book.py`).

This script implements a **three-phase workflow**:

1. **PLAN** (section-level)
2. **INQUIRY** (example-level, guided, inquiry-based)
3. **SOLUTION** (example-level, full exposition)

### 6.1 Setup (once)

Inside your activated `venv`:

```bash
pip install -r requirements.txt
export OPENAI_API_KEY="your-key"
```

### 6.2 Phase 1 – Plan the section

Pick a section/topic, e.g.:

> Phase Space Dynamics for Conservative and Perturbed Systems

Run:

```bash
python3 prompts_for_sections.py plan \
  --section "Phase Space Dynamics for Conservative and Perturbed Systems" \
  --run
```

You get:

* A narrative description of the section.
* A list of 3–7 example ideas with techniques and difficulty levels.
* A proposed ordering (learning narrative).

Paste this into comments or a planning file.

### 6.3 Phase 2 – Inquiry-based version of a chosen example

Choose one of the example ideas, e.g.:

> "Damped harmonic oscillator with small nonlinear perturbation"

Run:

```bash
python3 prompts_for_sections.py inquiry \
  --section "Phase Space Dynamics for Conservative and Perturbed Systems" \
  --example "Damped harmonic oscillator with small nonlinear perturbation" \
  --run
```

This produces a LaTeX snippet like:

```tex
\begin{problem}[Descriptive title]
% Motivational paragraph

(a) First exploratory question ...
% Hint: ...

(b) Next guided question ...
% Hint: ...

...

(e) Extension / "what if" question.
\end{problem}
```

Paste this into the corresponding `\section{...}` in `themes/ode.tex`
(or another themed chapter).

### 6.4 Phase 3 – Full solution/exposition for the same example

For the same example description:

```bash
python3 prompts_for_sections.py solution \
  --section "Phase Space Dynamics for Conservative and Perturbed Systems" \
  --example "Damped harmonic oscillator with small nonlinear perturbation" \
  --run
```

You get:

```tex
\begin{problem}[Descriptive title]
  ... concise, self-contained statement ...
\end{problem}

\begin{solution}
  ... full, Chicago-style exposition:
  complete sentences, clear reasoning,
  minimal unnecessary symbols, connections to the section theme ...
\end{solution}
```

You can either:

* Place this directly under the inquiry-based version, or
* Store it as an exam-style problem under `problems/exams/...`.

### 6.5 Rebuild

```bash
cd methods-book
make
```

Review `main.pdf` to see your new content integrated.

---

## 7. How to contribute (for future you / collaborators)

* Prefer editing **content files**:

  * `themes/*.tex` for topic-based narrative + examples.
  * `exams/*.tex` and `problems/exams/*` for exam-style problems.
* Keep `main.tex` structure stable unless you are reorganizing the book.
* Workflow for adding material:

  1. Update or add a `\section{...}` in a `themes/*.tex` file.
  2. Use `prompts_for_sections.py` to build:

     * a plan,
     * an inquiry-based problem,
     * and a full solution.
  3. If the problem relates to a specific exam, also add it under `problems/exams/examN/` and include it from `exams/examN.tex`.
  4. Run `make` to confirm the LaTeX builds cleanly.
  5. Commit and push; GitHub Actions will build `main.pdf` for you.

This way, the **Methods Bible** grows in a structured, inquiry-based, and exam-aware way, while staying friendly to Linux + venv workflows. 🧠📚

