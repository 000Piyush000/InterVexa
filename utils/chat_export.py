"""
Renders a chat transcript to a downloadable PDF (bonus feature).
"""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

_styles = getSampleStyleSheet()

_title_style = ParagraphStyle(
    "TranscriptTitle", parent=_styles["Title"], fontSize=18, spaceAfter=4
)
_meta_style = ParagraphStyle(
    "TranscriptMeta", parent=_styles["Normal"], textColor=colors.grey, spaceAfter=16
)
_question_style = ParagraphStyle(
    "Question",
    parent=_styles["Normal"],
    fontSize=11,
    leading=15,
    textColor=colors.HexColor("#1a1a2e"),
    backColor=colors.HexColor("#eef1ff"),
    borderPadding=8,
    spaceAfter=6,
    alignment=TA_LEFT,
)
_answer_style = ParagraphStyle(
    "Answer",
    parent=_styles["Normal"],
    fontSize=11,
    leading=15,
    spaceAfter=4,
    alignment=TA_LEFT,
)
_source_style = ParagraphStyle(
    "Source",
    parent=_styles["Normal"],
    fontSize=9,
    leading=12,
    textColor=colors.HexColor("#555577"),
    leftIndent=12,
    spaceAfter=14,
)


def _escape(text):
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_chat_pdf(messages, company=None, mode=None):
    """Build a PDF transcript from a list of message dicts and return raw bytes.

    Each message dict is expected to look like:
        {"role": "user"|"assistant", "content": str, "sources": [...]}
    """
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        title="Interview Copilot Chat Transcript",
    )

    story = [Paragraph("AI Interview Copilot — Chat Transcript", _title_style)]
    meta_bits = [f"Exported {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"]
    if company:
        meta_bits.append(f"Company: {company}")
    if mode:
        meta_bits.append(f"Mode: {mode}")
    story.append(Paragraph(" | ".join(meta_bits), _meta_style))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#dddddd")))
    story.append(Spacer(1, 12))

    if not messages:
        story.append(Paragraph("No messages in this conversation yet.", _answer_style))
    else:
        for message in messages:
            role = message.get("role", "user")
            content = _escape(message.get("content", ""))
            if role == "user":
                story.append(Paragraph(f"<b>You:</b> {content}", _question_style))
            else:
                story.append(Paragraph(f"<b>Copilot:</b> {content}", _answer_style))
                sources = message.get("sources") or []
                if sources:
                    source_lines = [
                        f"{s.get('source', 'unknown')} (Chunk {s.get('chunk_id', '?')})" for s in sources
                    ]
                    story.append(
                        Paragraph("Sources: " + "; ".join(_escape(s) for s in source_lines), _source_style)
                    )
                else:
                    story.append(Spacer(1, 10))

    document.build(story)
    return buffer.getvalue()
