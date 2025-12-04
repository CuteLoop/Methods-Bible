import json
from pathlib import Path

from init_methods_book import (
    parse_round_results,
    run_example_batch,
)


# -----------------------------
# Minimal mock batch responses
# -----------------------------

MOCK_BATCH_RESULT_COMPLETE = {
    "id": "batch_req_mock_0",
    "custom_id": "example::complex-analysis::analytic-functions-and-integration-along-contours::0",
    "response": {
        "status_code": 200,
        "request_id": "req_mock_0",
        "body": {
            "id": "resp_mock_0",
            "object": "response",
            "status": "completed",
            "incomplete_details": None,
            "output": [
                {
                    "id": "rs_mock_0",
                    "type": "reasoning",
                    "summary": [],
                },
                {
                    "id": "msg_mock_0",
                    "type": "message",
                    "status": "completed",
                    "content": [
                        {
                            "type": "output_text",
                            "text": {
                                "value": (
                                    "%%% INQUIRY START %%%\n"
                                    "\\begin{problem}[Direct Computation]\n"
                                    "Inquiry body here.\n"
                                    "\\end{problem}\n"
                                    "%%% INQUIRY END %%%\n"
                                    "%%% SOLUTION START %%%\n"
                                    "\\begin{problem}[Direct Computation]\n"
                                    "Problem statement.\n"
                                    "\\end{problem}\n"
                                    "\\begin{solution}\n"
                                    "Solution body here.\n"
                                    "\\end{solution}\n"
                                    "%%% SOLUTION END %%%\n"
                                )
                            },
                        }
                    ],
                },
            ],
        },
    },
    "error": None,
}

MOCK_BATCH_RESULT_INCOMPLETE_NO_SOL_END = {
    "id": "batch_req_mock_1",
    "custom_id": "example::complex-analysis::analytic-functions-and-integration-along-contours::1",
    "response": {
        "status_code": 200,
        "request_id": "req_mock_1",
        "body": {
            "id": "resp_mock_1",
            "object": "response",
            "status": "incomplete",
            "incomplete_details": {"reason": "max_output_tokens"},
            "output": [
                {
                    "id": "rs_mock_1",
                    "type": "reasoning",
                    "summary": [],
                },
                {
                    "id": "msg_mock_1",
                    "type": "message",
                    "status": "completed",
                    "content": [
                        {
                            "type": "output_text",
                            "text": {
                                "value": (
                                    "%%% INQUIRY START %%%\n"
                                    "Inquiry...\n"
                                    "%%% INQUIRY END %%%\n"
                                    "%%% SOLUTION START %%%\n"
                                    "Partial solution, but missing end marker.\n"
                                )
                            },
                        }
                    ],
                },
            ],
        },
    },
    "error": None,
}

MOCK_BATCH_RESULT_NO_RESPONSE = {
    "id": "batch_req_mock_2",
    "custom_id": "example::complex-analysis::analytic-functions-and-integration-along-contours::2",
    "response": None,
    "error": {"message": "mock error"},
}
# -----------------------------

def test_parse_round_results_marks_complete_when_all_markers_present(tmp_path):
    from src.init_methods_book import parse_round_results

    results_path = tmp_path / "results.jsonl"
    # Write a single JSONL line
    results_path.write_text(json.dumps(MOCK_BATCH_RESULT_COMPLETE) + "\n", encoding="utf-8")

    combined_text_by_id = {}
    example_state_by_id = {}

    incomplete_ids = parse_round_results(
        results_path,
        round_idx=1,
        combined_text_by_id=combined_text_by_id,
        example_state_by_id=example_state_by_id,
    )

    cid = MOCK_BATCH_RESULT_COMPLETE["custom_id"]
    assert cid in combined_text_by_id
    text = combined_text_by_id[cid]

    # All markers should be present in combined text
    assert "%%% INQUIRY START %%%" in text
    assert "%%% INQUIRY END %%%" in text
    assert "%%% SOLUTION START %%%" in text
    assert "%%% SOLUTION END %%%" in text

    # Marked as completed, no re-run needed
    assert example_state_by_id[cid]["completed"] is True
    assert example_state_by_id[cid]["incomplete_reason"] is None
    assert incomplete_ids == []


def test_parse_round_results_marks_incomplete_when_missing_solution_end(tmp_path):
    from src.init_methods_book import parse_round_results

    results_path = tmp_path / "results.jsonl"
    results_path.write_text(json.dumps(MOCK_BATCH_RESULT_INCOMPLETE_NO_SOL_END) + "\n", encoding="utf-8")

    combined_text_by_id = {}
    example_state_by_id = {}

    incomplete_ids = parse_round_results(
        results_path,
        round_idx=1,
        combined_text_by_id=combined_text_by_id,
        example_state_by_id=example_state_by_id,
    )

    cid = MOCK_BATCH_RESULT_INCOMPLETE_NO_SOL_END["custom_id"]
    assert cid in combined_text_by_id
    text = combined_text_by_id[cid]

    # Inquiry + solution start exist, but NO solution end
    assert "%%% INQUIRY START %%%" in text
    assert "%%% INQUIRY END %%%" in text
    assert "%%% SOLUTION START %%%" in text
    assert "%%% SOLUTION END %%%" not in text

    assert example_state_by_id[cid]["completed"] is False
    reason = example_state_by_id[cid]["incomplete_reason"]
    # Either the real incomplete_details dict or our fallback "markers_missing"
    assert reason is not None
    assert cid in incomplete_ids


def test_parse_round_results_handles_missing_response(tmp_path):
    from src.init_methods_book import parse_round_results

    results_path = tmp_path / "results.jsonl"
    results_path.write_text(json.dumps(MOCK_BATCH_RESULT_NO_RESPONSE) + "\n", encoding="utf-8")

    combined_text_by_id = {}
    example_state_by_id = {}

    incomplete_ids = parse_round_results(
        results_path,
        round_idx=1,
        combined_text_by_id=combined_text_by_id,
        example_state_by_id=example_state_by_id,
    )

    cid = MOCK_BATCH_RESULT_NO_RESPONSE["custom_id"]

    # No text available
    assert cid not in combined_text_by_id

    state = example_state_by_id[cid]
    assert state["completed"] is False
    assert state["status_code"] is None
    assert "reason" in state["incomplete_reason"]
    assert state["incomplete_reason"]["reason"] == "no_response"

    assert incomplete_ids == [cid]
def test_run_example_batch_single_round_complete(tmp_path, monkeypatch):
    """
    Use a fake plan with two examples and a mock results JSONL file.
    We pass client=None and max_rounds=1, so run_example_batch will
    reuse our results instead of hitting the API.
    """
    root = tmp_path / "book"
    root.mkdir()

    # --- Fake plans_by_section with two examples in the target section ---
    chapter = "Complex Analysis"
    section = "Analytic Functions and Integration along Contours"

    plans_by_section = {
        (chapter, section): {
            "narrative": "Some narrative.",
            "examples": [
                {
                    "title": "Direct Computation of a Contour Integral on a Circle",
                    "summary": "Compute z^2 around the unit circle.",
                },
                {
                    "title": "Path Independence and Analytic Primitives",
                    "summary": "Compare 2z and 1/z along different paths.",
                },
            ],
        }
    }

    # --- Prepare mock batch results file for round 1 ---
    results_path = root / "openai_examples_results.jsonl"
    with results_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(MOCK_BATCH_RESULT_COMPLETE) + "\n")
        f.write(json.dumps(MOCK_BATCH_RESULT_INCOMPLETE_NO_SOL_END) + "\n")

    # We only want a single round, so no continuation is attempted
    example_outputs = run_example_batch(
        root=root,
        client=None,         # no OpenAI client; we rely on existing results file
        plans_by_section=plans_by_section,
        max_rounds=1,
    )

    # We expect entries for indices 0 and 1 (though 1 will be incomplete)
    key0 = (chapter, section, 0)
    key1 = (chapter, section, 1)

    assert key0 in example_outputs
    ex0 = example_outputs[key0]
    assert "Direct Computation" in ex0["title"]
    assert "Inquiry body here" in ex0["inquiry"]
    assert "Solution body here" in ex0["solution"]
    # All markers must have been found for custom_id 0
    assert "%%% INQUIRY START %%%" not in ex0["inquiry"]  # strip by extract_block
    assert "%%% SOLUTION START %%%" not in ex0["solution"]

    # For example 1, markers are incomplete; our code falls back to using combined text
    assert key1 in example_outputs
    ex1 = example_outputs[key1]
    # The inquiry might be present, but solution will be raw combined text (since no SOL_END)
    # We at least assert that something came through.
    assert ex1["title"] == "Path Independence and Analytic Primitives"
    assert "Inquiry..." in (ex1["inquiry"] or ex1["solution"])
