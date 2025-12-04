# tests/test_init_methods_book.py

import json
from pathlib import Path

import pytest

from init_methods_book import (
    slugify,
    extract_block,
    write_if_missing,
    extract_output_text_from_response_obj,
    generate_basic_dirs,
    generate_main_tex,
    generate_mock_exam,
    generate_makefile,
    generate_github_actions,
)


# -----------------------------
# slugify
# -----------------------------

def test_slugify_basic():
    text = "Complex Variables and Complex-valued Functions"
    s = slugify(text)
    assert s == "complex-variables-and-complex-valued-functions"


def test_slugify_collapse_non_alnum_and_trim():
    text = "  Waves in a Homogeneous Medium: Hyperbolic PDE (*)  "
    s = slugify(text)
    # No leading/trailing hyphens, no multiple hyphens
    assert s == "waves-in-a-homogeneous-medium-hyperbolic-pde"


def test_slugify_empty_fallback():
    # If everything is stripped out, we should get "section"
    text = "   !!! ###   "
    s = slugify(text)
    assert s == "section"


# -----------------------------
# extract_block
# -----------------------------

def test_extract_block_happy_path():
    full = (
        "prefix\n"
        "%%% INQUIRY START %%%\n"
        "Here is the inquiry.\nLine two.\n"
        "%%% INQUIRY END %%%\n"
        "suffix\n"
    )
    block = extract_block(full, "%%% INQUIRY START %%%", "%%% INQUIRY END %%%")
    assert "Here is the inquiry." in block
    assert "Line two." in block
    # No markers inside the result
    assert "INQUIRY START" not in block
    assert "INQUIRY END" not in block


def test_extract_block_missing_markers_returns_empty():
    full = "No markers here at all."
    block = extract_block(full, "%%% INQUIRY START %%%", "%%% INQUIRY END %%%")
    assert block == ""


# -----------------------------
# write_if_missing
# -----------------------------

def test_write_if_missing_creates_file(tmp_path: Path):
    target = tmp_path / "foo.txt"
    assert not target.exists()

    write_if_missing(target, "hello world")
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "hello world"


def test_write_if_missing_is_idempotent(tmp_path: Path, capsys):
    target = tmp_path / "foo.txt"

    # First write
    write_if_missing(target, "first")
    first_content = target.read_text(encoding="utf-8")

    # Second call should *not* overwrite
    write_if_missing(target, "second")
    second_content = target.read_text(encoding="utf-8")

    assert first_content == second_content == "first"

    # Optional: check that the second call reported SKIP (not required, but nice)
    captured = capsys.readouterr().out
    assert "[SKIP]" in captured


# -----------------------------
# extract_output_text_from_response_obj
# -----------------------------

def test_extract_output_text_from_response_obj_basic():
    """
    Minimal body structure like what Batch 'body' would contain.
    """
    body = {
        "output": [
            {
                "content": [
                    {
                        "type": "output_text",
                        "text": {"value": "Hello world"},
                    }
                ]
            }
        ]
    }

    txt = extract_output_text_from_response_obj(body)
    assert txt == "Hello world"


def test_extract_output_text_from_response_obj_concatenates_multiple_chunks():
    body = {
        "output": [
            {
                "content": [
                    {
                        "type": "output_text",
                        "text": {"value": "Line 1"},
                    },
                    {
                        "type": "output_text",
                        "text": {"value": "Line 2"},
                    },
                    {
                        # Non-text content should be ignored
                        "type": "tool_call",
                        "text": {"value": "SHOULD NOT APPEAR"},
                    },
                ]
            }
        ]
    }

    txt = extract_output_text_from_response_obj(body)
    # They should be joined with newlines by the helper
    assert "Line 1" in txt
    assert "Line 2" in txt
    assert "SHOULD NOT APPEAR" not in txt


def test_extract_output_text_from_response_obj_handles_plain_string_text():
    body = {
        "output": [
            {
                "content": [
                    {
                        "type": "output_text",
                        "text": "Plain string text",
                    }
                ]
            }
        ]
    }

    txt = extract_output_text_from_response_obj(body)
    assert txt == "Plain string text"


def test_extract_output_text_from_response_obj_robust_to_missing_output():
    body = {
        # No "output" key
    }
    txt = extract_output_text_from_response_obj(body)
    assert txt == ""


def test_extract_output_text_from_response_obj_robust_to_non_list_output():
    body = {
        "output": {"not": "a list"},
    }
    txt = extract_output_text_from_response_obj(body)
    assert txt == ""
