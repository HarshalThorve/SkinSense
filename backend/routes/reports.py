"""
Report Download Routes — PDF generation
"""
import os
import io
from datetime import datetime
from flask import Blueprint, redirect, url_for, flash, session, send_file, current_app
from flask_login import login_required, current_user
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/download-report')
@login_required
def download_report():
    data = {
        "date": datetime.now().strftime("%d %B %Y"),
        "skin_type": session.get("skin_type", "Not specified"),
        "concern": ", ".join(session.get("concerns", ["None"])),
        "score": session.get("skin_score", "N/A"),
        "ai_findings": session.get("ai_findings", []),
        "morning": session.get("morning_routine", []),
        "night": session.get("night_routine", []),
        "precautions": session.get("precautions", []),
        "what_to_avoid": session.get("what_to_avoid", []),
        "remedies": session.get("remedies", []),
        "result": session.get("result", "N/A"),
        "image_path": session.get("image_path", None)
    }

    if data["skin_type"] == "Not specified":
        flash("No report found to download.")
        return redirect(url_for('main.dashboard'))

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # --- Header ---
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawCentredString(width / 2, height - 50, "Skin Analysis Report")
    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(width / 2, height - 70, f"Generated for: {current_user.name}")
    pdf.line(50, height - 80, width - 50, height - 80)

    y = height - 110
    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Date: {data['date']}")

    if data["score"] != "N/A":
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(400, y, f"Skin Health Score: {data['score']}/100")
        pdf.setFont("Helvetica", 11)
    y -= 25

    # --- Optional Image ---
    if data["image_path"]:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        img_path = os.path.join(upload_folder, data["image_path"])
        if os.path.exists(img_path):
            try:
                pdf.drawImage(img_path, width - 150, y - 70, width=100, height=100, preserveAspectRatio=True)
            except Exception as e:
                print(f"Skipping PDF image render, error: {e}")

    # --- User Details ---
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "User Profile")
    y -= 20
    pdf.setFont("Helvetica", 12)
    pdf.drawString(60, y, f"Skin Type: {data['skin_type']}")
    pdf.drawString(200, y, f"Main Concern: {data['concern']}")
    y -= 30
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, f"Analysis Result: {data['result']}")

    # --- AI Vision Findings ---
    y -= 40
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "AI Vision Findings (From Photo)")
    pdf.line(50, y - 5, 250, y - 5)
    y -= 25
    pdf.setFont("Helvetica", 11)

    findings_list = data.get("ai_findings", [])
    if isinstance(findings_list, dict):
        findings_list = []

    for f in findings_list:
        condition = f.get("condition", "Condition")
        severity = str(f.get("severity", "Low")).lower()
        is_clear = ("not detected" in severity or "balanced" in severity or severity == "smooth" or severity == "low" or severity == "small")
        status_text = "Found/Clear: Clear" if is_clear else f"Detected (Severity: {f.get('severity', '')})"
        color = (0, 0.5, 0) if is_clear else (0.8, 0, 0)

        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawString(60, y, f"• {condition}: ")
        pdf.setFillColorRGB(*color)
        pdf.drawString(190, y, status_text)
        pdf.setFillColorRGB(0, 0, 0)
        y -= 15
        if y < 50:
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica", 11)

    def draw_section(title, items, start_y):
        pdf.setStrokeColorRGB(0.86, 0.35, 0.47)
        pdf.setLineWidth(0.5)
        pdf.line(50, start_y + 20, width - 50, start_y + 20)
        pdf.setFillColorRGB(0.86, 0.35, 0.47)
        pdf.rect(50, start_y - 2, 5, 14, fill=1, stroke=0)
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(62, start_y, title)
        pdf.setFillColorRGB(0, 0, 0)
        start_y -= 20
        pdf.setFont("Helvetica", 11)

        for item in items:
            if len(item) > 85:
                split_point = item[:85].rfind(' ')
                line1 = item[:split_point]
                line2 = "  " + item[split_point:].strip()
                pdf.drawString(60, start_y, f"• {line1}")
                start_y -= 15
                pdf.drawString(60, start_y, line2)
            else:
                pdf.drawString(60, start_y, f"• {item}")
            start_y -= 15
            if start_y < 50:
                pdf.showPage()
                start_y = height - 50
                pdf.setFont("Helvetica", 11)
        return start_y - 15

    y -= 40
    y = draw_section("Morning Routine", data["morning"], y)
    y = draw_section("Night Routine", data["night"], y)
    y = draw_section("Precautions", data["precautions"], y)
    y = draw_section("What to Avoid", data["what_to_avoid"], y)
    draw_section("Suggested Remedies", data["remedies"], y)

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer, as_attachment=True,
        download_name=f"Skin_Report_{current_user.name}.pdf",
        mimetype="application/pdf"
    )
