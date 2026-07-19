"""AI analysis adapters for SJ AI Operating System.

This module keeps AI-specific code separate so Gemini can later be replaced
or cross-checked with ChatGPT, Claude, or a local model.
"""

import os

from dotenv import load_dotenv
from google import genai


DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"


def get_gemini_client() -> genai.Client:
    """Create an authenticated Gemini client.

    Input:
        None. The API key is loaded from the local .env file.
    Output:
        An authenticated Gemini API client.
    Role:
        Keep secret loading and Gemini authentication in one place.
    """
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Add it to the local .env file."
        )

    return genai.Client(api_key=api_key)


def analyze_sec_guidance(
    ticker: str,
    guidance_report: str,
    model: str = DEFAULT_GEMINI_MODEL,
) -> str:
    """Analyze official SEC guidance while separating facts and hypotheses.

    Input:
        ticker: A U.S. stock ticker.
        guidance_report: Official SEC guidance text prepared by sec_filings.py.
        model: Gemini model name.
    Output:
        Korean Markdown analysis for an Obsidian stock note.
    Role:
        Turn primary-source guidance into a structured research summary.
    """
    if not guidance_report.strip():
        raise ValueError("Guidance report cannot be empty.")

    prompt = f"""
You are the AI analysis engine for SJ AI Operating System.

Analyze only the official SEC guidance text supplied below.
Write the answer in Korean Markdown.

Required structure:
## Gemini SEC Guidance Analysis
### Confirmed facts
- Report only facts explicitly stated in the source.

### Guidance interpretation
- Explain what the guidance means for revenue, margins, expenses, and demand.
- Clearly label interpretation as inference.

### Prior-period comparison
- If prior guidance is not supplied, say that comparison cannot yet be confirmed.
- Never invent prior numbers.

### Risks and missing evidence
- List important risks, exclusions, and missing information.

Rules:
- Company-provided guidance is the primary source of truth.
- Separate confirmed facts from hypotheses.
- Do not add outside facts.
- Do not give a direct buy or sell instruction.
- Preserve important numbers and units exactly.
- Every inference must identify the exact supplied fact that supports it.
- Never guess causes such as pricing power, regional demand, or R&D spending unless explicitly stated.
- If a cause is not stated in the source, label it as unconfirmed.
- If a number's unit is unclear, do not convert or assume the unit.
- Do not compare GAAP and non-GAAP values unless both labels and periods are explicit in the source; otherwise state that comparison is unconfirmed.
Ticker: {ticker.upper()}

Official SEC guidance text:
{guidance_report}
""".strip()

    client = get_gemini_client()
    response = client.interactions.create(
        model=model,
        input=prompt,
    )
    analysis = response.output_text.strip()

    if not analysis:
        raise RuntimeError("Gemini returned an empty analysis.")

    return analysis