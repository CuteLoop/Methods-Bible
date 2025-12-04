#!/usr/bin/env python3
"""
Reusable prompt system for generating content for each Methods Bible section.

Three phases:

1. PLAN (section-level):
   - Given a section/topic name, ask for a plan of examples and subtopics.

2. INQUIRY (example-level):
   - Given a specific example description, generate an inquiry-based,
     guided, hint-rich exploration.

3. SOLUTION (example-level):
   - Given the same example description, generate a complete and thorough
     solution for an undergrad+grad audience, in clear Chicago-style
     mathematical exposition.

Usage examples:

    # Just print the PLAN prompt for a section
    python prompts_for_sections.py plan \
        --section "Phase Space Dynamics for Conservative and Perturbed Systems"

    # Actually call OpenAI and get a PLAN back (needs OPENAI_API_KEY)
    python prompts_for_sections.py plan \
        --section "Phase Space Dynamics for Conservative and Perturbed Systems" \
        --run

    # Print inquiry-based prompt for a specific example
    python prompts_for_sections.py inquiry \
        --section "Phase Space Dynamics for Conservative and Perturbed Systems" \
        --example "Damped harmonic oscillator with small nonlinear perturbation"

    # Print full-solution prompt for that example and run it
    python prompts_for_sections.py solution \
        --section "Phase Space Dynamics for Conservative and Perturbed Systems" \
        --example "Damped harmonic oscillator with small nonlinear perturbation" \
        --run
"""

import argparse
import os
from textwrap import dedent


# -------------------------------
# Optional OpenAI client
# -------------------------------

def get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[INFO] OPENAI_API_KEY not set; will only print the prompt.")
        return None
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        print("[INFO] 'openai' package not installed; run `pip install openai`.")
        return None
    return OpenAI()


def call_openai(prompt: str, model: str = "gpt-5.1-mini") -> str:
    """
    Call the OpenAI Responses API with the given prompt.
    Returns plain text output or the original prompt if something fails.
    """
    client = get_openai_client()
    if client is None:
        # No key or package: just return the prompt so user can copy-paste
        return prompt

    print(f"[INFO] Calling OpenAI with model={model} ...")
    resp = client.responses.create(
        model=model,
        input=prompt,
    )
    text = getattr(resp, "output_text", None)
    if not text:
        try:
            text = resp.output[0].content[0].text
        except Exception:
            text = "%% Failed to decode OpenAI response. Please rerun or paste the prompt manually.\n"
    return text


# -------------------------------
# Prompt templates
# -------------------------------

# Preferences block you described, reused in phase 2 & 3.
PREFERENCES_TEXT = dedent(
    """
    I appreciate inquiry-based learning with good guidance, good hints, motivated
    examples, and starting with small cases to learn the techniques that are
    commonly used. I like crafting a narrative so one can discover these topics
    and form a thorough understanding.

    For expository solutions, I want complete and thorough explanations written
    for an undergraduate + beginning graduate audience. Use complete
    mathematical sentences and avoid excessive use of symbols. Aim for a clear,
    Chicago-style mathematical exposition.
    """
).strip()


def build_plan_prompt(section_name: str) -> str:
    """
    Phase 1: section-level plan prompt.
    """
    return dedent(
        f"""
        You are helping design a section of a Methods in Applied Mathematics
        textbook / problem notebook.

        SECTION TITLE: "{section_name}"

        TASK:
        Design a *plan* for this section focused on graduate-level applied
        mathematics (with undergrad-friendly on-ramps).

        Please:

        1. Give a short narrative description (1–3 paragraphs) of:
           - What this section is about.
           - Why it matters for applied math, PDEs, asymptotics, or dynamical systems.
           - How it connects to other topics in complex analysis, Fourier analysis,
             ODEs, or PDEs.

        2. Propose **3–7 key example problems** that could be developed in this
           section. For each example:
           - Give it a short descriptive TITLE.
           - Write 2–4 sentences describing the problem idea in words.
           - Explain what main technique or concept it teaches.
           - Indicate possible "easy → medium → hard" variants.

        3. Suggest how these examples could be ordered to form a *learning
           narrative* (e.g. warm-up, core idea, refinement, edge cases).

        FORMAT:
        - Write in plain text / markdown that can be easily turned into LaTeX comments.
        - Use numbered and bulleted lists where appropriate.
        - Do *not* write the full problem statements or solutions yet; stay at the
          planning / outline level.
        """
    ).strip() + "\n"


def build_inquiry_prompt(section_name: str, example_description: str) -> str:
    """
    Phase 2: inquiry-based version of a specific example.
    """
    return dedent(
        f"""
        You are helping write an *inquiry-based* version of a worked example for
        a Methods in Applied Mathematics book.

        SECTION: "{section_name}"
        EXAMPLE (informal description):
        "{example_description}"

        {PREFERENCES_TEXT}

        GOAL FOR THIS PROMPT:
        Create a LaTeX snippet that looks like an inquiry-based worksheet, NOT
        a full solution. We will later generate a separate "complete solution"
        version.

        REQUIREMENTS:

        1. Start with a short motivational paragraph (2–5 sentences) that:
           - Explains why this example is interesting.
           - Connects it to physical or geometric intuition when appropriate.
           - Mentions which core methods or tools it will illustrate.

        2. Then write the example as a *sequence of guided steps* using a
           structure like:

               \\begin{{problem}}[Descriptive title]
               % Short narrative of the setup.

               (a) First exploratory question...

               (b) Next question that nudges the student toward the right technique...

               (c) A question that has them compute or prove a key intermediate fact...

               (d) A question that assembles the pieces into the final conclusion...

               (e) One or two "what if" or extension questions.
               \\end{{problem}}

        3. Include *hints* for the more delicate steps. Either:
           - As LaTeX comments starting with "% Hint:", or
           - As separate lines such as "Hint: ..." after the question.

        4. Start from a **simple/special case** (e.g. small dimension, simple
           potential, symmetric domain, linearized regime, etc.), and only then
           hint at how to generalize.

        5. DO NOT include the full solution here. Do not use \\begin{{solution}}
           in this prompt. This is purely the inquiry-based, guided version.

        OUTPUT FORMAT:

        - Output purely LaTeX, no surrounding \\documentclass or preamble.
        - Use:
            - \\begin{{problem}}[Title] ... \\end{{problem}}
        - Keep notation consistent and standard.
        """
    ).strip() + "\n"


def build_solution_prompt(section_name: str, example_description: str) -> str:
    """
    Phase 3: full solution / exposition for the same example.
    """
    return dedent(
        f"""
        You are helping write the *full expository solution* corresponding to a
        guided, inquiry-based example in a Methods in Applied Mathematics book.

        SECTION: "{section_name}"
        EXAMPLE (informal description):
        "{example_description}"

        {PREFERENCES_TEXT}

        We already have an inquiry-based version with scaffolded questions. Now
        we want a companion version that gives the complete worked solution and
        exposition.

        REQUIREMENTS:

        1. Produce a LaTeX snippet of the form:

               \\begin{{problem}}[Descriptive title]
               ... (concise statement of the problem) ...
               \\end{{problem}}

               \\begin{{solution}}
               ... full solution ...
               \\end{{solution}}

        2. The *problem statement* should be:
           - Clear and self-contained.
           - Shorter and more polished than the inquiry version (just the final
             task, not all intermediate questions).
           - Suitable for an exam or textbook problem.

        3. The *solution* should:
           - Be written in complete sentences, with a clear narrative thread.
           - Carefully justify each step, but without getting bogged down in
             trivial algebra unless it teaches something.
           - Point out the key ideas: where we use linearity, orthogonality,
             conservation laws, fixed-point arguments, asymptotic expansions,
             phase portraits, etc., depending on the example.
           - When appropriate, comment briefly on alternative approaches or
             common pitfalls.

        4. Style:
           - Exposition suitable for an advanced undergraduate or beginning
             graduate student in applied mathematics.
           - Avoid excessive symbolism; prefer words + standard notation.
           - Mention briefly how this example connects to the larger theme of
             the section "{section_name}".

        5. OUTPUT FORMAT:
           - Pure LaTeX, no preamble, no \\documentclass.
           - Exactly one \\begin{{problem}}...\\end{{problem}} and one
             \\begin{{solution}}...\\end{{solution}} block.
        """
    ).strip() + "\n"


# -------------------------------
# CLI
# -------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Three-phase prompt system for Methods Bible sections."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Phase 1: plan
    plan_p = subparsers.add_parser(
        "plan",
        help="Generate a planning prompt (or run it) for a given section/topic.",
    )
    plan_p.add_argument(
        "--section",
        required=True,
        help="Section / topic name (e.g. 'Phase Space Dynamics for Conservative and Perturbed Systems').",
    )
    plan_p.add_argument(
        "--run",
        action="store_true",
        help="If set, call OpenAI and print the generated plan instead of the raw prompt.",
    )

    # Phase 2: inquiry
    inq_p = subparsers.add_parser(
        "inquiry",
        help="Generate an inquiry-based prompt (or run it) for a specific example.",
    )
    inq_p.add_argument(
        "--section",
        required=True,
        help="Section / topic name.",
    )
    inq_p.add_argument(
        "--example",
        required=True,
        help="Short description of the example (in words).",
    )
    inq_p.add_argument(
        "--run",
        action="store_true",
        help="If set, call OpenAI and print the generated inquiry-based LaTeX.",
    )

    # Phase 3: solution
    sol_p = subparsers.add_parser(
        "solution",
        help="Generate a full-solution prompt (or run it) for a specific example.",
    )
    sol_p.add_argument(
        "--section",
        required=True,
        help="Section / topic name.",
    )
    sol_p.add_argument(
        "--example",
        required=True,
        help="Short description of the example (in words).",
    )
    sol_p.add_argument(
        "--run",
        action="store_true",
        help="If set, call OpenAI and print the generated solution LaTeX.",
    )

    args = parser.parse_args()

    if args.command == "plan":
        prompt = build_plan_prompt(args.section)
        if args.run:
            output = call_openai(prompt)
        else:
            output = prompt
        print(output)

    elif args.command == "inquiry":
        prompt = build_inquiry_prompt(args.section, args.example)
        if args.run:
            output = call_openai(prompt)
        else:
            output = prompt
        print(output)

    elif args.command == "solution":
        prompt = build_solution_prompt(args.section, args.example)
        if args.run:
            output = call_openai(prompt)
        else:
            output = prompt
        print(output)


if __name__ == "__main__":
    main()
