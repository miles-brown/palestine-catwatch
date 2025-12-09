from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import io
import os
from datetime import datetime

def generate_officer_dossier(officer, appearances):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # --- Header ---
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height - 50, "Officer Profile & Dossier")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 70, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.line(50, height - 80, width - 50, height - 80)
    
    # --- Officer Details ---
    y = height - 120
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, f"Officer ID: {officer.id}")
    y -= 25
    
    c.setFont("Helvetica", 14)
    c.drawString(50, y, f"Badge Number: {officer.badge_number or 'Unknown'}")
    y -= 20
    c.drawString(50, y, f"Force: {officer.force or 'Unknown'}")
    y -= 20
    # Role is on OfficerAppearance, not Officer - get from first appearance if available
    first_role = appearances[0].role if appearances and appearances[0].role else 'Unknown'
    c.drawString(50, y, f"Role: {first_role}")
    y -= 20
    c.drawString(50, y, f"Total Appearances: {len(appearances)}")
    y -= 40
    
    # --- Appearances List ---
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, "Incident Log")
    y -= 30
    
    for i, app in enumerate(appearances):
        if y < 150: # New page if running out of space
            c.showPage()
            y = height - 50
            
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, f"Incident #{i+1}")
        c.setFont("Helvetica", 12)
        c.drawString(150, y, f"Timestamp: {app.timestamp_in_video}")
        y -= 20
        c.drawString(50, y, f"Action: {app.action}")
        
        # Image
        if app.image_crop_path and os.path.exists(app.image_crop_path):
            try:
                # Draw image
                img_y = y - 110
                c.drawImage(app.image_crop_path, 50, img_y, width=100, height=100, preserveAspectRatio=True)
                y -= 120
            except Exception as e:
                c.drawString(50, y-20, "[Image Error]")
                y -= 30
        else:
            c.drawString(50, y-20, "[No Image]")
            y -= 30
            
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.line(50, y, width-50, y)
        y -= 20
        
    c.save()
    buffer.seek(0)
    return buffer
