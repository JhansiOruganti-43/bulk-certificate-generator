import os
from typing import Optional
from datetime import datetime
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

# Setup secure storage directory completely outside of endpoints
CERTIFICATE_STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "certificates")
os.makedirs(CERTIFICATE_STORAGE_DIR, exist_ok=True)

class PDFGenerationError(Exception):
    pass

def generate_pdf(recipient_name: str, course_name: str, certificate_id: str, issue_date: str, course_start: Optional[str] = None, course_end: Optional[str] = None, completion_date: Optional[str] = None) -> str:
    """
    Generates a PDF certificate safely into the internal storage directory.
    
    Returns the generated secure filename.
    """
    if not recipient_name or not course_name:
        raise PDFGenerationError("Recipient name and course name are required for PDF generation.")
        
    filename = f"{certificate_id}.pdf"
    safe_path = os.path.join(CERTIFICATE_STORAGE_DIR, filename)

    try:
        c = canvas.Canvas(safe_path, pagesize=landscape(letter))
        width, height = landscape(letter)

        # Background Color (Minimalistic)
        c.setFillColor(HexColor("#f8fafc"))
        c.rect(0, 0, width, height, fill=1, stroke=0)

        # Border
        c.setStrokeColor(HexColor("#008080")) # Teal blue
        c.setLineWidth(4)
        c.rect(20, 20, width - 40, height - 40)
        c.setStrokeColor(HexColor("#FFD700")) # Gold accents
        c.setLineWidth(1)
        c.rect(26, 26, width - 52, height - 52)
        
        # Header / Title
        c.setFillColor(HexColor("#0f172a"))
        c.setFont("Helvetica-Bold", 36)
        c.drawCentredString(width / 2.0, height - 120, "CERTIFICATE OF COMPLETION")

        # Ribbon text
        c.setFillColor(HexColor("#87CEEB")) # Sky blue accent
        c.setFont("Helvetica", 14)
        c.drawCentredString(width / 2.0, height - 160, "This is proudly presented to")

        # Name
        c.setFillColor(HexColor("#008080")) # Main Teal
        c.setFont("Helvetica-Bold", 32)
        c.drawCentredString(width / 2.0, height - 230, recipient_name.upper())

        # Subtext
        c.setFillColor(HexColor("#0f172a"))
        c.setFont("Helvetica", 14)
        c.drawCentredString(width / 2.0, height - 280, "for successfully completing the course/program:")
        
        # Course
        c.setFont("Helvetica-Oblique", 24)
        c.drawCentredString(width / 2.0, height - 330, course_name)

        # Details with optional dates
        c.setFont("Helvetica", 12)
        c.setFillColor(HexColor("#0f172a"))
        y = 60
        c.drawString(60, y, f"Issued Date: {issue_date}")
        if course_start:
            y += 15
            c.drawString(60, y, f"Course Start: {course_start}")
        if course_end:
            y += 15
            c.drawString(60, y, f"Course End: {course_end}")
        if completion_date:
            y += 15
            c.drawString(60, y, f"Completion Date: {completion_date}")
        c.drawRightString(width - 60, 60, f"Certificate ID: {certificate_id}")

        c.showPage()
        c.save()
        
        return filename
    except Exception as e:
        # If failure occurred, ensure we don't leave partial or corrupt files
        if os.path.exists(safe_path):
            os.remove(safe_path)
        raise PDFGenerationError(f"PDF library failed: {str(e)}")
