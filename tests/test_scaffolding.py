from pathlib import Path

# If you’re using conftest to add src/ to sys.path:
from init_methods_book import (
    generate_basic_dirs,
    generate_main_tex,
    generate_mock_exam,
    generate_makefile,
    generate_github_actions,
    generate_themes_with_openai,
)


def test_generate_basic_dirs_creates_expected_structure(tmp_path):
    root = tmp_path / "book"
    root.mkdir()

    generate_basic_dirs(root)

    assert (root / "figures").is_dir()
    assert (root / "problems").is_dir()
    assert (root / "problems" / "exams").is_dir()
    assert (root / "exams").is_dir()


def test_generate_main_tex_creates_file_with_core_bits_and_is_idempotent(tmp_path):
    root = tmp_path / "book"
    root.mkdir()

    # First call should create main.tex
    generate_main_tex(root)
    main_path = root / "main.tex"
    assert main_path.exists()

    content1 = main_path.read_text(encoding="utf-8")

    # Check some core structure
    assert r"\documentclass[12pt,oneside]{book}" in content1
    assert r"\include{themes/complex_analysis}" in content1
    assert r"\include{themes/fourier_analysis}" in content1
    assert r"\include{themes/ode}" in content1
    assert r"\include{themes/pde}" in content1

    # Idempotency: second call should not change the file
    generate_main_tex(root)
    content2 = main_path.read_text(encoding="utf-8")
    assert content1 == content2


def test_generate_mock_exam_creates_problem_and_exam_chapter(tmp_path):
    root = tmp_path / "book"
    root.mkdir()

    generate_mock_exam(root)

    prob_path = root / "problems" / "exams" / "exam1" / "ex1_prob01.tex"
    exam_chapter_path = root / "exams" / "exam1.tex"

    assert prob_path.exists()
    assert exam_chapter_path.exists()

    prob_content = prob_path.read_text(encoding="utf-8")
    exam_content = exam_chapter_path.read_text(encoding="utf-8")

    # Sanity checks on problem text
    assert "Exam 1, Problem 1: Warm-up ODE" in prob_content
    assert "y'(t) = -2 y(t)" in prob_content
    assert r"y(t) = e^{-2t}" in prob_content

    # Exam chapter should input that problem file
    assert r"\input{problems/exams/exam1/ex1_prob01}" in exam_content

    # Idempotent: modify the file and confirm generate_mock_exam doesn't overwrite
    prob_path.write_text("% modified\n", encoding="utf-8")
    generate_mock_exam(root)
    assert prob_path.read_text(encoding="utf-8") == "% modified\n"


def test_generate_makefile_creates_expected_targets_and_is_idempotent(tmp_path):
    root = tmp_path / "book"
    root.mkdir()

    generate_makefile(root)
    makefile_path = root / "Makefile"
    assert makefile_path.exists()

    content1 = makefile_path.read_text(encoding="utf-8")

    # Basic sanity checks
    assert "MAIN=main" in content1
    assert "pdf:" in content1
    assert "pdflatex $(MAIN).tex" in content1
    assert "clean:" in content1

    # Idempotency: second call should not overwrite user changes
    makefile_path.write_text("# user modified\n", encoding="utf-8")
    generate_makefile(root)
    content2 = makefile_path.read_text(encoding="utf-8")
    assert content2 == "# user modified\n"


def test_generate_github_actions_creates_workflow_and_is_idempotent(tmp_path):
    root = tmp_path / "book"
    root.mkdir()

    generate_github_actions(root)
    workflow_path = root / ".github" / "workflows" / "latex.yml"
    assert workflow_path.exists()

    content1 = workflow_path.read_text(encoding="utf-8")

    # Basic sanity checks on workflow
    assert "name: Build LaTeX" in content1
    assert "texlive-latex-recommended" in content1
    assert "pdflatex main.tex" in content1
    assert "upload-artifact" in content1

    # Idempotency: user modifications should be preserved
    workflow_path.write_text("# user modified workflow\n", encoding="utf-8")
    generate_github_actions(root)
    content2 = workflow_path.read_text(encoding="utf-8")
    assert content2 == "# user modified workflow\n"


def test_generate_themes_stub_without_openai_creates_chapters_and_sections(tmp_path):
    """
    This covers F3, F8 in stub mode: when OpenAI is disabled or not requested,
    themes/*.tex should be created with chapters, sections, and TODO comments.
    """
    root = tmp_path / "book"
    root.mkdir()

    # This call will create themes/ and stub chapter files
    generate_themes_with_openai(root, use_openai=False)

    themes_dir = root / "themes"
    assert themes_dir.is_dir()

    expected_files = {
        "complex_analysis.tex",
        "fourier_analysis.tex",
        "ode.tex",
        "pde.tex",
    }

    for fname in expected_files:
        path = themes_dir / fname
        assert path.exists(), f"{path} was not created"

        content = path.read_text(encoding="utf-8")
        # Should contain a chapter line
        assert r"\chapter{" in content
        # Should contain at least one section line
        assert r"\section{" in content
        # Stub should mention TODO
        assert "TODO" in content
