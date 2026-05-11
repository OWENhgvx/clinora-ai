"""
export.py — PDF report generation for Clinora
Builds a structured medical report using reportlab
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── colour palette ───────────────────────────────────────────
CYAN   = colors.HexColor("#22d3ee")
PURPLE = colors.HexColor("#a78bfa")
ORANGE = colors.HexColor("#fb923c")
DARK   = colors.HexColor("#0f172a")
SLATE  = colors.HexColor("#475569")
LIGHT  = colors.HexColor("#e2e8f0")
WHITE  = colors.white
YELLOW = colors.HexColor("#fbbf24")
RED    = colors.HexColor("#f87171")
GREEN  = colors.HexColor("#4ade80")


def _styles():
    base = getSampleStyleSheet()
    s = {}

    s["title"] = ParagraphStyle("mc_title",
        fontSize=22, textColor=DARK, leading=28,
        fontName="Helvetica-Bold", spaceAfter=4)

    s["subtitle"] = ParagraphStyle("mc_sub",
        fontSize=11, textColor=SLATE, leading=16,
        fontName="Helvetica", spaceAfter=16)

    s["section"] = ParagraphStyle("mc_section",
        fontSize=9, textColor=CYAN, leading=12,
        fontName="Helvetica-Bold", spaceBefore=18, spaceAfter=6,
        letterSpacing=1.5)

    s["body"] = ParagraphStyle("mc_body",
        fontSize=9.5, textColor=DARK, leading=15,
        fontName="Helvetica", spaceAfter=4)

    s["mono"] = ParagraphStyle("mc_mono",
        fontSize=8.5, textColor=colors.HexColor("#1e293b"), leading=13,
        fontName="Courier", spaceAfter=3)

    s["agent_diag"] = ParagraphStyle("mc_agent_diag",
        fontSize=8.5, textColor=colors.HexColor("#0f172a"), leading=13,
        fontName="Courier", spaceAfter=3)

    s["label"] = ParagraphStyle("mc_label",
        fontSize=7.5, textColor=SLATE, leading=10,
        fontName="Helvetica-Bold", spaceAfter=2,
        letterSpacing=1)

    s["val"] = ParagraphStyle("mc_val",
        fontSize=9.5, textColor=DARK, leading=14,
        fontName="Helvetica", spaceAfter=0)

    s["ref_title"] = ParagraphStyle("mc_ref_title",
        fontSize=9, textColor=DARK, leading=13,
        fontName="Helvetica-Bold", spaceAfter=2)

    s["ref_meta"] = ParagraphStyle("mc_ref_meta",
        fontSize=8, textColor=SLATE, leading=12,
        fontName="Helvetica", spaceAfter=2)

    s["ref_excerpt"] = ParagraphStyle("mc_ref_excerpt",
        fontSize=8, textColor=colors.HexColor("#334155"), leading=12,
        fontName="Helvetica", spaceAfter=3)

    s["warning"] = ParagraphStyle("mc_warning",
        fontSize=8.5, textColor=colors.HexColor("#92400e"), leading=13,
        fontName="Helvetica", spaceAfter=0)

    s["chat_patient"] = ParagraphStyle("mc_chat_patient",
        fontSize=8.5, textColor=colors.HexColor("#0369a1"), leading=13,
        fontName="Helvetica-Bold", spaceAfter=1)

    s["chat_ai"] = ParagraphStyle("mc_chat_ai",
        fontSize=8.5, textColor=colors.HexColor("#374151"), leading=13,
        fontName="Helvetica", spaceAfter=1)

    s["chat_label"] = ParagraphStyle("mc_chat_label",
        fontSize=7, textColor=SLATE, leading=9,
        fontName="Helvetica-Bold", spaceAfter=2, letterSpacing=1)

    return s


def _severity_color(n):
    if isinstance(n, str):
        lv = n.strip().lower()
        if lv == "mild":
            return GREEN
        if lv == "moderate":
            return YELLOW
        if lv == "severe":
            return RED
        n = 5
    if n <= 3: return GREEN
    if n <= 6: return YELLOW
    if n <= 8: return ORANGE
    return RED


def _severity_label(n) -> str:
    if isinstance(n, str):
        lv = n.strip().lower()
        if lv == "mild":
            return "Mild"
        if lv == "moderate":
            return "Moderate"
        if lv == "severe":
            return "Severe"
        n = 5
    if n <= 3: return "Mild"
    if n <= 5: return "Moderate"
    if n <= 7: return "Significant"
    if n <= 9: return "Severe"
    return "Critical"


def _header_footer(canvas, doc):
    """Draw the header and footer on every page."""
    canvas.saveState()
    w, h = A4

    # header
    canvas.setFillColor(DARK)
    canvas.rect(0, h - 30*mm, w, 30*mm, fill=True, stroke=False)
    canvas.setFillColor(CYAN)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(20*mm, h - 16*mm, "⚕  MEDICHAIN")
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(20*mm, h - 23*mm, "AI Diagnostic Report  ·  Educational Use Only")
    canvas.setFillColor(colors.HexColor("#334155"))
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(w - 20*mm, h - 16*mm,
        datetime.now().strftime("%d %b %Y  %H:%M"))
    canvas.drawRightString(w - 20*mm, h - 23*mm,
        f"Page {doc.page}")

    # footer
    canvas.setFillColor(colors.HexColor("#f1f5f9"))
    canvas.rect(0, 0, w, 14*mm, fill=True, stroke=False)
    canvas.setFillColor(SLATE)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(w/2, 5*mm,
        "This report is generated by Clinora for educational and research purposes only. "
        "It does not constitute medical advice. Always consult a qualified healthcare professional.")

    canvas.restoreState()


def generate_pdf(session: dict) -> bytes:
    """
    Build a complete diagnostic report PDF from session data.
    Returns raw bytes.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=36*mm, bottomMargin=20*mm,
    )

    s = _styles()
    story = []
    symptoms = session.get("symptoms", {})
    diagnosis = session.get("diagnosis", "")
    review    = session.get("review", "")
    refs      = session.get("refs", [])
    messages  = session.get("messages", [])
    created   = session.get("created_at", datetime.utcnow().isoformat())

    # ── 1. cover title ──────────────────────────────────────
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph("Diagnostic Report", s["title"]))
    story.append(Paragraph(
        f"Session ID: {session.get('id','N/A')[:8]}…  ·  "
        f"Generated: {datetime.fromisoformat(created).strftime('%d %b %Y, %H:%M UTC')}",
        s["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=CYAN, spaceAfter=12))

    # ── 2. case summary card ────────────────────────────────
    story.append(Paragraph("PATIENT CASE SUMMARY", s["section"]))

    sev = symptoms.get("severity_level") or symptoms.get("severity", 0)
    summary_data = [
        [
            _lv("CHIEF COMPLAINT", symptoms.get("description","—"), s),
            _lv("BODY AREA", symptoms.get("bodyPart","—"), s),
        ],
        [
            _lv("DURATION", symptoms.get("duration","—"), s),
            _lv("SEVERITY",
                _severity_label(sev), s,
                val_color=_severity_color(sev)),
        ],
        [
            _lv("MEDICAL HISTORY / MEDICATIONS",
                symptoms.get("notes","None provided") or "None provided", s),
            _lv("AGENT PIPELINE",
                "Interviewer → Diagnostician → Critic (RAG-grounded)", s),
        ],
    ]

    tbl = Table(summary_data, colWidths=["50%", "50%"])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,-1), colors.HexColor("#f8fafc")),
        ("ROWBACKGROUNDS", (0,0),(-1,-1),
            [colors.HexColor("#f8fafc"), colors.HexColor("#f1f5f9")]),
        ("BOX",         (0,0),(-1,-1), 1, colors.HexColor("#e2e8f0")),
        ("INNERGRID",   (0,0),(-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN",      (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",  (0,0),(-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("LEFTPADDING", (0,0),(-1,-1), 10),
        ("RIGHTPADDING",(0,0),(-1,-1), 10),
    ]))
    story.append(tbl)

    # ── 3. diagnosis results ────────────────────────────────
    story.append(Spacer(1, 4*mm))
    story.append(_agent_header("🔬  DIAGNOSTIC AGENT OUTPUT", PURPLE, s))
    story.append(Spacer(1, 2*mm))

    if diagnosis:
        for line in diagnosis.split("\n"):
            line = line.rstrip()
            if not line:
                story.append(Spacer(1, 2))
                continue
            if line.startswith("## "):
                story.append(Spacer(1, 4))
                story.append(Paragraph(line[3:].upper(), s["section"]))
            elif line.startswith("# "):
                story.append(Paragraph(line[2:], s["section"]))
            else:
                clean = line.replace("**", "").replace("*", "")
                story.append(Paragraph(clean, s["agent_diag"]))
    else:
        story.append(Paragraph("No diagnostic output available.", s["body"]))

    # ── 4. critic review ────────────────────────────────────
    story.append(PageBreak())
    story.append(_agent_header("⚖️  CRITIC AGENT REVIEW", ORANGE, s))
    story.append(Spacer(1, 2*mm))

    if review:
        for line in review.split("\n"):
            line = line.rstrip()
            if not line:
                story.append(Spacer(1, 2))
                continue
            if line.startswith("## "):
                story.append(Spacer(1, 4))
                story.append(Paragraph(line[3:].upper(), s["section"]))
            elif "CRITICAL" in line or "⚠" in line:
                story.append(Paragraph(
                    line.replace("**","").replace("*",""),
                    ParagraphStyle("mc_crit", parent=s["body"],
                        textColor=RED, fontName="Helvetica-Bold")))
            elif "APPROVED" in line:
                story.append(Paragraph(
                    line.replace("**","").replace("*",""),
                    ParagraphStyle("mc_appr", parent=s["body"],
                        textColor=GREEN, fontName="Helvetica-Bold")))
            else:
                clean = line.replace("**", "").replace("*", "")
                story.append(Paragraph(clean, s["agent_diag"]))
    else:
        story.append(Paragraph("No critic review available.", s["body"]))

    # ── 5. RAG references ───────────────────────────────────
    if refs:
        story.append(PageBreak())
        story.append(Paragraph("📚  RAG MEDICAL LITERATURE REFERENCES", s["section"]))
        story.append(Paragraph(
            f"{len(refs)} articles retrieved from PubMed via ChromaDB semantic search.",
            s["body"]))
        story.append(Spacer(1, 3*mm))

        for i, ref in enumerate(refs, 1):
            ref_data = [[
                Paragraph(f"[{i}]", ParagraphStyle("rn", parent=s["ref_title"],
                    textColor=PURPLE, fontSize=10)),
                [
                    Paragraph(ref.get("title",""), s["ref_title"]),
                    Paragraph(
                        f"{ref.get('authors','')}  ·  {ref.get('year','')}  ·  {ref.get('source','')}",
                        s["ref_meta"]),
                    Paragraph(ref.get("excerpt",""), s["ref_excerpt"]),
                    Paragraph(ref.get("url",""), ParagraphStyle("url",
                        parent=s["ref_meta"], textColor=CYAN)),
                ],
                Paragraph(f"Score\n{ref.get('score','')}", ParagraphStyle("score",
                    parent=s["label"], textColor=PURPLE, alignment=TA_RIGHT)),
            ]]
            rt = Table(ref_data, colWidths=[8*mm, None, 18*mm])
            rt.setStyle(TableStyle([
                ("VALIGN",      (0,0),(-1,-1), "TOP"),
                ("TOPPADDING",  (0,0),(-1,-1), 6),
                ("BOTTOMPADDING",(0,0),(-1,-1), 6),
                ("LEFTPADDING", (0,0),(-1,-1), 4),
                ("BACKGROUND",  (0,0),(-1,-1),
                    colors.HexColor("#faf5ff") if i%2==0 else WHITE),
                ("BOX",         (0,0),(-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ]))
            story.append(rt)
            story.append(Spacer(1, 1*mm))

    # ── 6. conversation transcript ──────────────────────────
    if messages:
        story.append(PageBreak())
        story.append(Paragraph("💬  CONSULTATION TRANSCRIPT", s["section"]))
        story.append(Spacer(1, 3*mm))

        for msg in messages:
            role = msg.get("role","")
            text = msg.get("text","")
            if not text:
                continue

            if role == "user":
                story.append(Paragraph("PATIENT", s["chat_label"]))
                story.append(Paragraph(text, s["chat_patient"]))
            else:
                agent = msg.get("agent","ai")
                agent_label = {
                    "interviewer":  "INTERVIEWER AGENT",
                    "diagnostician":"DIAGNOSTIC AGENT",
                    "critic":       "CRITIC AGENT",
                    "safety":       "SAFETY AGENT",
                }.get(agent, "AGENT")
                story.append(Paragraph(agent_label, s["chat_label"]))
                story.append(Paragraph(text[:600]+("…" if len(text)>600 else ""), s["chat_ai"]))

            story.append(Spacer(1, 2*mm))
            story.append(HRFlowable(width="100%", thickness=0.3,
                color=colors.HexColor("#e2e8f0"), spaceAfter=2))

    # ── 7. disclaimer ───────────────────────────────────────
    story.append(Spacer(1, 6*mm))
    disc_data = [[
        Paragraph(
            "<b>⚠ DISCLAIMER:</b> This AI-generated report is produced by Clinora, "
            "a research prototype developed at UNSW Sydney (COMP9900). It is intended "
            "for educational and research purposes ONLY. This report does NOT constitute "
            "medical advice, diagnosis, or treatment. Always seek the advice of a qualified "
            "healthcare professional for any medical condition. In case of emergency, "
            "call 000 (Australia) or your local emergency services immediately.",
            s["warning"])
    ]]
    dt = Table(disc_data, colWidths=["100%"])
    dt.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,-1), colors.HexColor("#fffbeb")),
        ("BOX",         (0,0),(-1,-1), 1, YELLOW),
        ("TOPPADDING",  (0,0),(-1,-1), 10),
        ("BOTTOMPADDING",(0,0),(-1,-1), 10),
        ("LEFTPADDING", (0,0),(-1,-1), 12),
        ("RIGHTPADDING",(0,0),(-1,-1), 12),
    ]))
    story.append(dt)

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buf.getvalue()


# ── helpers ───────────────────────────────────────────────

def _lv(label: str, value: str, s: dict, val_color=None) -> list:
    """Render a label + value cell pair."""
    val_style = s["val"]
    if val_color:
        val_style = ParagraphStyle("mc_val_c", parent=s["val"], textColor=val_color,
                                   fontName="Helvetica-Bold")
    return [
        Paragraph(label, s["label"]),
        Paragraph(str(value), val_style),
    ]


def _agent_header(title: str, color, s: dict):
    """Render an agent section header block."""
    data = [[Paragraph(title, ParagraphStyle("ah",
        fontSize=9, textColor=WHITE, fontName="Helvetica-Bold",
        leading=13, letterSpacing=1))]]
    t = Table(data, colWidths=["100%"])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), color),
        ("TOPPADDING",   (0,0),(-1,-1), 7),
        ("BOTTOMPADDING",(0,0),(-1,-1), 7),
        ("LEFTPADDING",  (0,0),(-1,-1), 12),
        ("RIGHTPADDING", (0,0),(-1,-1), 12),
    ]))
    return t
