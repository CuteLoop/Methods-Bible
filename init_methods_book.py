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

Optionally calls the OpenAI API to generate mock LaTeX content
for each themed chapter (instead of simple stubs).

Usage:
    python init_methods_book.py --root methods-book
    OPENAI_API_KEY=... python init_methods_book.py --root methods-book --with-openai
"""

import argparse
import os
from pathlib import Path
from textwrap import dedent

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


# -------------------------------
# OpenAI helper (optional)
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


def generate_chapter_with_openai(client, chapter_title, subsections):
    """
    Ask OpenAI to generate LaTeX for a chapter with given title and subsections.

    Returns a LaTeX string starting with \\chapter{...} and \\section{...}s,
    with one simple problem+solution per section.
    """
    subsection_list = "\n".join(f"- {s}" for s in subsections)
    prompt = f"""
You are helping write a LaTeX textbook for a graduate "Methods in Applied Mathematics" course.

Write LaTeX *only for a single chapter body*, with:

- A \\chapter{{{chapter_title}}} line.
- Then one \\section for each of the following subsection titles:

{subsection_list}

- In each section:
    - A short introductory paragraph (1–3 sentences, intuitive but concise).
    - One sample worked example, written as:
        \\begin{{problem}}[...] ... \\end{{problem}}
        \\begin{{solution}} ... \\end{{solution}}

Constraints:

- Do NOT include \\documentclass, preamble or \\begin{{document}}.
- Use inline math $...$ and display math \\[ ... \\] normally.
- Keep the examples relatively short and gentle; this is just a mock skeleton.
"""

    print(f"[INFO] Calling OpenAI for chapter '{chapter_title}'...")
    response = client.responses.create(
        model="gpt-5.1-mini",
        input=prompt.strip(),
    )
    text = getattr(response, "output_text", None)
    if not text:
        # Fallback in case output_text is unavailable
        try:
            text = response.output[0].content[0].text
        except Exception:
            text = "% Failed to decode OpenAI response; please fill manually.\n"
    return text.strip() + "\n"


# -------------------------------
# File generation helpers
# -------------------------------

def write_if_missing(path: Path, content: str):
    """Write content to path if it does not already exist."""
    if path.exists():
        print(f"[SKIP] {path} (already exists)")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"[OK]   Created {path}")


def generate_main_tex(root: Path):
    """Create main.tex with your book skeleton and includes for the themes + exams."""
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
        It is organized in three complementary ways:

        \begin{itemize}
          \item \emph{By topic}, following the core course outline
                (complex analysis, Fourier analysis, differential equations).
          \item \emph{By exam and problem}, collecting solved exam problems
                in dedicated chapters.
          \item \emph{By cross-reference}, via a mapping between topics and
                exam problems in the back matter.
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
        % Part III: Exams and Problem Collections
        %========================================
        \part{Exams and Problem Collections}

        % Each exam chapter can be kept in exams/examN.tex
        \include{exams/exam1}
        % TODO: add \include{{exams/exam2}}, \include{{exams/exam3}}, etc.

        %========================================
        % Back matter
        %========================================
        \backmatter

        \chapter*{Summary of Topics and Problem Map}

        Here you can keep a running list of topics, theorems, and page
        references for exam review, plus a mapping between exam problems
        and the thematic sections where they naturally belong.

        \end{document}
        """
    ).lstrip("\n")

    write_if_missing(root / "main.tex", main_tex)


def generate_theme_stub(chapter_title, subsections):
    """Return a minimal LaTeX stub for a themed chapter."""
    lines = [f"\\chapter{{{chapter_title}}}\n\n"]
    for title in subsections:
        lines.append(f"\\section{{{title}}}\n")
        lines.append(
            "% TODO (Madeline + Joel): invent an OpenAI prompt for this topic,\n"
            "% generate rough examples, and then write the curated theory,\n"
            "% problems, and solutions here.\n\n"
        )
    return "".join(lines)


def generate_theme_files(root: Path, use_openai: bool):
    """Create the themed chapter .tex files under themes/."""
    themes_dir = root / "themes"
    themes_dir.mkdir(parents=True, exist_ok=True)

    client = get_openai_client() if use_openai else None
    if use_openai and client is None:
        print("[INFO] Falling back to simple stubs for themes.")
        use_openai = False

    for spec in THEME_SPECS:
        path = themes_dir / spec["filename"]
        if path.exists():
            print(f"[SKIP] {path} (already exists)")
            continue

        if use_openai and client is not None:
            content = generate_chapter_with_openai(
                client,
                spec["chapter_title"],
                spec["subsections"],
            )
        else:
            content = generate_theme_stub(
                spec["chapter_title"],
                spec["subsections"],
            )
        write_if_missing(path, content)


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
        help="Use OpenAI API to generate mock LaTeX content for themed chapters.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Project root: {root}")

    generate_basic_dirs(root)
    generate_main_tex(root)
    generate_theme_files(root, use_openai=args.with_openai)
    generate_mock_exam(root)
    generate_makefile(root)
    generate_github_actions(root)

    print("\n[DONE] Skeleton created.")
    print("Next steps:")
    print("  - cd into the root directory and run `make` or `pdflatex main.tex`.")
    print("  - Start filling in the themed chapters in `themes/` (or re-run with --with-openai).")
    print("  - Add more exam-based chapters in `exams/` and problems under `problems/exams/`.")


if __name__ == "__main__":
    main()
