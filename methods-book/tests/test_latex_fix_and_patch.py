# tests/test_latex_fix_and_patch.py
from pathlib import Path
import textwrap

import pytest

from tools.latex_scan_regions import Region
from tools.latex_fix_and_patch import apply_fixes_to_files


def test_apply_fixes_replaces_region_only(tmp_path: Path):
    """
    Apply a fix to a small region and check that only the intended lines changed.
    """
    project_root = tmp_path
    tex = project_root / "themes" / "pde.tex"
    tex.parent.mkdir(parents=True, exist_ok=True)

    # 1-based line numbers:
    # 1: before
    # 2: bad
    # 3: after
    tex.write_text(
        textwrap.dedent(
            r"""
            Before line
            Bad math: \alpha + 1]
            After line
            """
        ).lstrip("\n"),
        encoding="utf-8",
    )

    # Region covering only line 2
    region = Region(
        file=tex,
        error_line=2,
        start_line=2,
        end_line=2,
        snippet="Bad math: \\alpha + 1]\n",
    )

    def fake_fixer(r: Region) -> str:
        # Simulate ChatGPT “fixing” by adding missing '$' and bracket.
        assert "Bad math" in r.snippet
        return "Bad math: $\\alpha + 1$.\n"

    apply_fixes_to_files([region], fake_fixer, project_root)

    new_contents = tex.read_text(encoding="utf-8").splitlines()
    assert new_contents[0] == "Before line"
    assert new_contents[1] == "Bad math: $\\alpha + 1$."
    assert new_contents[2] == "After line"


def test_apply_fixes_multiple_files(tmp_path: Path):
    """
    Apply fixes to regions in different files, ensure each file is updated correctly.
    """
    project_root = tmp_path
    pde = project_root / "themes" / "pde.tex"
    ca = project_root / "themes" / "complex_analysis.tex"
    pde.parent.mkdir(parents=True, exist_ok=True)

    pde.write_text("pde header\nbad pde\npde footer\n", encoding="utf-8")
    ca.write_text("ca header\nbad ca\nca footer\n", encoding="utf-8")

    regions = [
        Region(
            file=pde,
            error_line=2,
            start_line=2,
            end_line=2,
            snippet="bad pde\n",
        ),
        Region(
            file=ca,
            error_line=2,
            start_line=2,
            end_line=2,
            snippet="bad ca\n",
        ),
    ]

    def fake_fixer(r: Region) -> str:
        if r.file.name == "pde.tex":
            return "fixed pde\n"
        else:
            return "fixed ca\n"

    apply_fixes_to_files(regions, fake_fixer, project_root)

    assert "fixed pde" in pde.read_text(encoding="utf-8")
    assert "fixed ca" in ca.read_text(encoding="utf-8")
    assert "bad pde" not in pde.read_text(encoding="utf-8")
    assert "bad ca" not in ca.read_text(encoding="utf-8")


def test_apply_fixes_preserves_unrelated_lines(tmp_path: Path):
    """
    If the region is in the middle of a larger file, everything outside
    start..end must remain byte-for-byte identical.
    """
    project_root = tmp_path
    tex = project_root / "themes" / "ode.tex"
    tex.parent.mkdir(parents=True, exist_ok=True)

    original_lines = [
        "line 1\n",
        "line 2\n",
        "bad line 3\n",
        "line 4\n",
        "line 5\n",
    ]
    tex.write_text("".join(original_lines), encoding="utf-8")

    region = Region(
        file=tex,
        error_line=3,
        start_line=3,
        end_line=3,
        snippet="bad line 3\n",
    )

    def fake_fixer(r: Region) -> str:
        return "good line 3\n"

    apply_fixes_to_files([region], fake_fixer, project_root)

    new_lines = tex.read_text(encoding="utf-8").splitlines(keepends=True)
    assert new_lines[0] == original_lines[0]
    assert new_lines[1] == original_lines[1]
    assert new_lines[2] == "good line 3\n"
    assert new_lines[3] == original_lines[3]
    assert new_lines[4] == original_lines[4]


def test_apply_fixes_overlapping_regions_order_independent(tmp_path: Path):
    """
    If two regions overlap, the algorithm should either:
      - merge them before fixing, or
      - apply them in a way that the final result is consistent.
    Here we simulate two overlapping fixes; final file must contain both changes.
    """
    project_root = tmp_path
    tex = project_root / "themes" / "pde.tex"
    tex.parent.mkdir(parents=True, exist_ok=True)

    tex.write_text(
        "a = b + c]\n"  # line 1
        "d = e + f]\n",  # line 2
        encoding="utf-8",
    )

    regions = [
        Region(
            file=tex,
            error_line=1,
            start_line=1,
            end_line=1,
            snippet="a = b + c]\n",
        ),
        Region(
            file=tex,
            error_line=2,
            start_line=2,
            end_line=2,
            snippet="d = e + f]\n",
        ),
    ]

    def fake_fixer(r: Region) -> str:
        # rudely fix the ']' into ');'
        return r.snippet.replace("]", ");")

    apply_fixes_to_files(regions, fake_fixer, project_root)

    contents = tex.read_text(encoding="utf-8").splitlines()
    assert contents[0] == "a = b + c);"
    assert contents[1] == "d = e + f);"
