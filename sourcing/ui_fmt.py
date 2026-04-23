"""UI formatting helpers — escape currency so Streamlit's KaTeX doesn't interpret $ as LaTeX math mode."""
from __future__ import annotations


def usd(amount: float, precision: int = 2) -> str:
    """USD amount formatted for Streamlit markdown/metrics.

    Streamlit renders any `$...$` span as LaTeX math. A backslash in front of `$`
    escapes that behaviour, so we always emit `\\$` in user-visible strings.
    """
    return f"\\${amount:,.{precision}f}"


def esc_dollar(text: str) -> str:
    """Escape every bare `$` in a string so Streamlit doesn't turn it into LaTeX."""
    return text.replace("$", "\\$")
