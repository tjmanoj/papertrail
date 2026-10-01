"""Builds the PaperTrail submission deck inside the official hackathon template.

Rules enforced here after the first attempt overflowed its boxes:
  * every text block gets a box sized from a measured line estimate, so text
    cannot run past its container
  * one idea per slide, short lines, generous whitespace
  * the architecture slide is a drawn diagram with real arrows, not a wall of text
  * Arial everywhere (the template carries Manrope, absent on stock macOS)
  * no em dashes anywhere in the output
"""
import math
from pptx import Presentation
from pptx.util import Emu, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.oxml.ns import qn

SRC = "template.pptx"
OUT = "PaperTrail-Provenance-Prototype-Submission.pptx"

EMU_IN = 914400
SLIDE_W, SLIDE_H = 9144000, 5143500
MARGIN = 470000
BODY_W = SLIDE_W - 2 * MARGIN
TOP = 600000
FLOOR = 4930000

INK = RGBColor(0x0F, 0x18, 0x29)
INK2 = RGBColor(0x46, 0x57, 0x70)
MUTED = RGBColor(0x8A, 0x99, 0xAD)
CYAN = RGBColor(0x0C, 0x7F, 0xAA)
CYAN_B = RGBColor(0x29, 0xB5, 0xE8)
NAVY = RGBColor(0x0E, 0x16, 0x24)
CRIT = RGBColor(0xB1, 0x2B, 0x2B)
SOFT = RGBColor(0xF3, 0xF6, 0xFA)
LINE = RGBColor(0xD8, 0xE0, 0xEA)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

prs = Presentation(SRC)


def est_height(text, size_pt, width_emu, pad=160000):
    cpl = max(12, int((width_emu / EMU_IN) * (96 / (size_pt * 0.50))))
    lines = sum(max(1, math.ceil(len(p) / cpl)) for p in text.split("\n"))
    return int(lines * size_pt * 1.30 * (EMU_IN / 72)) + pad


def write(tf, blocks, *, size=12, color=INK2, bold=False, align=PP_ALIGN.LEFT,
          space=5, line=None):
    tf.word_wrap = True
    first = True
    for b in blocks:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = align
        p.space_after = Pt(space)
        if line:
            p.line_spacing = line
        for text, ov in ([(b, {})] if isinstance(b, str) else b):
            r = p.add_run()
            r.text = text
            r.font.name = "Arial"
            r.font.size = Pt(ov.get("size", size))
            r.font.bold = ov.get("bold", bold)
            r.font.color.rgb = ov.get("color", color)
            if ov.get("link"):
                r.hyperlink.address = ov["link"]
                # keep our own colour; PowerPoint would otherwise force theme blue
                r.font.color.rgb = ov.get("color", color)
                r.font.underline = ov.get("underline", False)


def textbox(slide, l, t, w, h):
    tb = slide.shapes.add_textbox(Emu(int(l)), Emu(int(t)), Emu(int(w)), Emu(int(h)))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    return tf


def card(slide, l, t, w, h, fill=SOFT, border=LINE, radius=0.09):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                Emu(int(l)), Emu(int(t)), Emu(int(w)), Emu(int(h)))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    if border is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = border
        sh.line.width = Pt(0.75)
    sh.shadow.inherit = False
    try:
        sh.adjustments[0] = radius
    except Exception:
        pass
    tf = sh.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Emu(130000)
    tf.margin_top = tf.margin_bottom = Emu(90000)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    return sh


def arrow(slide, x1, y1, x2, y2, color=CYAN, width=1.25):
    cn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Emu(int(x1)), Emu(int(y1)),
                                    Emu(int(x2)), Emu(int(y2)))
    cn.line.color.rgb = color
    cn.line.width = Pt(width)
    ln = cn.line._get_or_add_ln()
    ln.append(ln.makeelement(qn('a:tailEnd'),
                             {'type': 'triangle', 'w': 'sm', 'len': 'sm'}))
    return cn


def heading(slide, text, sub=None):
    write(textbox(slide, MARGIN, TOP, BODY_W, 420000), [text],
          size=25, bold=True, color=INK, space=0)
    y = TOP + 430000
    if sub:
        write(textbox(slide, MARGIN, y, BODY_W, 260000), [sub],
              size=11, color=MUTED, space=0)
        y += 290000
    return y + 190000


# ------------------------------------------------------------------ slide 1
FIELDS = {
    "Team Name :": ("Team Name", "Provenance"),
    "Team Leader Name :": ("Team Leader Name", "Manoj T"),
    "Team Size :": ("Team Size", "2"),
    "Problem Statement :": ("Problem Statement",
                            "1. Risk, Fraud and Regulatory Intelligence Copilot"),
}
for sh in prs.slides[0].shapes:
    if sh.has_text_frame and sh.text_frame.text.strip() in FIELDS:
        label, value = FIELDS[sh.text_frame.text.strip()]
        sh.text_frame.clear()
        write(sh.text_frame, [[(label + " :  ", {"color": INK2}),
                               (value, {"color": INK, "bold": True})]], size=15, space=0)

# strip the template's own scaffolding text from the content slides
for _s in list(prs.slides)[1:5]:
    for _sh in list(_s.shapes):
        if _sh.has_text_frame and any(k in _sh.text_frame.text
                                      for k in ("Submission Guidelines", "Additional Slide")):
            _sh._element.getparent().remove(_sh._element)

S = [prs.slides[i] for i in range(1, 5)]

# ================================================================== 2 problem
sl = S[0]
y = heading(sl, "The problem",
            "Risk, Fraud and Regulatory Intelligence Copilot   ·   banking and NBFC")

band = card(sl, MARGIN, y, BODY_W, 720000, fill=NAVY, border=None)
write(band.text_frame, [[("Finding the risk signal is cheap.   ", {"color": WHITE}),
                         ("Defending the number is expensive.", {"color": CYAN_B, "bold": True})]],
      size=18, align=PP_ALIGN.CENTER, space=0)
y += 720000 + 280000

tiles = [("TODAY",
          "Ten minutes to find the signal. Two days to assemble an evidence pack an auditor "
          "will accept."),
         ("THE GAP",
          "Ask two analysts the same question and they compute it differently. Booking or "
          "value date. Reversals in or out."),
         ("THE USER",
          "A compliance analyst or MLRO at a mid-sized bank who has to put their name on "
          "the number.")]
g = 210000
tw = (BODY_W - 2 * g) // 3
th = max(est_height(b, 11, tw - 300000) + 320000 for _, b in tiles)
for i, (head, body) in enumerate(tiles):
    c = card(sl, MARGIN + i * (tw + g), y, tw, th, fill=WHITE, border=LINE)
    c.text_frame.vertical_anchor = MSO_ANCHOR.TOP
    write(c.text_frame, [[(head, {"size": 9.5, "bold": True, "color": CYAN})],
                         [(body, {"size": 11, "color": INK2})]], space=7)
y += th + 280000

closing = ("PaperTrail does not answer with a number. It answers with a filing, in which every "
           "figure is a footnote that resolves to its governed definition, the exact SQL, the "
           "source rows, and the clause that makes it matter.")
ch = min(est_height(closing, 12.5, BODY_W - 300000), FLOOR - y)
write(card(sl, MARGIN, y, BODY_W, ch, fill=SOFT).text_frame,
      [closing], size=12.5, color=INK, space=0)

# ============================================================ 3 architecture
sl = S[1]
y = heading(sl, "Architecture",
            "Snowflake-native, end to end. No LangChain, no external vector store, "
            "no third-party LLM API.")

BH = 380000
cgap = 320000
colw = (BODY_W - cgap) // 2
lx, rx = MARGIN, MARGIN + colw + cgap


def node(x, w, t, title_txt, sub_txt, h=BH):
    c = card(sl, x, t, w, h, fill=WHITE, border=LINE)
    write(c.text_frame, [[(title_txt, {"size": 10.5, "bold": True, "color": CYAN})],
                         [(sub_txt, {"size": 8.5, "color": MUTED})]],
          space=1, align=PP_ALIGN.CENTER)
    return t + h


STEP = BH + 140000
rows = [("STRUCTURED", "240,798 transactions  ·  809 counterparties",
         "UNSTRUCTURED", "11 regulatory PDFs  ·  AI_PARSE_DOCUMENT"),
        ("RAW to CURATED to GOLD", "9 Dynamic Tables  ·  entity resolution",
         "CORTEX SEARCH", "72 clauses  ·  11 of 12 top-1 retrieval"),
        ("SEMANTIC VIEW", "7 governed metrics  ·  10 verified queries",
         "ROW ACCESS POLICIES", "AU and SG analyst personas")]
ya = y
for i, (lt, ls, rt, rs) in enumerate(rows):
    bot = node(lx, colw, ya, lt, ls)
    node(rx, colw, ya, rt, rs)
    nxt = ya + STEP
    arrow(sl, lx + colw / 2, bot, lx + colw / 2, nxt)
    arrow(sl, rx + colw / 2, bot, rx + colw / 2, nxt)
    ya = nxt

ag = card(sl, MARGIN, ya, BODY_W, 420000, fill=NAVY, border=None)
write(ag.text_frame,
      [[("CORTEX AGENT", {"color": CYAN_B, "bold": True, "size": 11}),
        ("      figures to Analyst   ·   rules to Search   ·   refuses what it cannot ground",
         {"color": WHITE, "size": 10})]], align=PP_ALIGN.CENTER, space=0)
ya += 420000 + 150000

skills = [("risk-scanner", "governed query,\nprovenance bundle"),
          ("regulation-linker", "clause retrieval\nwith citations"),
          ("finding-writer", "assembles finding,\ncannot invent a figure"),
          ("provenance-logger", "append only,\ncontent hashed")]
sg = 160000
sw = (BODY_W - 3 * sg) // 4
shh = 520000
for i, (nm, ds) in enumerate(skills):
    x = MARGIN + i * (sw + sg)
    c = card(sl, x, ya, sw, shh, fill=WHITE, border=CYAN)
    write(c.text_frame, [[(nm, {"size": 10, "bold": True, "color": CYAN})],
                         [(ds, {"size": 8, "color": MUTED})]],
          space=1, align=PP_ALIGN.CENTER)
    if i < 3:
        arrow(sl, x + sw, ya + shh / 2, x + sw + sg, ya + shh / 2)

# ============================================================= 4 measurement
sl = S[2]
y = heading(sl, "Measured, not asserted",
            "Governed against ungoverned. Same data, same model, full raw DDL, "
            "no hint of any governance rule.")

lead = ("An ungoverned model is not inconsistent. Across 25 runs the SQL was byte identical. "
        "It is perfectly confident, and wrong on 2 of 5.")
lh = est_height(lead, 12, BODY_W - 400000) + 60000
c = card(sl, MARGIN, y, BODY_W, lh, fill=RGBColor(0xFB, 0xEC, 0xEC),
         border=RGBColor(0xE8, 0xC8, 0xC8))
write(c.text_frame, [[("Our hypothesis was wrong. ", {"bold": True, "color": CRIT}),
                      (lead, {"color": INK})]], size=12, space=0)
y += lh + 300000

rows = [("Suspicious volume, Q3 2026", "8,797,923", "4,295,229", "+105%", CRIT),
        ("Exposure to CP-STRUCT-01", "87,185", "87,185", "agree", MUTED),
        ("Alert closure rate, 2026", "63.6%", "63.6%", "agree", MUTED),
        ("SAR filing share", "6.5%", "6.5%", "agree", MUTED),
        ("High risk counterparties, Singapore", "23", "36", "-36%", CRIT)]
cw = [BODY_W - 3300000, 1200000, 1200000, 900000]
x = MARGIN
for i, hname in enumerate(["QUESTION", "UNGOVERNED", "GOVERNED", ""]):
    write(textbox(sl, x, y, cw[i], 190000), [hname], size=8, bold=True, color=MUTED,
          space=0, align=PP_ALIGN.RIGHT if i else PP_ALIGN.LEFT)
    x += cw[i]
y += 230000
rule = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(MARGIN), Emu(int(y)), Emu(BODY_W), Emu(9000))
rule.fill.solid(); rule.fill.fore_color.rgb = LINE
rule.line.fill.background(); rule.shadow.inherit = False
y += 70000
for label, u, gv, v, col in rows:
    x = MARGIN
    for i, (val, al) in enumerate([(label, PP_ALIGN.LEFT), (u, PP_ALIGN.RIGHT),
                                   (gv, PP_ALIGN.RIGHT), (v, PP_ALIGN.RIGHT)]):
        write(textbox(sl, x, y, cw[i], 240000), [val], size=11, space=0, align=al,
              color=(col if i == 3 else INK), bold=(i == 3 and col is CRIT))
        x += cw[i]
    y += 285000

y += 90000
foot = ("The $4.5M overstatement comes from four missed decisions at once: booking date rather than "
        "value date, reversals counted, unsettled counted, and transactions on already closed "
        "alerts treated as suspicious. Exposure agrees only by coincidence, because that "
        "counterparty has no beneficial ownership links.")
write(textbox(sl, MARGIN, y, BODY_W, min(est_height(foot, 10, BODY_W), FLOOR - y)),
      [foot], size=10, color=INK2, space=0, line=1.2)

# =============================================================== 5 outcomes
sl = S[3]
y = heading(sl, "Measured outcomes",
            "Scored against an answer key that was never loaded into Snowflake.")

stats = [("0.944", "detection recall"), ("5 of 6", "typologies at F1 1.000"),
         ("11 / 12", "clause retrieval, top-1"), ("5 / 5", "agent tool routing")]
sg = 180000
sw = (BODY_W - 3 * sg) // 4
for i, (v, l) in enumerate(stats):
    c = card(sl, MARGIN + i * (sw + sg), y, sw, 680000, fill=WHITE, border=LINE)
    write(c.text_frame, [[(v, {"size": 21, "bold": True, "color": CYAN})],
                         [(l, {"size": 8.5, "color": MUTED})]],
          space=2, align=PP_ALIGN.CENTER)
y += 680000 + 250000

pg = 240000
hw = (BODY_W - pg) // 2
panels = [("WHAT IT SAVES",
           "The evidence pack is the artefact that takes an analyst two days by hand. "
           "PaperTrail emits it with the answer, and the figure re-derives from its own "
           "footnote in about 300 ms."),
          ("WHY NOT 100%",
           "Velocity spike detection is weak. Removing it would take precision and F1 to "
           "1.000. We kept it because the regulation requires it. A perfect score on "
           "self-authored data would be evidence of tuning.")]
ph = max(est_height(b, 10.5, hw - 380000) + 330000 for _, b in panels)
for i, (head, body) in enumerate(panels):
    c = card(sl, MARGIN + i * (hw + pg), y, hw, ph, fill=SOFT)
    c.text_frame.vertical_anchor = MSO_ANCHOR.TOP
    write(c.text_frame, [[(head, {"size": 9.5, "bold": True, "color": CYAN})],
                         [(body, {"size": 10.5, "color": INK2})]], space=7)
y += ph + 250000

lh2 = min(760000, FLOOR - y)
links = card(sl, MARGIN, y, BODY_W, lh2, fill=NAVY, border=None)
APP = "https://papertrail-provenance.vercel.app"
REPO = "https://github.com/tjmanoj/papertrail"
write(links.text_frame,
      [[("Live app    ", {"color": MUTED, "size": 9.5}),
        ("papertrail-provenance.vercel.app",
         {"color": CYAN_B, "size": 12.5, "bold": True, "link": APP}),
        ("    opens for anyone, no login", {"color": MUTED, "size": 9.5})],
       [("Repository    ", {"color": MUTED, "size": 9.5}),
        ("github.com/tjmanoj/papertrail",
         {"color": WHITE, "size": 10.5, "link": REPO}),
        ("        Also deployed natively as    ", {"color": MUTED, "size": 9.5}),
        ("Streamlit in Snowflake", {"color": WHITE, "size": 10.5})]],
      space=4, align=PP_ALIGN.CENTER)

# --------------------------------------------------------------- final sweep
for _sl in prs.slides:
    for _sh in _sl.shapes:
        if not _sh.has_text_frame:
            continue
        for _p in _sh.text_frame.paragraphs:
            for _r in _p.runs:
                _r.font.name = "Arial"
                if "—" in _r.text or "–" in _r.text:
                    _r.text = _r.text.replace("—", "-").replace("–", "-")

prs.save(OUT)
print("saved:", OUT, "| slides:", len(prs.slides._sldIdLst))
