"""
Skin Analysis Routes — Main analysis wizard + AI image analysis API
"""
import os
import copy
import json
import base64
import datetime

from flask import Blueprint, render_template, request, flash, session, jsonify, current_app
from flask_login import login_required, current_user

from backend import db
from backend.models import SkinReport
from backend.services.gemini import analyze_face_image, generate_personalized_routine
from backend.services.scoring import calculate_skin_score
from backend.data.routines import SKIN_ROUTINES

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route('/skin-analysis', methods=['GET', 'POST'])
@login_required
def skin_analysis():
    if request.method == 'POST':
        image_path = None
        current_timestamp = int(datetime.datetime.now().timestamp())
        upload_folder = current_app.config['UPLOAD_FOLDER']

        # 1. Handle File Upload
        file = request.files.get('face_image')
        if file and file.filename and _allowed_file(file.filename):
            filename = f"user_{current_user.id}_{current_timestamp}.jpg"
            save_path = os.path.join(upload_folder, filename)
            file.save(save_path)
            image_path = filename

        # 2. Handle Camera Capture (Base64)
        camera_data = request.form.get('camera_image')
        if camera_data and "base64" in camera_data:
            try:
                header, encoded = camera_data.split(",", 1)
                data_bytes = base64.b64decode(encoded)
                filename = f"cam_{current_user.id}_{current_timestamp}.png"
                save_path = os.path.join(upload_folder, filename)
                with open(save_path, "wb") as f:
                    f.write(data_bytes)
                image_path = filename
            except Exception as e:
                print(f"Error saving camera image: {e}")

        # Collect Form Data
        concerns_list = request.form.getlist('concerns')
        concern_raw = ", ".join(concerns_list) if concerns_list else (request.form.get('concern') or 'None')
        skin_type = request.form.get('skin_type') or 'Normal'

        data = {
            "age": request.form.get('age') or 25,
            "gender": request.form.get('gender') or 'Other',
            "climate": request.form.get('climate') or 'Not specified',
            "skin_type": skin_type,
            "oily_after_wash": request.form.get('oily_after_wash') or 'No',
            "dry_after_wash": request.form.get('dry_after_wash') or 'No',
            "concern": concern_raw,
            "problem_duration": request.form.get('problem_duration') or 'Not specified',
            "condition_severity": request.form.get('condition_severity') or 'Not specified',
            "facewash": request.form.get('wash_frequency') or 'Yes',
            "moisturizer": 'Yes',
            "budget": request.form.get('budget') or 'Mid-range',
            "time_spend": request.form.get('time_spend') or '5-10 min',
            "goal": request.form.get('goal') or 'Clear skin',
            "sunscreen": request.form.get('sunscreen') or 'Yes',
            "skincare_products": request.form.get('skincare_products') or 'None',
            "home_remedies": request.form.get('home_remedies') or 'None',
            "allergies": request.form.get('allergies') or 'None',
            "medication": request.form.get('medication') or 'None',
            "sleep": request.form.get('sleep') or '7',
            "water": request.form.get('water') or '1-2 liters',
            "ai_pimples": request.form.get('ai_pimples') == 'true',
            "ai_oily": request.form.get('ai_oily') == 'true' or skin_type in ('Oily', 'Combination'),
            "ai_spots": request.form.get('ai_spots') == 'true',
            "skin_tone": request.form.get('skin_tone') or 'Unknown',
            "estimated_age": request.form.get('estimated_age') or 'Unknown',
            "ai_overall_score": request.form.get('ai_overall_score') or 50
        }

        concern = concern_raw[:50]

        # Parse AI Findings from hidden input
        ai_findings_raw = request.form.get('ai_findings_json')
        if ai_findings_raw:
            try:
                ai_results_enriched = json.loads(ai_findings_raw)
            except:
                ai_results_enriched = []
        else:
            ai_results_enriched = _default_ai_findings(data)

        # Calculate score
        skin_health_score, score_breakdown = calculate_skin_score(ai_results_enriched, data)

        # Result text
        if skin_health_score >= 85:
            result_text = "Good Skin Health 🌟"
        elif skin_health_score >= 65:
            result_text = "Average Skin Health ⚠️"
        elif skin_health_score >= 45:
            result_text = "Needs Attention 🔴"
        else:
            result_text = "Needs Immediate Care 🚨"

        # Build routine
        base_routine = SKIN_ROUTINES.get(data["skin_type"], SKIN_ROUTINES["Combination"])
        routine = copy.deepcopy(base_routine)

        # Try Gemini personalized routine
        gemini_result = generate_personalized_routine(data, ai_results_enriched)
        if gemini_result["routine"]:
            routine = gemini_result["routine"]
        lifestyle = gemini_result["lifestyle"]
        key_ingredients = gemini_result["key_ingredients"]
        warnings = gemini_result["warnings"]

        # Dynamic routine adjustments (fallback)
        routine = _apply_dynamic_adjustments(routine, data, concern, ai_results_enriched)

        # Build dynamic lists
        dynamic_ingredients = _build_dynamic_ingredients(data, concern, ai_results_enriched)
        dynamic_avoid = _build_dynamic_avoid(data, concern, ai_results_enriched)
        dynamic_lifestyle = _build_dynamic_lifestyle(data, concern, ai_results_enriched)

        # Consult CTA logic
        show_consult_cta, consult_reasons = _build_consult_cta(skin_health_score, data, ai_results_enriched)

        routine["what_to_avoid"] = dynamic_avoid
        lifestyle = dynamic_lifestyle
        key_ingredients = dynamic_ingredients

        # Save to DB
        try:
            report = SkinReport(
                user_id=current_user.id, age=data['age'], gender=data['gender'],
                image_file=image_path, skin_type=data["skin_type"], concern=data["concern"],
                facewash=data["facewash"], moisturizer=data["moisturizer"],
                sunscreen=data["sunscreen"], sleep=data["sleep"], water=data["water"],
                ai_pimples=data["ai_pimples"], ai_oily=data["ai_oily"], ai_spots=data["ai_spots"],
                result=result_text, skin_health_score=skin_health_score,
                timestamp=datetime.datetime.utcnow()
            )
            db.session.add(report)
            db.session.commit()
            report_id = report.id
        except Exception as e:
            print(f"DB save error: {e}")
            report_id = None

        # Save to session for PDF
        session["skin_type"] = data["skin_type"]
        session["concerns"] = [data["concern"]]
        session["skin_score"] = skin_health_score
        session["ai_findings"] = ai_results_enriched
        session["morning_routine"] = routine["morning"]
        session["night_routine"] = routine["night"]
        session["precautions"] = routine["precautions"]
        session["what_to_avoid"] = routine.get("what_to_avoid", [])
        session["remedies"] = routine["remedies"]
        session["result"] = result_text
        if image_path:
            session["image_path"] = image_path

        # Previous report comparison
        previous_report = None
        if report_id:
            previous_report = SkinReport.query.filter(
                SkinReport.user_id == current_user.id, SkinReport.id < report_id
            ).order_by(SkinReport.id.desc()).first()

        report_count = SkinReport.query.filter_by(user_id=current_user.id).count()
        first_scan = report_count <= 1

        # AJAX response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
           'application/json' in request.headers.get('Accept', ''):
            return jsonify({
                "status": "saved", "result": result_text, "score": skin_health_score,
                "score_breakdown": score_breakdown, "show_consult_cta": show_consult_cta,
                "consult_reasons": consult_reasons, "ai_results": ai_results_enriched,
                "routine": routine, "report_id": report_id,
                "previous_score": previous_report.skin_health_score if previous_report else None,
                "first_scan": first_scan
            })

        return render_template(
            'skin_report.html', data=data, result=result_text, routine=routine,
            lifestyle=lifestyle, key_ingredients=key_ingredients, warnings=warnings,
            image_path=image_path, ai_results=ai_results_enriched, score=skin_health_score,
            score_breakdown=score_breakdown, show_consult_cta=show_consult_cta,
            consult_reasons=consult_reasons,
            current_date=datetime.datetime.now().strftime("%d %b %Y, %I:%M %p"),
            previous_report=previous_report,
            previous_score=previous_report.skin_health_score if previous_report else None,
            first_scan=first_scan
        )

    return render_template('skin_analysis.html')


@analysis_bp.route('/api/analyze-image', methods=['POST'])
@login_required
def analyze_image_api():
    try:
        image_data = request.form.get('image')
        file = request.files.get('file')
        result = analyze_face_image(image_data=image_data, file_obj=file)
        if result and "error" in result:
            return jsonify(result), 400 if "No image" in result.get("error", "") else 500
        if result:
            return jsonify(result)
        return jsonify({"error": "AI analysis failed"}), 500
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500


# ================== HELPER FUNCTIONS ==================

def _allowed_file(filename):
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'jfif', 'webp'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


def _default_ai_findings(data):
    return [
        {"condition": "Pimples / Acne", "severity": "High" if data["ai_pimples"] else "Low", "detected": data["ai_pimples"], "confidence": 92},
        {"condition": "Oiliness", "severity": "High" if data["ai_oily"] else "Low", "detected": data["ai_oily"], "confidence": 88},
        {"condition": "Dark Spots / Hyperpigmentation", "severity": "High" if data["ai_spots"] else "Low", "detected": data["ai_spots"], "confidence": 85},
        {"condition": "Dryness / Flakiness", "severity": "Low", "detected": False, "confidence": 90},
        {"condition": "Redness / Irritation", "severity": "Low", "detected": False, "confidence": 90},
        {"condition": "Visible Pores", "severity": "Small", "detected": False, "confidence": 90},
        {"condition": "Skin Texture", "severity": "Smooth", "detected": False, "confidence": 90},
        {"condition": "Under-eye Circles", "severity": "Low", "detected": False, "confidence": 90}
    ]


def _apply_dynamic_adjustments(routine, data, concern, ai_results):
    if data["ai_pimples"] or concern == "Acne":
        if not any("Salicylic" in step or "Benzoyl" in step for step in routine["night"]):
            routine["night"].append("Targeted acne spot treatment (Salicylic acid/Benzoyl peroxide) (30 sec) — reduces active breakouts.")
        if "Avoid comedogenic products" not in routine["precautions"]:
            routine["precautions"].append("Avoid comedogenic products")

    if data["ai_spots"] or concern in ["Pigmentation", "Dark Spots"]:
        if not any("Vitamin C" in step for step in routine["morning"]):
            routine["morning"].insert(1, "Vitamin C Serum (Brightening) (30 sec) — fades dark spots.")
        if not any("Arbutin" in step or "Tranexamic" in step for step in routine["night"]):
            routine["night"].insert(1, "Alpha Arbutin or Tranexamic Acid serum (30 sec) — corrects pigmentation.")
        if "Strict daily sun protection is crucial" not in routine["precautions"]:
            routine["precautions"].append("Strict daily sun protection is crucial")

    if data["ai_oily"] and data["skin_type"] != "Oily":
        if "Use a clay mask on oily areas 1x/week" not in routine["remedies"]:
            routine["remedies"].append("Use a clay mask on oily areas 1x/week")

    return routine


def _build_dynamic_ingredients(data, concern, ai_results):
    ingredients = []
    is_spots = data["ai_spots"] or concern in ["Pigmentation", "Dark Spots"]
    is_oily = data["ai_oily"] or data["skin_type"] == "Oily"
    is_acne = data["ai_pimples"] or concern == "Acne"

    ingredients.append({"name": "SPF 50", "desc": "Universal protection against UV damage & aging."})

    if is_spots:
        ingredients.extend([
            {"name": "Vitamin C", "desc": "Brightens dark spots & evens tone."},
            {"name": "Alpha Arbutin", "desc": "Gently fades hyperpigmentation."},
            {"name": "Tranexamic Acid", "desc": "Reduces stubborn dark spots."}
        ])
    if is_oily:
        ingredients.extend([
            {"name": "Niacinamide", "desc": "Regulates oil production & minimizes pores."},
            {"name": "Zinc", "desc": "Controls sebum and reduces inflammation"}
        ])
    if "Visible Pores" in str(ai_results):
        ingredients.extend([
            {"name": "Retinol", "desc": "Increases cell turnover and reduces pore visibility"},
            {"name": "Clay", "desc": "Absorbs excess oil and tightens pores"}
        ])
    if concern == "Dryness / Tanning" or data["skin_type"] == "Dry":
        ingredients.extend([
            {"name": "Hyaluronic Acid", "desc": "Draws moisture into the skin."},
            {"name": "Ceramides", "desc": "Repairs the skin barrier."},
            {"name": "Squalane", "desc": "Lightweight, non-comedogenic hydration"}
        ])
    if is_acne:
        ingredients.extend([
            {"name": "Benzoyl Peroxide", "desc": "Kills acne-causing bacteria."},
            {"name": "Salicylic Acid", "desc": "Cleans deep inside pores."},
            {"name": "Tea Tree", "desc": "Natural antibacterial for mild breakouts"}
        ])
    return ingredients


def _build_dynamic_avoid(data, concern, ai_results):
    avoid = []
    is_spots = data["ai_spots"] or concern in ["Pigmentation", "Dark Spots"]
    is_oily = data["ai_oily"] or data["skin_type"] == "Oily"
    is_acne = data["ai_pimples"] or concern == "Acne"
    clm = data.get("climate", "").lower()

    if is_spots:
        avoid.extend(["Avoid unprotected sun exposure", "Avoid photosensitizing actives without SPF", "Avoid DIY lemon/lime juice treatments"])
    if "humid" in clm:
        avoid.extend(["Avoid heavy occlusive creams", "Avoid skipping face wash after sweating", "Avoid thick balm-based sunscreens on T-zone"])
    if is_oily:
        avoid.extend(["Avoid pore-clogging ingredients", "Avoid over-washing — causes rebound oiliness", "Avoid alcohol-based toners"])
    if is_acne:
        avoid.extend(["Avoid picking or touching healed spots", "Avoid high-strength retinol without building up slowly"])
    if data["water"] == "Less than 1 liter":
        avoid.append("Avoid excess caffeine/alcohol — dehydrates skin further")
    if data["sunscreen"] == "No":
        avoid.append("⚠️ CRITICAL: Avoiding SPF is your #1 skin damage risk")
    if not avoid:
        avoid = ["Avoid sleeping with makeup on", "Avoid touching your face throughout the day"]
    return avoid


def _build_dynamic_lifestyle(data, concern, ai_results):
    lifestyle = []
    is_spots = data["ai_spots"] or concern in ["Pigmentation", "Dark Spots"]
    is_acne = data["ai_pimples"] or concern == "Acne"
    clm = data.get("climate", "").lower()

    try:
        sleep = float(data["sleep"])
        if sleep < 6:
            lifestyle.append("⚠️ Low sleep increases cortisol — worsens dark spots and pore size. Target: 7-8hrs.")
        elif sleep < 8:
            lifestyle.append("💤 Try to reach 8hrs for optimal skin repair during sleep cycles.")
        else:
            lifestyle.append("✅ Great sleep habits — skin repairs itself during deep sleep.")
    except:
        pass

    wt = data.get("water", "")
    if wt == "Less than 1 liter":
        lifestyle.append("⚠️ Severely under-hydrated — aim for 2-3L daily.")
    elif wt == "1-2 liters":
        lifestyle.append("💧 Slightly low. Add 2 extra glasses daily.")
    elif wt == "More than 2 liters":
        lifestyle.append("✅ Well hydrated — helps flush toxins.")

    if "humid" in clm:
        lifestyle.append("🌡️ Humid climate — use lightweight, water-based products.")
    elif "dry" in clm:
        lifestyle.append("🏜️ Dry climate — layer hydrating toner before moisturizer.")
    elif "tropical" in clm:
        lifestyle.append("☀️ High UV — reapply SPF every 2hrs outdoors.")

    if is_spots:
        lifestyle.append("🥦 Eat Vitamin C rich foods for natural brightening support.")
    elif is_acne:
        lifestyle.append("🥛 Consider reducing dairy and high-GI foods.")
    else:
        lifestyle.append("🫐 Antioxidant-rich diet reduces skin inflammation.")

    return lifestyle


def _build_consult_cta(score, data, ai_results):
    show = False
    reasons = []
    if score < 70:
        show = True
        reasons.append("Overall skin health score (<70) requires professional guidance")
    if data.get("problem_duration") == "More than 6 months":
        show = True
        reasons.append("Persistent condition lasting over 6 months")
    for f in ai_results:
        sev = f.get("severity", "").lower()
        cond = f.get("condition", "")
        if sev in ["moderate", "severe", "visible", "high", "large"]:
            show = True
            reasons.append(f"{sev.title()} {cond.lower()} treatment options")
    return show, list(dict.fromkeys(reasons))
