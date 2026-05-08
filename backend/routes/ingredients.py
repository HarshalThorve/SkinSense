"""
Ingredient Scan Routes
"""
import os
import re
from flask import Blueprint, render_template, request, flash, current_app
from flask_login import login_required, current_user
from backend import db
from backend.models import IngredientScanHistory
from backend.services.gemini import analyze_ingredient_image
from backend.services.ocr import extract_text_from_image, parse_ingredients_from_text
from backend.data.ingredients_db import SAFE_DB, CAUTION_DB, AVOID_DB

ingredients_bp = Blueprint('ingredients', __name__)


def _allowed_file(filename):
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'jfif', 'webp'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


def _is_good_for_skin_type(ingredient_skin_types, user_skin_type):
    if "all" in ingredient_skin_types:
        return True
    return user_skin_type.lower() in [s.lower() for s in ingredient_skin_types]


@ingredients_bp.route('/ingredient-scan', methods=['GET', 'POST'])
@login_required
def ingredient_scan():
    scan_results = None

    if request.method == 'POST':
        skin_type = request.form.get('skin_type')
        file = request.files.get('image')

        if not skin_type or not file:
            flash("Please select skin type and upload image")
            return render_template('ingredient_scan.html')

        if not _allowed_file(file.filename):
            flash("Only JPG, PNG, WEBP, JFIF images allowed")
            return render_template('ingredient_scan.html')

        upload_folder = current_app.config['UPLOAD_FOLDER']
        filename = file.filename
        path = os.path.join(upload_folder, filename)
        file.save(path)

        try:
            parsed_results = []
            mode_used = "offline"

            # --- TIER 1: GEMINI VISION API ---
            try:
                parsed_results = analyze_ingredient_image(path, skin_type)
                if parsed_results and isinstance(parsed_results, list) and len(parsed_results) > 0:
                    mode_used = "ai"
                else:
                    parsed_results = []
            except Exception as e:
                print(f"Gemini Vision API failed/timeout: {e}")
                parsed_results = []

            # --- TIER 2: FALLBACK WITH OCR ---
            if not parsed_results:
                mode_used = "offline"
                raw_text = extract_text_from_image(path)

                if raw_text:
                    filtered_tokens = parse_ingredients_from_text(raw_text)
                    ingredients_text = ", ".join(filtered_tokens)

                    words = re.split(r'[,.\n|]+', ingredients_text)
                    found_ings = [w.strip() for w in words if len(w.strip()) > 3]

                    if not found_ings:
                        found_ings = ["No clear ingredients parsed"]

                    st_normalized = skin_type.lower()
                    seen = set()

                    for ing in found_ings:
                        matched = False

                        # Check Safe
                        for key, data in SAFE_DB.items():
                            if matched:
                                break
                            aliases = [key] + data.get("aliases", [])
                            if any(a in ing for a in aliases):
                                if key in seen:
                                    matched = True
                                    break
                                seen.add(key)
                                is_compat = _is_good_for_skin_type(data.get("compat", []), st_normalized)
                                parsed_results.append({
                                    "name": key.title(), "status": "Safe",
                                    "reason": data["desc"], "skinTypeCompatibility": is_compat
                                })
                                matched = True

                        # Check Caution
                        for key, data in CAUTION_DB.items():
                            if matched:
                                break
                            aliases = [key] + data.get("aliases", [])
                            if any(a in ing for a in aliases):
                                if key in seen:
                                    matched = True
                                    break
                                seen.add(key)
                                is_compat = False if ("all" in data.get("bad_compat", []) or st_normalized in data.get("bad_compat", [])) else True
                                parsed_results.append({
                                    "name": key.title(), "status": "Caution",
                                    "reason": data["desc"], "skinTypeCompatibility": is_compat
                                })
                                matched = True

                        # Check Avoid
                        for key, data in AVOID_DB.items():
                            if matched:
                                break
                            aliases = [key] + data.get("aliases", [])
                            if any(a in ing for a in aliases):
                                if key in seen:
                                    matched = True
                                    break
                                seen.add(key)
                                is_compat = False if ("all" in data.get("bad_compat", []) or st_normalized in data.get("bad_compat", [])) else True
                                parsed_results.append({
                                    "name": key.title(), "status": "Avoid",
                                    "reason": data["desc"], "skinTypeCompatibility": is_compat
                                })
                                matched = True

                        # Unknown
                        if not matched and len(parsed_results) < 15 and len(ing.split()) <= 4:
                            if ing not in seen:
                                seen.add(ing)
                                parsed_results.append({
                                    "name": ing.title(), "status": "Unknown",
                                    "reason": "Not enough data available", "skinTypeCompatibility": False
                                })

            # Verdict Logic
            has_avoid = any(r.get("status") == "Avoid" for r in parsed_results)
            has_caution = any(r.get("status") == "Caution" for r in parsed_results)

            if has_avoid:
                overall = "Ingredients to Watch 🚨"
                status_class = "danger"
            elif has_caution:
                overall = "Use with Care ⚠️"
                status_class = "warning"
            else:
                overall = "Looks Good 🌿"
                status_class = "success"

            total = len(parsed_results)
            compatible_count = sum(1 for r in parsed_results if r.get("skinTypeCompatibility"))
            if total > 0:
                compat_ratio = compatible_count / total
                if compat_ratio >= 0.7:
                    suitable_msg = "✅ This product is suitable for your skin type"
                    skin_suitable = True
                else:
                    suitable_msg = "⚠️ This product may not be ideal for your skin type"
                    skin_suitable = False
            else:
                skin_suitable = None
                suitable_msg = ""

            scan_results = {
                "parsed_items": parsed_results, "summary": overall,
                "status": status_class, "mode": mode_used,
                "skin_suitable": skin_suitable, "suitable_msg": suitable_msg,
                "skin_type": skin_type
            }

        except Exception as e:
            print(f"Scan Error: {e}")
            flash("⚠️ Could not process image. Please try another one.")
            scan_results = None

        # Log History
        if scan_results:
            scan_history = IngredientScanHistory(
                user_id=current_user.id,
                image_path=filename,
                result_summary=scan_results['summary']
            )
            db.session.add(scan_history)
            db.session.commit()

    return render_template('ingredient_scan.html', scan_results=scan_results)
