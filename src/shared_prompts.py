#!/usr/bin/env python3
"""
shared_prompts.py

Shared prompt templates for the Methods Bible project.

This module centralizes:

- PREFERENCES_TEXT: your style / pedagogy preferences.
- build_plan_prompt: human-readable section planning (for interactive use).
- build_plan_json_prompt: machine-readable planning prompt (for init + parsing).
- build_inquiry_prompt: inquiry-based example prompt.
- build_solution_prompt: full-solution example prompt.
- build_example_triplet_prompt: combined inquiry+solution prompt for Batch API.
"""

from textwrap import dedent


# -------------------------------
# Global preferences block
# -------------------------------

PREFERENCES_TEXT = dedent(
    """
    I appreciate inquiry-based learning with good guidance, good hints,
    motivated examples, and starting with small cases to learn the techniques
    that are commonly used. I like crafting a narrative so one can discover
    these topics and form a thorough understanding.

    For expository solutions, I want complete and thorough explanations written
    for an undergraduate + beginning graduate audience. Use complete
    mathematical sentences and avoid excessive use of symbols. Aim for a clear,
    Chicago-style mathematical exposition.
    """
).strip()


# -------------------------------
# 1) Section-level planning prompts
# -------------------------------

def build_plan_prompt(section_name: str) -> str:
    """
    Phase 1 (interactive / human): section-level plan prompt in prose/markdown.

    This is good for manual use from prompts_for_sections.py when you just want
    to read/think about the plan, not necessarily parse JSON.
    """
    return dedent(
        f"""
        You are helping design a section of a Methods in Applied Mathematics
        textbook / problem notebook.

        SECTION TITLE: "{section_name}"

        {PREFERENCES_TEXT}

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


def build_plan_json_prompt(chapter_title: str, section_title: str) -> str:
    """
    Phase 1 (machine): section-level plan prompt with pure JSON output.

    Used by init_methods_book.py so we can json.loads() the plan for each
    section and then drive Batch generation for all examples.
    """
    return dedent(
        f"""
        You are helping design a section of a Methods in Applied Mathematics
        textbook / problem notebook.

        CHAPTER: "{chapter_title}"
        SECTION: "{section_title}"

        {PREFERENCES_TEXT}

        Produce a JSON object ONLY, with no surrounding explanation or markdown.
        The JSON MUST have the following structure:

        {{
          "section_title": <string>,
          "narrative": <string>,
          "examples": [
            {{
              "title": <string>,
              "summary": <string>,
              "teaches": <string>,
              "difficulty_variants": [<string>, ...]
            }},
            ...
          ]
        }}

        Requirements:

        - "narrative": 1–3 paragraphs (as a single string) describing:
          * what this section is about,
          * why it matters for applied math / PDEs / dynamical systems, etc.,
          * how it connects to other topics (complex analysis, Fourier, ODEs, PDEs).

        - "examples": between 3 and 7 entries.
          For each example:
          * "title": a short descriptive title (e.g. "Damped harmonic oscillator").
          * "summary": 2–4 sentences in words about the scenario / model.
          * "teaches": 1–2 sentences about the main technique or concept.
          * "difficulty_variants": 2–4 labels like "easy", "medium", "hard", "extension".

        Output ONLY valid JSON; do not include backticks, comments, or any extra text.
        """
    ).strip() + "\n"


# -------------------------------
# 2) Per-example prompts (single version)
# -------------------------------

def build_inquiry_prompt(section_name: str, example_description: str) -> str:
    """
    Phase 2: inquiry-based version of a specific example.

    This is the standalone version (non-batch) used by prompts_for_sections.py.
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

    This is the standalone version (non-batch) used by prompts_for_sections.py.
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
# 3) Batch-friendly combined prompt
# -------------------------------

def build_example_triplet_prompt(
    chapter_title: str,
    section_title: str,
    example_title: str,
    example_summary: str,
) -> str:
    """
    Combined INQUIRY + SOLUTION prompt for ONE example.

    Designed for Batch API: model returns both versions in a single response,
    separated by markers:

        %%% INQUIRY START %%%
        ... inquiry-based LaTeX ...
        %%% INQUIRY END %%%
        %%% SOLUTION START %%%
        ... problem+solution LaTeX ...
        %%% SOLUTION END %%%

    init_methods_book.py will later split these and drop into themes/*.tex.
    """
    return dedent(
        f"""
        You are helping write a Methods in Applied Mathematics textbook /
        problem notebook.

        CHAPTER: "{chapter_title}"
        SECTION: "{section_title}"
        EXAMPLE TITLE: "{example_title}"

        Informal description of the example:
        "{example_summary}"

        {PREFERENCES_TEXT}

        Produce TWO pieces of LaTeX output, clearly separated by markers:

            %%% INQUIRY START %%%
            ... inquiry-based LaTeX problem ...
            %%% INQUIRY END %%%
            %%% SOLUTION START %%%
            ... full problem + solution LaTeX ...
            %%% SOLUTION END %%%

        ------------------------------------------------------------
        PART 1: Inquiry-based version (between INQUIRY markers)
        ------------------------------------------------------------

        Requirements:

        - Output a single LaTeX environment:

              \\begin{{problem}}[{example_title}]
              % Short narrative of the physical / geometric / modeling setup.

              (a) First exploratory question...

              (b) Question that nudges the student toward the right technique...

              (c) A question that has them compute or prove a key intermediate fact...

              (d) Question that assembles the pieces into the final conclusion...

              (e) One or two "what if" / extension questions.
              \\end{{problem}}

        - Start with 2–5 sentences of motivation inside the problem.
        - Include hints for delicate steps, either as comments "% Hint: ..."
          or as "Hint: ..." after the question.
        - DO NOT include a \\begin{{solution}} here.

        ------------------------------------------------------------
        PART 2: Full solution version (between SOLUTION markers)
        ------------------------------------------------------------

        Requirements:

        - Output exactly:

              \\begin{{problem}}[{example_title}]
              ... concise, self-contained statement of the problem ...
              \\end{{problem}}

              \\begin{{solution}}
              ... full expository solution ...
              \\end{{solution}}

        - The problem statement should be shorter and exam-style, but for the
          same mathematical task as in the inquiry version.

        - The solution should:
          * be written in complete sentences, with a clear narrative thread,
          * justify key steps (but no need to expand trivial algebra),
          * point out the central ideas (e.g. phase plane, eigenvalues, resonance,
            energy, orthogonality, Green's functions, etc. as appropriate),
          * briefly mention how this example illustrates the main ideas of the
            section "{section_title}".

        IMPORTANT:
        - Do NOT wrap the output in \\documentclass or \\begin{{document}}.
        - Do NOT include the markers themselves inside LaTeX comments.
        - Output only plain text with the markers and LaTeX content.
        """
    ).strip() + "\n"
