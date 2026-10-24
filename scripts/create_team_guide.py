"""Build the compact team brochure and one-page feedback setup guide."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / ".build-tools"))
sys.path.insert(0, str(ROOT / "build/pdf-tools"))
from pdfstudio import __version__
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

OUT = ROOT / "output/pdf"
OUT.mkdir(parents=True, exist_ok=True)
W, H = A4
NAVY = HexColor("#20365b")
TEAL = HexColor("#006b67")
INK = HexColor("#202936")
MUTED = HexColor("#4b5868")
LINE = HexColor("#d8e0e7")
PALE = HexColor("#edf6f5")
for name, file in [("Sarabun", "Sarabun-Regular.ttf"), ("SarabunBold", "Sarabun-Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(name, str(ROOT / "vendor/fonts" / file)))


def text(c, x, y, value, size=11, color=INK, bold=False):
    c.setFillColor(color)
    c.setFont("SarabunBold" if bold else "Sarabun", size)
    c.drawString(x, y, value)


def paragraph(c, x, top, width, value, size=10.5, color=MUTED, leading=None, bold=False):
    style = ParagraphStyle("body", fontName="SarabunBold" if bold else "Sarabun", fontSize=size,
                           leading=leading or size * 1.5, textColor=color)
    content = Paragraph(value, style)
    _, height = content.wrap(width, 1000)
    content.drawOn(c, x, top - height)
    return height


def chrome(c, page, label="TEAM GUIDE"):
    c.setFillColor(white)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.drawImage(str(ROOT / "web/public/branding/pdfstudio-128.png"), 42, 777, 34, 34, mask="auto")
    text(c, 87, 790, "PDF Studio", 17, NAVY, True)
    c.setFont("SarabunBold", 8)
    c.setFillColor(TEAL)
    c.drawRightString(W - 42, 791, label)
    c.setStrokeColor(LINE)
    c.line(42, 766, W - 42, 766)
    c.line(42, 48, W - 42, 48)
    text(c, 42, 30, f"PDF Studio  |  v{__version__}  |  Team enablement", 8, MUTED)
    c.drawRightString(W - 42, 30, page)


def card(c, x, top, number, title, body):
    width, height = 247, 167
    c.setFillColor(HexColor("#f5f7fa"))
    c.roundRect(x, top - height, width, height, 9, fill=1, stroke=0)
    text(c, x + 17, top - 28, number, 9, TEAL, True)
    text(c, x + 17, top - 54, title, 18, NAVY, True)
    paragraph(c, x + 17, top - 66, width - 34, body, 10, leading=15)


def brochure():
    path = OUT / "PDF-Studio-Team-Guide.pdf"
    c = canvas.Canvas(str(path), pagesize=A4, pageCompression=1)
    c.setTitle("PDF Studio - compact team guide")
    c.setAuthor("PDF Studio")
    chrome(c, "01 / 02")
    text(c, 42, 739, "DOCUMENT WORK, MADE PRACTICAL", 9, TEAL, True)
    text(c, 42, 690, "Read. Prepare. Share.", 35, NAVY, True)
    paragraph(c, 42, 669, 480, "A practical Windows workspace for reading, arranging and finishing PDFs, with useful conversion tools for everyday team documents.", 12, INK, 18)
    for x, label in [(42, "On-device processing"), (222, "Original files preserved"), (414, "Windows desktop")]:
        c.setFillColor(PALE)
        width = pdfmetrics.stringWidth(label, "Sarabun", 9) + 18
        c.roundRect(x, 596, width, 24, 12, fill=1, stroke=0)
        text(c, x + 9, 604, label, 9, TEAL)
    screenshot = ROOT / "tmp/feedback-review-0.1.016/studio-reader.png"
    c.setStrokeColor(LINE)
    c.roundRect(42, 244, W - 84, 335, 5, fill=0, stroke=1)
    c.drawImage(str(screenshot), 43, 245, width=W - 86, height=333, preserveAspectRatio=True, anchor="c")
    text(c, 42, 228, "Actual application view with a synthetic training document.", 8.5, MUTED)
    text(c, 42, 196, "One workspace for everyday document tasks.", 16, NAVY, True)
    text(c, 42, 163, "Keep work on your device", 12, NAVY, True)
    paragraph(c, 42, 150, 240, "Read, edit and convert locally. The application does not upload your open documents to a processing service.", 10.5)
    text(c, 311, 163, "Save a result you can share", 12, NAVY, True)
    paragraph(c, 311, 150, 242, "Prepare a working copy, review it, then use Save As. Your original source file is preserved.", 10.5)
    c.showPage()
    chrome(c, "02 / 02")
    text(c, 42, 730, "Choose the right workflow.", 28, NAVY, True)
    paragraph(c, 42, 714, 510, "Four clear workspaces cover the tasks your team repeats most often.", 11)
    card(c, 42, 677, "01", "Read", "Search and copy selectable text. Choose single, continuous, two-page or four-page views. Pan, zoom and enter Focus view. Read Aloud uses installed local voices when text is available.")
    card(c, 306, 677, "02", "Organize", "Build a pack from PDFs and prepared image or Office copies. Reorder, duplicate and rotate pages. Combine files, export selected pages or split ranges into a ZIP.")
    card(c, 42, 496, "03", "Edit / Fill", "Add text, images, signatures, drawings and covers. Apply changes to page ranges, undo and preview. Use <b>Redact content</b> to remove underlying content on export; a cover only hides it visually.")
    card(c, 306, 496, "04", "Tools", "Convert supported documents to PDF locally. Extract PDF tables to Excel or CSV and create Markdown from PDFs. Review the result: complex layouts and table structures may need adjustment.")
    text(c, 42, 302, "A practical 3-minute start", 17, NAVY, True)
    steps = ["<b>Add files.</b> Open a PDF, image, Office document, HTML, Markdown or text file.", "<b>Choose a workflow.</b> Review in Read, arrange in Organize, or finish in Edit / Fill.", "<b>Preview and save.</b> Check the result, choose Save As and keep the saved copy."]
    for index, step in enumerate(steps):
        top = 279 - index * 31
        text(c, 44, top - 12, str(index + 1).zfill(2), 10, TEAL, True)
        paragraph(c, 72, top, 475, step, 10.5)
    c.setFillColor(NAVY)
    c.roundRect(42, 119, W - 84, 63, 7, fill=1, stroke=0)
    text(c, 56, 161, "Before you share", 11, white, True)
    paragraph(c, 56, 151, W - 112, "Check page order and sensitive content. Use redaction when information must be removed. Save results before quitting; unsaved temporary work is cleared on exit.", 9, white, 12)
    paragraph(c, 42, 108, W - 84, "<b>Help improve the app:</b> open Feedback after opening a file (or Settings &gt; Share feedback). Give a score and a useful example of what worked or what should improve. Your response goes to your team's Microsoft Form; PDF Studio does not attach your documents.", 9, MUTED, 13)
    c.save()
    return path


def feedback_guide():
    path = OUT / "PDF-Studio-Feedback-Setup.pdf"
    c = canvas.Canvas(str(path), pagesize=A4, pageCompression=1)
    c.setTitle("PDF Studio - Microsoft Forms setup")
    c.setAuthor("PDF Studio")
    chrome(c, "01 / 01", "FORM OWNER GUIDE")
    text(c, 42, 729, "Connect your feedback form", 27, NAVY, True)
    paragraph(c, 42, 711, 510, "Create the form once, connect it in Settings and review responses online. No email-sending credentials are needed in PDF Studio.", 11, INK, 17)
    steps = [
        ("Create a form", "Open <b>forms.office.com</b> with your work account. Select <b>New form</b>, title it <b>PDF Studio feedback</b>, and describe its purpose."),
        ("Add the score", "Add a required <b>Rating</b>: How would you rate PDF Studio? Use <b>5 levels</b> with stars. Subtitle: 1 = Poor / 5 = Excellent."),
        ("Add written feedback", "Add a required <b>Text</b>: What would you like to share? Turn on <b>Long answer</b>."),
        ("Add the feature", "Add an optional <b>Choice</b>: Which feature did you use? Options: Read, Organize, Edit / Fill, Tools, Other. Choose a dropdown if preferred."),
        ("Choose style and audience", "Use a teal style. In <b>Collect responses</b>, choose <b>Anyone can respond</b> for responses inside the app, when company policy permits. Company-only forms may require the browser sign-in fallback."),
        ("Connect PDF Studio", "Copy the response link, or the URL in the Embed code. In PDF Studio, open <b>Settings &gt; Feedback &gt; Form connection</b>, paste the URL and choose <b>Save form link</b>. Use a response link, not an editing link."),
        ("Verify collection", "Open Feedback and submit one test response. Check the form's <b>Responses</b> tab and <b>Open in Excel</b>. Keep response access limited to the people reviewing feedback."),
    ]
    top = 651
    for index, (title, body) in enumerate(steps):
        text(c, 42, top - 13, str(index + 1).zfill(2), 11, TEAL, True)
        text(c, 73, top - 12, title, 11, NAVY, True)
        height = paragraph(c, 73, top - 18, 478, body, 9.5, leading=14)
        top -= height + 34
    c.setFillColor(PALE)
    c.roundRect(42, 121, W - 84, 75, 7, fill=1, stroke=0)
    text(c, 56, 176, "If company sign-in does not load", 11, TEAL, True)
    paragraph(c, 56, 165, W - 112, "Choose <b>Open in browser</b> in the panel. Your PDF stays open. Closing and reopening the panel preserves its current form; reloading it or quitting the app may clear unsubmitted answers.", 9.5, INK, 14)
    text(c, 42, 92, "Microsoft's setup reference", 9, NAVY, True)
    link = "https://support.microsoft.com/en-gb/forms/send-a-form-to-get-responses"
    text(c, 42, 76, "Send a form to get responses - Microsoft Support", 9, TEAL)
    c.linkURL(link, (42, 72, 300, 88), relative=0)
    c.save()
    return path


if __name__ == "__main__":
    for path in (brochure(), feedback_guide()):
        print(path)
