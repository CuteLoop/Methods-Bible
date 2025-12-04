# tests/test_latex_scan_regions.py
import textwrap
from pathlib import Path

import pytest

from latex_scan_regions import collect_problem_regions, Region


def test_collect_single_error_with_file_and_line(tmp_path: Path):
    """
    Simple sanity check: one error in themes/pde.tex, verify that
    - we get exactly one Region
    - file is resolved correctly
    - start/end window is symmetric around error_line
    - snippet actually contains the bad line
    """
    project_root = tmp_path

    # Create a small fake pde.tex with 30 lines
    pde_path = project_root / "themes" / "pde.tex"
    pde_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"% line {i}\n" for i in range(1, 31)]
    # Insert a “bad” line at 20
    lines[19] = r"This is bad math: \alpha + 1]" + "\n"
    pde_path.write_text("".join(lines), encoding="utf-8")

    # Fake LaTeX log snippet like the real one
    log_text = textwrap.dedent(
        r"""
        (./themes/pde.tex
        ! Missing $ inserted.
        <inserted text> 
                    $
        l.20 This is bad math: \alpha + 1]
        ) (./themes/ode.tex
        """
    )

    regions = collect_problem_regions(log_text, project_root, context_lines=3)
    assert len(regions) == 1

    region = regions[0]
    assert isinstance(region, Region)
    assert region.file == pde_path
    assert region.error_line == 20
    # 3 lines context -> 17..23
    assert region.start_line == 17
    assert region.end_line == 23
    # snippet lines are 17..23 inclusive
    snippet_lines = region.snippet.splitlines()
    assert len(snippet_lines) == 7
    # Contains the problematic content
    assert "This is bad math: \\alpha + 1]" in region.snippet


def test_collect_multiple_errors_different_files(tmp_path: Path):
    """
    Two different files with errors should produce two regions with correct file mapping.
    """
    project_root = tmp_path

    # fake files
    pde_path = project_root / "themes" / "pde.tex"
    ca_path = project_root / "themes" / "complex_analysis.tex"
    pde_path.parent.mkdir(parents=True, exist_ok=True)

    pde_path.write_text(
        "% pde header\n" * 5 + "pde bad line\n" + "% pde footer\n" * 5,
        encoding="utf-8",
    )
    ca_path.write_text(
        "% ca header\n" * 5 + "ca bad line\n" + "% ca footer\n" * 5,
        encoding="utf-8",
    )

    log_text = textwrap.dedent(
        r"""
        (./themes/pde.tex
        ! Missing $ inserted.
        <inserted text> 
                    $
        l.6 pde bad line
        ) (./themes/complex_analysis.tex
        ! Package amsmath: \begin{aligned} allowed only in math mode.
        l.6 ca bad line
        )
        """
    )

    regions = collect_problem_regions(log_text, project_root, context_lines=2)
    assert len(regions) == 2

    files = {r.file for r in regions}
    assert files == {pde_path, ca_path}

    pde_region = next(r for r in regions if r.file == pde_path)
    ca_region = next(r for r in regions if r.file == ca_path)

    assert "pde bad line" in pde_region.snippet
    assert "ca bad line" in ca_region.snippet


def test_collect_default_to_main_when_no_file(tmp_path: Path):
    """
    If the log doesn't give a file path before an error, the scanner should
    default to main.tex.
    """
    project_root = tmp_path
    main_path = project_root / "main.tex"
    main_path.write_text(
        "% main header\n" * 3 + "main bad line\n" + "% main footer\n" * 3,
        encoding="utf-8",
    )

    log_text = textwrap.dedent(
        r"""
        ! Bad math environment delimiter.
        l.4 main bad line
        """
    )

    regions = collect_problem_regions(log_text, project_root, context_lines=1)
    assert len(regions) == 1
    r = regions[0]
    assert r.file == main_path
    assert "main bad line" in r.snippet


def test_overlapping_errors_same_file_merge_or_keep(tmp_path: Path):
    """
    Robustness: if two errors are within the same context window, the scanner
    may either:
      - return two overlapping regions, or
      - merge them into a single region.
    Either behavior is acceptable as long as all bad lines are covered.
    """
    project_root = tmp_path
    pde = project_root / "themes" / "pde.tex"
    pde.parent.mkdir(parents=True, exist_ok=True)
    contents = "\n".join(
        [
            "% line 1",
            "line 2",
            "bad line 3",
            "bad line 5",
            "line 6",
        ]
    )
    pde.write_text(contents + "\n", encoding="utf-8")

    log_text = textwrap.dedent(
        r"""
        (./themes/pde.tex
        ! Missing $ inserted.
        l.3 bad line 3
        ! Missing $ inserted.
        l.4 bad line 5
        )
        """
    )

    regions = collect_problem_regions(log_text, project_root, context_lines=1)
    assert len(regions) in (1, 2)

    combined = "\n".join(r.snippet for r in regions)
    assert "bad line 3" in combined
    assert "bad line 5" in combined
