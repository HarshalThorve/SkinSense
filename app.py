# ================== IMPORTS ==================
import os
import datetime
import base64
import uuid
import joblib
import numpy as np
import pytesseract
from PIL import Image
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, login_user,
    login_required, logout_user,
    UserMixin, current_user
)
from flask import jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask import send_file
import io
import json

# ================== TESSERACT PATH ==================
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\kunal\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

# ================== ML MODEL ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "ml_models", "skin_model.pkl")

model = joblib.load(MODEL_PATH)


# ================== APP CONFIG ==================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'skinsense_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ================== LOGIN MANAGER ==================
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# ================== DATABASE MODELS ==================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(200)) # Nullable for Google Users? Handled in logic
    phone = db.Column(db.String(20))



class TrendHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    trend = db.Column(db.String(200))
    result = db.Column(db.String(50)) # e.g., "Harmful", "Safe"
    status = db.Column(db.String(20)) # "danger", "success", "warning"
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class IngredientScanHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    image_path = db.Column(db.String(200))
    result_summary = db.Column(db.String(200)) # Short summary
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class SkinReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    image_file = db.Column(db.String(120)) # Added image file column
    skin_type = db.Column(db.String(50))
    concern = db.Column(db.String(50))
    facewash = db.Column(db.String(10))
    moisturizer = db.Column(db.String(10))
    sunscreen = db.Column(db.String(10))
    sleep = db.Column(db.String(20))
    water = db.Column(db.String(20))
    # AI Analysis Results (from Image)
    ai_pimples = db.Column(db.Boolean)
    ai_oily = db.Column(db.Boolean)
    ai_spots = db.Column(db.Boolean)
    result = db.Column(db.String(100))
    skin_health_score = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.template_filter('ist')
def utc_to_ist(dt):
    import datetime
    if not dt:
        return None
    return dt + datetime.timedelta(hours=5, minutes=30)

# ...

# -------- SKIN ANALYSIS (UPDATED) --------
@app.route('/skin-analysis', methods=['GET', 'POST'])
@login_required
def skin_analysis():

    if request.method == 'POST':
        image_path = None
        current_timestamp = int(datetime.datetime.now().timestamp())
        
        # 1. Handle File Upload
        file = request.files.get('face_image')
        if file and file.filename and allowed_file(file.filename):
            filename = f"user_{current_user.id}_{current_timestamp}.jpg"
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(save_path)
            image_path = filename
        
        # 2. Handle Camera Capture (Base64)
        camera_data = request.form.get('camera_image')
        if camera_data and "base64" in camera_data:
            try:
                header, encoded = camera_data.split(",", 1)
                data_bytes = base64.b64decode(encoded)
                filename = f"cam_{current_user.id}_{current_timestamp}.png"
                save_path = os.path.join(UPLOAD_FOLDER, filename)
                with open(save_path, "wb") as f:
                    f.write(data_bytes)
                image_path = filename
            except Exception as e:
                print(f"Error saving camera image: {e}")

        # Collect Form Data — support both old and new UI field names
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
        
        # Primary concern mapped for deterministic database storage length limit
        concern = concern_raw[:50]

        # 1. Parse AI Findings from hidden input
        import json
        ai_findings_raw = request.form.get('ai_findings_json')
        if ai_findings_raw:
            try:
                ai_results_enriched = json.loads(ai_findings_raw)
            except:
                ai_results_enriched = []
        else:
            # Fallback mock for direct routing without JS
            ai_results_enriched = [
                {"condition": "Pimples / Acne", "severity": "High" if data["ai_pimples"] else "Low", "detected": data["ai_pimples"], "confidence": 92},
                {"condition": "Oiliness", "severity": "High" if data["ai_oily"] else "Low", "detected": data["ai_oily"], "confidence": 88},
                {"condition": "Dark Spots / Hyperpigmentation", "severity": "High" if data["ai_spots"] else "Low", "detected": data["ai_spots"], "confidence": 85},
                {"condition": "Dryness / Flakiness", "severity": "Low", "detected": False, "confidence": 90},
                {"condition": "Redness / Irritation", "severity": "Low", "detected": False, "confidence": 90},
                {"condition": "Visible Pores", "severity": "Small", "detected": False, "confidence": 90},
                {"condition": "Skin Texture", "severity": "Smooth", "detected": False, "confidence": 90},
                {"condition": "Under-eye Circles", "severity": "Low", "detected": False, "confidence": 90}
            ]

        # 2. Base Score calculation (Now incorporating Questionnaire Health Factors!)
        def calculate_skin_score(ai_findings, user_data):
            base_score = 100
            score_breakdown = []
            
            # --- Vision Deductions ---
            deductions = {
                "Severe": 20, "Moderate": 12, "Mild": 6, 
                "Visible": 10, "High": 10, "Balanced": 0, "Small": 2, 
                "Not detected": 0, "Smooth": 0, "Clear": 0
            }
            for finding in ai_findings:
                severity = finding.get("severity", "Not detected")
                val = deductions.get(severity, 0)
                if val > 0:
                    base_score -= val
                    score_breakdown.append(f"⚠️ {severity} {finding.get('condition').lower()} (-{val}pts)")
                elif severity in ["Not detected", "Smooth", "Clear", "Balanced"]:
                    cond = finding.get('condition').lower()
                    if cond != "skin texture" and cond != "oiliness":  # simple filter
                        score_breakdown.append(f"✅ Clear {cond} (+0pts)")
                    elif cond == "skin texture":
                        score_breakdown.append(f"✅ Smooth skin texture (+0pts)")
            
            # --- Lifestyle & Questionnaire Deductions / Bonuses ---
            try:
                sleep = float(user_data["sleep"])
                if sleep < 6:
                    base_score -= 5
                    score_breakdown.append("⚠️ Low sleep hours (-5pts)")
                elif sleep >= 7:
                    base_score += 10
                    score_breakdown.append("✅ Good sleep hours (+10pts)")
            except: pass

            if user_data["water"] == "Less than 1 liter":
                base_score -= 5
                score_breakdown.append("⚠️ Low water intake (-5pts)")
            elif user_data["water"] == "More than 2 liters":
                base_score += 5
                score_breakdown.append("✅ Great water intake (+5pts)")

            if user_data["sunscreen"] == "No":
                base_score -= 10
                score_breakdown.append("⚠️ Skipping sunscreen (-10pts)")
            else:
                base_score += 5
                score_breakdown.append("✅ Daily sunscreen (+5pts)")
                
            climate = user_data.get("climate", "").lower()
            if "humid" in climate:
                base_score -= 5
                score_breakdown.append("⚠️ Humid climate risk (-5pts)")

            if user_data["condition_severity"] == "Severe":
                base_score -= 8
                score_breakdown.append("⚠️ Severe reported concern (-8pts)")
            elif user_data["condition_severity"] == "Moderate":
                base_score -= 4
                score_breakdown.append("⚠️ Moderate reported concern (-4pts)")

            return max(30, min(100, base_score)), score_breakdown

        skin_health_score, score_breakdown = calculate_skin_score(ai_results_enriched, data)

        # 3. Deterministic Logic for Result
        if skin_health_score >= 85:
            result_text = "Good Skin Health 🌟"
        elif skin_health_score >= 65:
            result_text = "Average Skin Health ⚠️"
        elif skin_health_score >= 45:
            result_text = "Needs Attention 🔴"
        else:
            result_text = "Needs Immediate Care 🚨"

        import copy
        base_routine = SKIN_ROUTINES.get(data["skin_type"], SKIN_ROUTINES["Combination"])
        routine = copy.deepcopy(base_routine)

        # ====== GEMINI PERSONALIZED GENERATION ======
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            import urllib.request
            import json
            prompt = f"""You are an expert AI dermatologist generating a personalized skincare report and routine.
A user has provided the following skin profile and AI image analysis results.
Profile:
- Age: {data['age']}, Gender: {data['gender']}, Climate: {data['climate']}
- Skin Type: {data['skin_type']}
- Goal/Main Focus: {data['goal']}
- Concerns: {data['concern']}
- Daily Sunscreen: {data['sunscreen']}
- Allergies: {data['allergies']}
- Sleep: {data['sleep']} hrs, Water: {data['water']}
- Budget: {data['budget']}, Time Available: {data['time_spend']}

AI Vision Findings:
{json.dumps(ai_results_enriched)}

Apply the following logic explicitly if matched:
- If user selected 'Acne' concern + AI confirmed it: Add salicylic acid/benzoyl peroxide to routine. Add 'Avoid comedogenic products' warning.
- If user said No sunscreen: Add a critical red warning recommending immediate SPF addition.
- If user has allergies: Add 'Always patch test' prominently and flag common allergens in avoid list.
- If sleep < 6 hours: Add a lifestyle tip explaining that poor sleep increases cortisol which worsens breakouts/dullness.
- If water is less than 1 liter: Flag dehydration as a contributor to dryness/dullness.
- If budget = 'Budget-friendly': Suggest only drugstore/affordable product categories like Cerave, Cetaphil, Ordinary.
- If time = 'Under 5 min': Provide a simplified maximum 3-step routine.
- Add estimated time per step (e.g., '30 sec') and dynamically include *why* each product is recommended (e.g., 'Gel cleanser — removes excess oil').
- Include an array of Key Ingredients to look for.

Return ONLY a JSON response in the following exact format, with NO markdown formatting:
{{
  "routine": {{
    "morning": ["Step 1 info (30 sec) - Why...", "Step 2..."],
    "night": ["Step 1...", "Step 2..."],
    "precautions": ["Precaution 1...", "Precaution 2..."],
    "what_to_avoid": ["Avoid 1...", "Avoid 2..."],
    "remedies": ["Remedy 1...", "Remedy 2..."]
  }},
  "lifestyle": ["Tip 1...", "Tip 2..."],
  "key_ingredients": ["Niacinamide", "Vitamin C", "Salicylic Acid"],
  "warnings": ["CRITICAL WARNING if applicable, else empty string"]
}}"""
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                payload = json.dumps({
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
                }).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=15) as response:
                    res_body = json.loads(response.read().decode("utf-8"))
                    text = res_body["candidates"][0]["content"]["parts"][0]["text"]
                    clean = text.replace("```json","").replace("```","").strip()
                    generated_report = json.loads(clean)
                    routine = generated_report.get("routine", routine)
                    lifestyle = generated_report.get("lifestyle", [])
                    key_ingredients = generated_report.get("key_ingredients", [])
                    warnings = generated_report.get("warnings", [])
            except Exception as e:
                print(f"Gemini routine generation failed: {e}")
                lifestyle = []
                key_ingredients = []
                warnings = []
                pass
        else:
            lifestyle = []
            key_ingredients = []
            warnings = []
        # ============================================

        # 4. Dynamic Routine adjustments (Fallback if Gemini fails or lacks key info)
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

        # 5. Build Dynamic Lifestyle, Ingredients, and Avoid Lists Deterministically
        dynamic_ingredients = []
        is_spots = data["ai_spots"] or concern in ["Pigmentation", "Dark Spots"]
        is_oily = data["ai_oily"] or data["skin_type"] == "Oily"
        is_acne = data["ai_pimples"] or concern == "Acne"
        
        dynamic_ingredients.append({"name": "SPF 50", "desc": "Universal protection against UV damage & aging."})
        
        if is_spots:
            dynamic_ingredients.extend([
                {"name": "Vitamin C", "desc": "Brightens dark spots & evens tone. Look for: Serums with 10-20% concentration"},
                {"name": "Alpha Arbutin", "desc": "Gently fades hyperpigmentation. Look for: Serums or creams"},
                {"name": "Tranexamic Acid", "desc": "Reduces stubborn dark spots. Look for: Serums"}
            ])
        if is_oily:
            dynamic_ingredients.extend([
                {"name": "Niacinamide", "desc": "Regulates oil production & minimizes pores. Look for: 5-10% Serums"},
                {"name": "Zinc", "desc": "Controls sebum and reduces inflammation"}
            ])
        if ("Visible Pores" in str(ai_results_enriched)):
            dynamic_ingredients.extend([
                {"name": "Retinol", "desc": "Increases cell turnover and reduces pore visibility"},
                 {"name": "Clay", "desc": "Absorbs excess oil and tightens pores"}
            ])
        if concern == "Dryness / Tanning" or data["skin_type"] == "Dry":
             dynamic_ingredients.extend([
                {"name": "Hyaluronic Acid", "desc": "Draws moisture into the skin. Look for: Hydrating serums"},
                {"name": "Ceramides", "desc": "Repairs the skin barrier. Look for: Moisturizers"},
                {"name": "Squalane", "desc": "Lightweight, non-comedogenic hydration"}
            ])
        if is_acne:
            dynamic_ingredients.extend([
                {"name": "Benzoyl Peroxide", "desc": "Kills acne-causing bacteria. Look for: Spot treatments"},
                {"name": "Salicylic Acid", "desc": "Cleans deep inside pores. Look for: 2% BHA Toners"},
                {"name": "Tea Tree", "desc": "Natural antibacterial for mild breakouts"}
            ])
            
        dynamic_avoid = []
        if is_spots:
             dynamic_avoid.extend([
                 "Avoid unprotected sun exposure — worsens pigmentation",
                 "Avoid photosensitizing actives (AHA/BHA) without SPF",
                 "Avoid DIY lemon/lime juice treatments"
             ])
        clm = data.get("climate", "").lower()
        if "humid" in clm:
             dynamic_avoid.extend([
                 "Avoid heavy occlusive creams — trap sweat & bacteria",
                 "Avoid skipping face wash after sweating",
                 "Avoid thick balm-based sunscreens on T-zone"
             ])
        if is_oily:
             dynamic_avoid.extend([
                 "Avoid pore-clogging (comedogenic) ingredients",
                 "Avoid over-washing — strips oil, causes rebound oiliness",
                 "Avoid alcohol-based toners"
             ])
        if request.form.get("spot_type") == "Post-acne marks" or is_acne:
             dynamic_avoid.extend([
                 "Avoid picking or touching healed spots",
                 "Avoid high-strength retinol without building up slowly"
             ])
        if data["water"] == "Less than 1 liter":
             dynamic_avoid.append("Avoid excess caffeine/alcohol — dehydrates skin further")
        if data["sunscreen"] == "No":
             dynamic_avoid.append("⚠️ CRITICAL: Avoiding SPF is your #1 skin damage risk")
             
        if not dynamic_avoid: 
             dynamic_avoid = ["Avoid sleeping with makeup on", "Avoid touching your face throughout the day"]
             
        # --- CONSULT CTA LOGIC ---
        show_consult_cta = False
        consult_reasons = []
        if skin_health_score < 70:
            show_consult_cta = True
            consult_reasons.append("Overall skin health score (<70) requires professional guidance")
        if data.get("problem_duration") == "More than 6 months":
            show_consult_cta = True
            consult_reasons.append("Persistent condition lasting over 6 months")
        for f in ai_results_enriched:
            sev = f.get("severity", "").lower()
            cond = f.get("condition", "")
            conf = int(f.get("confidence", 0))
            if sev in ["moderate", "severe", "visible", "high", "large"]:
                show_consult_cta = True
                consult_reasons.append(f"{sev.title()} {cond.lower()} treatment options")
            elif conf > 90 and sev in ["moderate", "severe", "visible", "high", "large"]:
                show_consult_cta = True
                consult_reasons.append(f"High confidence AI detection of {cond.lower()}")
        consult_reasons = list(dict.fromkeys(consult_reasons))

        dynamic_lifestyle = []
        try:
            sleep = float(data["sleep"])
            if sleep < 6:
                dynamic_lifestyle.append("⚠️ Your 5hr sleep increases cortisol — directly worsens dark spots and pore size. Target: 7-8hrs.")
            elif sleep < 8:
                dynamic_lifestyle.append("💤 You're close — try to reach 8hrs for optimal skin repair during sleep cycles.")
            else:
                dynamic_lifestyle.append("✅ Great sleep habits — skin repairs itself during deep sleep, keep it up.")
        except: pass

        wt = data.get("water", "")
        if wt == "Less than 1 liter":
            dynamic_lifestyle.append("⚠️ Severely under-hydrated — skin looks dull and pores appear larger. Aim for 2-3L daily.")
        elif wt == "1-2 liters":
            dynamic_lifestyle.append("💧 Slightly low for your skin goals. Add 2 extra glasses daily to improve tone.")
        elif wt == "More than 2 liters" or wt == "More than 2 liters":
            dynamic_lifestyle.append("✅ Well hydrated — hydration helps flush toxins that cause breakouts.")

        if "humid" in clm:
            dynamic_lifestyle.append("🌡️ Humid climate increases sebum production — use lightweight, water-based products and cleanse twice daily.")
        elif "dry" in clm:
            dynamic_lifestyle.append("🏜️ Dry climate strips moisture barrier — layer hydrating toner before moisturizer.")
        elif "tropical" in clm:
            dynamic_lifestyle.append("☀️ High UV exposure in tropical climate — reapply SPF every 2hrs outdoors.")

        if is_spots:
            dynamic_lifestyle.append("🥦 Eat Vitamin C rich foods: oranges, bell peppers, kiwi — natural brightening support.")
        elif is_acne:
            dynamic_lifestyle.append("🥛 Consider reducing dairy and high-GI foods — linked to hormonal breakouts.")
        else:
            dynamic_lifestyle.append("🫐 Antioxidant-rich diet (berries, green tea) reduces skin inflammation.")
            
        routine["what_to_avoid"] = dynamic_avoid
        lifestyle = dynamic_lifestyle
        key_ingredients = dynamic_ingredients

        try:
            report = SkinReport(
                user_id=current_user.id,
                age=data['age'],
                gender=data['gender'],
                image_file=image_path,
                skin_type=data["skin_type"],
                concern=data["concern"],
                facewash=data["facewash"],
                moisturizer=data["moisturizer"],
                sunscreen=data["sunscreen"],
                sleep=data["sleep"],
                water=data["water"],
                ai_pimples=data["ai_pimples"],
                ai_oily=data["ai_oily"],
                ai_spots=data["ai_spots"],
                result=result_text,
                skin_health_score=skin_health_score,
                timestamp=datetime.datetime.utcnow()
            )
            db.session.add(report)
            db.session.commit()
            report_id = report.id
        except Exception as e:
            print(f"DB save error: {e}")
            report_id = None

        # --- SAVE TO SESSION FOR PDF GENERATOR ---
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

        # Fetch previous report for comparison
        previous_report = None
        if report_id:
            previous_report = SkinReport.query.filter(SkinReport.user_id == current_user.id, SkinReport.id < report_id).order_by(SkinReport.id.desc()).first()

        report_count = SkinReport.query.filter_by(user_id=current_user.id).count() if current_user.is_authenticated else 0
        first_scan = report_count <= 1

        # If this is an AJAX/fetch request from the new wizard UI, return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
           'application/json' in request.headers.get('Accept', ''):
            return jsonify({
                "status": "saved", 
                "result": result_text,
                "score": skin_health_score,
                "score_breakdown": score_breakdown,
                "show_consult_cta": show_consult_cta,
                "consult_reasons": consult_reasons,
                "ai_results": ai_results_enriched,
                "routine": routine,
                "report_id": report_id,
                "previous_score": previous_report.skin_health_score if previous_report else None,
                "first_scan": first_scan
            })

        # Fallback: render report for direct form submission
        return render_template(
            'skin_report.html',
            data=data,
            result=result_text,
            routine=routine,
            lifestyle=lifestyle,
            key_ingredients=key_ingredients,
            warnings=warnings,
            image_path=image_path,
            ai_results=ai_results_enriched,
            score=skin_health_score,
            score_breakdown=score_breakdown,
            show_consult_cta=show_consult_cta,
            consult_reasons=consult_reasons,
            current_date=datetime.datetime.now().strftime("%d %b %Y, %I:%M %p"),
            previous_report=previous_report,
            previous_score=previous_report.skin_health_score if previous_report else None,
            first_scan=first_scan
        )

    return render_template('skin_analysis.html')
    


@app.route('/api/analyze-image', methods=['POST'])
@login_required
def analyze_image_api():
    try:
        image_data = request.form.get('image')
        file = request.files.get('file')
        
        img = None
        if image_data and "base64" in image_data:
            try:
                header, encoded = image_data.split(",", 1)
                data = base64.b64decode(encoded)
                img = Image.open(io.BytesIO(data))
            except Exception as e:
                return jsonify({"error": f"Invalid base64: {str(e)}"}), 400
        elif file:
            img = Image.open(file)
        
        if not img:
            return jsonify({"error": "No image provided"}), 400
        
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "Gemini API Key missing"}), 500

        # Encode image to base64 for Gemini
        import io
        import base64
        import json
        import urllib.request
        import time

        img_byte_arr = io.BytesIO()
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(img_byte_arr, format='JPEG')
        encoded_string = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

        prompt = """You are a professional AI dermatologist analyzing a patient's face photo.
Analyze the skin for the following 8 conditions and categorize their severity:
1. Pimples / Acne (Not detected / Mild / Moderate / Severe)
2. Oiliness (Low / Balanced / High)
3. Dark Spots / Hyperpigmentation (Not detected / Mild / Visible)
4. Dryness / Flakiness (Not detected / Signs present)
5. Redness / Irritation (Not detected / Mild redness)
6. Visible Pores (Small / Moderate / Large)
7. Skin Texture (Smooth / Slightly rough / Rough)
8. Under-eye Circles (Not detected / Mild / Visible)

Also estimate the following based on the photo:
9. Skin Tone (Fair / Medium / Tan / Deep)
10. Estimated Skin Age (Return an integer)

Return ONLY a JSON response in the following exact format:
{
  "findings": [
    {"condition": "Pimples / Acne", "severity": "Mild", "detected": true, "confidence": 88},
    ... (include all 8 conditions)
  ],
  "skin_tone": "Medium",
  "estimated_age": 28,
  "overall_score": 72,
  "skin_summary": "One sentence summary of the overall skin health."
}
IMPORTANT: Provide valid JSON only, no markdown blocks."""

        MODELS_TO_TRY = ["gemini-1.5-flash", "gemini-2.5-flash", "gemini-flash-latest"]
        for model in MODELS_TO_TRY:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                payload = json.dumps({
                    "contents": [{"parts": [
                        {"text": prompt},
                        {
                           "inlineData": {
                             "mimeType": "image/jpeg",
                             "data": encoded_string
                           }
                        }
                    ]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                }).encode("utf-8")

                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=30) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    text = result["candidates"][0]["content"]["parts"][0]["text"]
                    clean = text.replace("```json","").replace("```","").strip()
                    parsed = json.loads(clean)
                    
                    # Ensure backward compatibility for earlier routing
                    parsed["pimples"] = any(f["condition"] == "Pimples / Acne" and f["detected"] for f in parsed.get("findings", []))
                    parsed["oily"] = any(f["condition"] == "Oiliness" and f["severity"] == "High" for f in parsed.get("findings", []))
                    parsed["spots"] = any(f["condition"] == "Dark Spots / Hyperpigmentation" and f["detected"] for f in parsed.get("findings", []))

                    return jsonify(parsed)

            except Exception as e:
                print(f"Gemini error with {model}: {e}")
                continue

        return jsonify({"error": "All AI models failed"}), 500
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500



# ================== HELPERS ==================
def encode_input(data):
    skin_map = {"Oily": 0, "Dry": 1, "Combination": 2, "Sensitive": 3}
    concern_map = {"Acne": 0, "Pigmentation": 1, "Tanning": 2, "Dark Spots": 3, "None": 4}
    yes_no = {"Yes": 1, "No": 0}
    yes_no_lower = {"yes": 1, "no": 0}
    sleep_map = {"good": 1, "less": 0}
    water_map = {"good": 1, "less": 0}

    return np.array([[
        skin_map[data["skin_type"]],
        concern_map[data["concern"]],
        yes_no[data["facewash"]],
        yes_no[data["moisturizer"]],
        yes_no_lower[data["sunscreen"]],
        sleep_map[data["sleep"]],
        water_map[data["water"]],
    ]])
    
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'jfif', 'webp'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ================== TREND VERIFICATION ==================
def verify_trend(text, skin_type):
    text = text.lower().strip()
    
    # Expanded Database with synonyms and common typos
    harmful_keywords = {
        "lemon": "Lemon is highly acidic (pH 2) and can disrupt the skin barrier, causing irritation and photosensitivity.",
        "lime": "Lime causes phytophotodermatitis (blistering when exposed to sun) and is too acidic for skin.",
        "baking soda": "Baking soda is too alkaline (pH 9) and destroys the acid mantle, leading to bacteria growth and dryness.",
        "toothpaste": "Toothpaste contains drying agents (menthol, baking soda) that can chemically burn the skin.",
        "bleach": "Bleach causes severe chemical burns and permanent damage to skin melanin.",
        "glue": "Pore strips or glue can tear the skin and cause broken capillaries.",
        "vinegar": "Undiluted vinegar can burn the skin. Always dilute Apple Cider Vinegar.",
        "garlic": "Garlic can cause severe chemical burns on skin contact.",
        "cinnamon": "Cinnamon is a common allergen and can cause contact dermatitis.",
        "rubbing alcohol": "Strips natural oils completely, damaging the skin barrier."
    }

    safe_keywords = {
        "aloe": "Aloe Vera is soothing and hydrating.",
        "aleovera": "Aloe Vera is soothing and hydrating (Typo detected: 'aleovera').", # Handling typo
        "aloevera": "Aloe Vera is soothing and hydrating.",
        "rose water": "Rose water balances pH and hydrates gently.",
        "rosewater": "Rose water balances pH and hydrates gently.",
        "oatmeal": "Colloidal oatmeal soothes eczema and sensitive skin.",
        "oats": "Oats are gentle exfoliants and soothing agents.",
        "honey": "Honey is antibacterial and a natural humectant.",
        "curd": "Curd (Yogurt) contains lactic acid for gentle exfoliation.",
        "yogurt": "Yogurt contains lactic acid for gentle exfoliation.",
        "yoghurt": "Yogurt contains lactic acid for gentle exfoliation.",
        "turmeric": "Turmeric is anti-inflammatory and brightens skin.",
        "haldi": "Turmeric (Haldi) is anti-inflammatory.",
        "besan": "Gram flour (Besan) cleanses oil but can be drying for dry skin.",
        "gram flour": "Gram flour cleanses oil.",
        "cucumber": "Cucumber hydrates and reduces puffiness.",
        "green tea": "Green tea is rich in antioxidants and reduces oil.",
        "ice": "Icing reduces inflammation and puffiness (use a cloth, not direct ice).",
        "icing": "Icing reduces inflammation and puffiness.",
        "rice water": "Rice water brightens and soothes skin.",
        "coffee": "Coffee scrubs can be harsh, but caffeine reduces puffiness."
    }

    bad_matches = [key for key in harmful_keywords if key in text]
    good_matches = [key for key in safe_keywords if key in text]

    if bad_matches:
        items = ", ".join([f"'{item}'" for item in bad_matches])
        reasons = " ".join([harmful_keywords[item] for item in bad_matches])
        
        message = f"Detected {items}: {reasons} Not recommended for {skin_type} skin."
        if good_matches:
            good_items = ", ".join([f"'{item}'" for item in good_matches])
            good_reasons = " ".join([safe_keywords[item] for item in good_matches])
            message += f" (Also found safe items {good_items}: {good_reasons})"
            
        return "❌ Harmful Trend", message, "danger"

    if good_matches:
        items = ", ".join([f"'{item}'" for item in good_matches])
        reasons = " ".join([safe_keywords[item] for item in good_matches])
        
        # Skin type specific nuances
        caution_items = [item for item in good_matches if item in ["besan", "gram flour", "lemon", "clay"]]
        if skin_type in ["Sensitive", "Dry"] and caution_items:
             caution_items_str = ", ".join([f"'{item}'" for item in caution_items])
             return "⚠️ Use with Caution", f"Detected {items}. {reasons} Note: {caution_items_str} can be drying for {skin_type} skin.", "warning"
        
        return "✅ Safe Trend", f"Detected {items}: {reasons} Generally safe for {skin_type} skin.", "success"

    return "⚠️ Unverified Trend", "No specific dermatological evidence found for this query in our database. Patch test required.", "warning"

# ================== ROUTES ==================
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/test-api')
def test_api():
    key = os.environ.get("GEMINI_API_KEY")
    return {
        "key_loaded": bool(key),
        "key_preview": key[:8] + "..." if key else "NOT FOUND"
    }


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and user.password and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash("Invalid email or password")
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if User.query.filter_by(email=request.form['email']).first():
            flash("Email already exists")
        else:
            user = User(
                name=request.form['name'],
                email=request.form['email'],
                phone=request.form['phone'],
                password=generate_password_hash(request.form['password'])
            )
            db.session.add(user)
            db.session.commit()
            flash("Account created successfully!", "success")
            return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


# ================== SKINCARE ROUTINES DATA ==================
SKIN_ROUTINES = {
    "Oily": {
        "morning": [
            "Gentle foaming cleanser with Salicylic Acid",
            "Alcohol-free toner (Niacinamide or Witch Hazel)",
            "Lightweight, oil-free moisturizer (Gel-based)",
            "Broad-spectrum SPF 50 sunscreen (Matte finish)"
        ],
        "night": [
            "Double cleanse (Oil cleanser + Water-based cleanser)",
            "Exfoliating serum (BHA/Salicylic Acid) - 2x/week",
            "Retinol or Niacinamide serum",
            "Lightweight night cream or gel moisturizer"
        ],
        "precautions": [
            "Don't over-wash your face (strips natural oils)",
            "Avoid touching your face to prevent acne transfer",
            "Always patch-test new products first"
        ],
        "what_to_avoid": [
            "Heavy, pore-clogging oils (coconut oil, mineral oil)",
            "Alcohol-based astringents",
            "Thick occlusive creams"
        ],
        "remedies": [
            "Clay mask (Kaolin/Bentonite) once a week",
            "Green tea toner for oil control",
            "Aloe vera gel for inflammation"
        ]
    },
    "Dry": {
        "morning": [
            "Creamy, hydrating cleanser (unscented)",
            "Hydrating toner (Hyaluronic Acid/Glycerin)",
            "Rich moisturizer with Ceramides/Shea Butter",
            "Broad-spectrum SPF 50 sunscreen (Dewy finish)"
        ],
        "night": [
            "Oil-based cleanser or cleansing balm",
            "Hydrating serum (Hyaluronic Acid/Vitamin E)",
            "Thick night cream using peptides/ceramides",
            "Facial oil (Rosehip/Jojoba) to seal moisture"
        ],
        "precautions": [
            "Don't use overly hot water (strips moisture)",
            "Don't skip moisturizer even if it feels humid",
            "Apply moisturizer while skin is still damp"
        ],
        "what_to_avoid": [
            "Alcohol-based toners and astringents",
            "Harsh physical scrubs (walnut shells)",
            "Foaming cleansers with SLS/SLES"
        ],
        "remedies": [
            "Honey and oatmeal mask for hydration",
            "Mashed avocado mask",
            "Coconut oil massage before bed"
        ]
    },
    "Combination": {
        "morning": [
            "Gentle gel cleanser",
            "Balancing toner (Rose wafer/Green tea)",
            "Light moisturizer for T-zone, cream for cheeks",
            "SPF 50 sunscreen (Hybrid formulation)"
        ],
        "night": [
            "Micellar water + Gentle cleanser",
            "Lactic Acid serum (mild exfoliation)",
            "Niacinamide for oil control & brightness",
            "Gel-cream moisturizer"
        ],
        "precautions": [
            "Don't use harsh scrubs on dry areas",
            "Treat T-zone and cheeks separately if needed",
            "Always patch-test active ingredients"
        ],
        "what_to_avoid": [
            "Heavy generic creams on the T-zone",
            "Harsh alcohol-based toners",
            "Using stripping acne wash on dry cheeks"
        ],
        "remedies": [
            "Multimasking (Clay on T-zone, Hydrating on cheeks)",
            "Cucumber juice toner",
            "Yogurt and honey mask"
        ]
    },
    "Sensitive": {
        "morning": [
            "Ultra-gentle, soap-free cleanser",
            "Soothing toner (Chamomile/Calendula)",
            "Hypoallergenic, fragrance-free moisturizer",
            "Mineral sunscreen (Zinc Oxide/Titanium Dioxide)"
        ],
        "night": [
            "Gentle cleansing lotion",
            "Soothing serum (Centella Asiatica/Panthenol)",
            "Barrier repair cream (Ceramides)",
            "Avoid active acids/retinoids unless prescribed"
        ],
        "precautions": [
            "Patch test every new product",
            "If irritated, heavily pare down your routine",
            "Don't over-exfoliate"
        ],
        "what_to_avoid": [
            "Artificial fragrances and heavy essential oils",
            "Chemical sunscreens (Oxybenzone/Avobenzone)",
            "Harsh physical scrubs (exfoliants)",
            "High concentration AHAs/BHAs"
        ],
        "remedies": [
            "Oatmeal water wash (soothing)",
            "Aloe vera gel (pure)",
            "Cold compress for redness"
        ]
    },
    "Normal": {
        "morning": [
            "Gentle balanced cleanser",
            "Hydrating toner with antioxidants",
            "Lightweight daily moisturizer (SPF included or separate)",
            "Broad-spectrum SPF 50 sunscreen"
        ],
        "night": [
            "Gentle cleansing milk or gel",
            "Vitamin C serum (brightening)",
            "Light niacinamide or peptide serum",
            "Gel-cream moisturizer"
        ],
        "precautions": [
            "Don't skip sunscreen even if skin feels good",
            "Maintain consistency with your routine",
            "Remove makeup fully before bed"
        ],
        "what_to_avoid": [
            "Over-exfoliating (max 2x/week)",
            "Harsh stripping soaps",
            "Unnecessary heavy acidic treatments"
        ],
        "remedies": [
            "Rose water mist for freshness",
            "Honey mask for glow",
            "Green tea compress for antioxidants"
        ]
    }
}


@app.route('/download-report')
@login_required
def download_report():
    from datetime import datetime
    
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
        return redirect(url_for('dashboard'))

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # --- Header ---
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawCentredString(width / 2, height - 50, "Skin Analysis Report")
    
    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(width / 2, height - 70, f"Generated for: {current_user.name}")
    pdf.line(50, height - 80, width - 50, height - 80)

    # --- Print Date & Score ---
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
        img_path = os.path.join(UPLOAD_FOLDER, data["image_path"])
        if os.path.exists(img_path):
            try:
                # Draw small thumbnail of user's face in the right corner
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
        findings_list = [] # Fail-safe if leftover session logic applies

    for f in findings_list:
        condition = f.get("condition", "Condition")
        severity = str(f.get("severity", "Low")).lower()
        
        # Parse 'clear' equivalent
        is_clear = ("not detected" in severity or "balanced" in severity or severity == "smooth" or severity == "low" or severity == "small")
        
        status_text = "Found/Clear: Clear" if is_clear else f"Detected (Severity: {f.get('severity', '')})"
        color = (0, 0.5, 0) if is_clear else (0.8, 0, 0)

        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawString(60, y, f"• {condition}: ")
        pdf.setFillColorRGB(*color)
        pdf.drawString(190, y, status_text)
        pdf.setFillColorRGB(0, 0, 0) # Reset to black
        
        y -= 15
        if y < 50:
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica", 11)

    def draw_section(title, items, start_y):
        # Draw a thin colored divider line before the section
        pdf.setStrokeColorRGB(0.86, 0.35, 0.47) # Pink/Rose color
        pdf.setLineWidth(0.5)
        pdf.line(50, start_y + 20, width - 50, start_y + 20)
        
        # Draw a colored rectangle bar next to the title
        pdf.setFillColorRGB(0.86, 0.35, 0.47)
        pdf.rect(50, start_y - 2, 5, 14, fill=1, stroke=0)
        
        pdf.setFillColorRGB(0.86, 0.35, 0.47)
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(62, start_y, title)
        
        # Reset color to black for text
        pdf.setFillColorRGB(0, 0, 0)
        start_y -= 20
        pdf.setFont("Helvetica", 11)
        
        for item in items:
            # Simple text wrapping
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
            
            if start_y < 50: # New Page
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
        buffer,
        as_attachment=True,
        download_name=f"Skin_Report_{current_user.name}.pdf",
        mimetype="application/pdf"
    )

import urllib.request
import urllib.error
import json
import os
import time

_last_gemini_call = 0

def analyze_with_gemini_vision(image_path, skin_type):
    global _last_gemini_call
    api_key = os.environ.get("GEMINI_API_KEY")
    
    elapsed = time.time() - _last_gemini_call
    if elapsed < 15:
        wait = 15 - elapsed
        print(f"Rate limit protection: waiting {wait:.1f}s")
        time.sleep(wait)
        
    _last_gemini_call = time.time()
    
    if not api_key:
        return None

    MODELS_TO_TRY = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-flash-latest",
        "gemini-pro"
    ]

    try:
        import base64
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        ext = image_path.split('.')[-1].lower()
        mime_type = f"image/{ext}" if ext != 'jpg' else "image/jpeg"
        if ext == 'jfif': mime_type = "image/jpeg"
    except Exception as e:
        print(f"Failed to read image for Gemini: {e}")
        return None

    prompt = f"""You are a cosmetic ingredient safety expert.
Skin type: {skin_type}

Extract ALL real INCI cosmetic ingredient names from the provided image of a product label.
Ignore all marketing words, benefit claims, brand names, packaging info, and non-ingredient text.
If there are no readable ingredients in the image, return an empty array [].

Return a JSON array of objects with the exact keys:
"name" (string), "status" (string: must be "Safe", "Caution", or "Avoid"), "reason" (string: max 6 words), "skinTypeCompatibility" (boolean)."""

    for model in MODELS_TO_TRY:
        for attempt in range(2):
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                
                payload = json.dumps({
                    "contents": [{"parts": [
                        {"text": prompt},
                        {
                           "inlineData": {
                             "mimeType": mime_type,
                             "data": encoded_string
                           }
                        }
                    ]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 8192,
                        "responseMimeType": "application/json"
                    },
                    "safetySettings": [
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                    ]
                }).encode("utf-8")

                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )

                with urllib.request.urlopen(req, timeout=60) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    text = result["candidates"][0]["content"]["parts"][0]["text"]
                    clean = text.replace("```json","").replace("```","").strip()
                    try:
                        parsed = json.loads(clean)
                        print(f"SUCCESS with model {model}: {len(parsed)} ingredients")
                        return parsed
                    except Exception as je:
                        finish_reason = result["candidates"][0].get("finishReason", "UNKNOWN")
                        print(f"Failed to parse JSON for {model}. Finish reason: {finish_reason}")
                        print(f"Raw text first 200 chars: {clean[:200]}")
                        raise je

            except urllib.error.HTTPError as e:
                error_body = e.read().decode()
                print(f"Model {model} attempt {attempt+1}: HTTP {e.code}")
                if e.code == 429:
                    if "GenerateRequestsPerDay" in error_body or "RESOURCE_EXHAUSTED" in error_body:
                        print("Quota exhausted for this model, trying next...")
                        break
                    print("Rate limited, waiting 10s...")
                    time.sleep(10)
                    continue
                elif e.code == 404:
                    print(f"Model {model} not found, trying next...")
                    break  # try next model
                else:
                    print(f"Error: {error_body[:200]}")
                    break
            except Exception as e:
                print(f"Model {model} error: {e}")
                break

    print("All models failed, using offline fallback")
    return None

@app.route('/ingredient-scan', methods=['GET', 'POST'])
@login_required
def ingredient_scan():
    scan_results = None

    if request.method == 'POST':
        skin_type = request.form.get('skin_type')
        file = request.files.get('image')

        if not skin_type or not file:
            flash("Please select skin type and upload image")
            return render_template('ingredient_scan.html')

        if not allowed_file(file.filename):
            flash("Only JPG, PNG, WEBP, JFIF images allowed")
            return render_template('ingredient_scan.html')

        filename = file.filename
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)

        try:
            parsed_results = []
            mode_used = "offline"

            # --- TIER 1: GEMINI VISION API ---
            try:
                parsed_results = analyze_with_gemini_vision(path, skin_type)
                if parsed_results and isinstance(parsed_results, list) and len(parsed_results) > 0:
                    mode_used = "ai"
                else:
                    parsed_results = []
            except Exception as e:
                print(f"Gemini Vision API failed/timeout: {e}")
                parsed_results = []

            # --- TIER 2: FALLBACK DATABASE WITH PYTESSERACT OCR ---
            if not parsed_results:
                mode_used = "offline"
                raw_text = pytesseract.image_to_string(Image.open(path))
                lower_text = raw_text.lower()
                
                # --- STEP 1: Extract ingredients section ---
                import re
                trigger_keywords = ["ingredients:", "ingredients :", "composition:", "contains:", "inci:"]
                ingredients_section = lower_text
                for tk in trigger_keywords:
                    if tk in lower_text:
                        ingredients_section = lower_text.split(tk, 1)[1]
                        break
                
                # --- STEP 2: Filter out non-ingredient tokens ---
                raw_tokens = re.split(r'[,;\n•]+', ingredients_section)
                
                stop_words = {"juicy", "smooth", "clean", "bright", "deep", "light", "rich", "pure", "fresh", "gentle", "advanced", "natural", "new", "with", "for", "and", "the", "your", "skin", "providing", "underneath", "revealing", "surface", "chemistry", "tone", "spots", "glow", "formula", "complex", "technology", "system", "blend"}
                marketing_regex = re.compile(r'^(juicy|chemistry|surface|providing|underneath|brighter|revealing|smoother|complex|formula|serum|cream|gel|lotion|toner|moisturizer|cleanser|scrub|mask|essence|ampoule|treatment|solution|boost|care|repair|restore|renew|refresh|hydrate|glow|radiance|luminous)$', re.IGNORECASE)
                
                filtered_tokens = []
                for t in raw_tokens:
                    t = t.strip()
                    if not t: continue
                    if len(t) < 4: continue
                    if re.match(r'^[\d.%]+$', t): continue
                    if t in ["ml", "mg", "oz", "spf"]: continue
                    
                    words = t.split()
                    if len(words) == 1:
                        w = words[0]
                        if w in stop_words or marketing_regex.match(w):
                            continue
                            
                    filtered_tokens.append(t)
                    
                ingredients_text = ", ".join(filtered_tokens)
                
                # We already know parsed_results is empty if we reached here
                
                # Fallback db dictionaries below...
                # --- TIER 2: FALLBACK DATABASE ---
            if not parsed_results:
                mode_used = "offline"
                
                safe_db = {
                    "niacinamide": {"compat": ["all"], "desc": "Reduces pores, controls oil, brightens skin"},
                    "hyaluronic acid": {"compat": ["all"], "desc": "Deep hydration, plumps skin"},
                    "ceramides": {"compat": ["all"], "desc": "Restores skin barrier"},
                    "glycerin": {"compat": ["all"], "desc": "Humectant, draws moisture"},
                    "aloe vera": {"compat": ["oily", "sensitive"], "desc": "Soothes inflammation"},
                    "green tea": {"compat": ["all"], "desc": "Antioxidant, anti-inflammatory", "aliases": ["green tea extract"]},
                    "vitamin c": {"compat": ["normal", "dry"], "desc": "Brightens, anti-aging", "aliases": ["ascorbic acid"]},
                    "salicylic acid": {"compat": ["oily", "acne", "acne-prone"], "desc": "Unclogs pores, exfoliates"},
                    "zinc oxide": {"compat": ["sensitive"], "desc": "Sun protection, calming"},
                    "shea butter": {"compat": ["dry", "normal"], "desc": "Deep moisturizing"},
                    "jojoba oil": {"compat": ["all"], "desc": "Balancing, non-comedogenic"},
                    "azelaic acid": {"compat": ["all"], "desc": "Reduces pigmentation and redness"},
                    "panthenol": {"compat": ["all"], "desc": "Healing, hydrating", "aliases": ["vitamin b5"]},
                    "neem": {"compat": ["oily", "acne", "acne-prone"], "desc": "Antibacterial, anti-acne", "aliases": ["azadirachta indica", "neem-ol", "neem extract"]},
                    "turmeric": {"compat": ["all"], "desc": "Anti-inflammatory, brightening", "aliases": ["curcuma longa", "haldi", "turmeric extract"]},
                    "rosemary": {"compat": ["oily"], "desc": "Antioxidant, antimicrobial", "aliases": ["rosmarinus officinalis", "rosemary leaf extract"]},
                    "sandalwood": {"compat": ["sensitive", "dry"], "desc": "Soothing, anti-inflammatory"},
                    "retinol": {"compat": ["normal", "dry"], "desc": "Anti-aging, cell turnover"},
                    "benzoyl peroxide": {"compat": ["oily", "acne", "acne-prone"], "desc": "Kills acne bacteria"},
                    "water": {"compat": ["all"], "desc": "Base ingredient, hydrates skin", "aliases": ["aqua", "eau"]},
                    "cetearyl alcohol": {"compat": ["all"], "desc": "Emollient, softens and smooths skin", "aliases": ["cetyl alcohol", "cetostearyl"]},
                    "cetearyl": {"compat": ["all"], "desc": "Fatty alcohol, skin conditioner", "aliases": ["cetyl"]},
                    "glyceryl stearate": {"compat": ["all"], "desc": "Emulsifier, helps skin retain moisture", "aliases": ["glyceryl stearate se"]},
                    "ethylhexanoate": {"compat": ["all"], "desc": "Lightweight emollient, non-greasy", "aliases": ["ethylhexyl"]},
                    "centella asiatica": {"compat": ["all"], "desc": "Soothing, healing, anti-inflammatory", "aliases": ["gotu kola", "cica"]},
                    "pterocarpus marsupium": {"compat": ["all"], "desc": "Ayurvedic extract, skin brightening", "aliases": ["indian kino", "vijayasar"]},
                    "carbomer": {"compat": ["all"], "desc": "Thickening agent, texture enhancer"},
                    "xanthan gum": {"compat": ["all"], "desc": "Natural thickener, skin feel enhancer", "aliases": ["guar gum"]},
                    "tocopherol": {"compat": ["all"], "desc": "Antioxidant, skin nourishing", "aliases": ["vitamin e", "tocopheryl acetate"]},
                    "allantoin": {"compat": ["all"], "desc": "Soothing, promotes healing"},
                    "stearic acid": {"compat": ["all"], "desc": "Fatty acid, skin conditioning", "aliases": ["palmitic acid"]},
                    "caprylic": {"compat": ["all"], "desc": "Lightweight moisturizer from coconut", "aliases": ["capric triglyceride"]},
                    "disodium edta": {"compat": ["all"], "desc": "Preservative booster, chelating agent", "aliases": ["edta"]}
                }
                caution_db = {
                    "fragrance": {"bad_compat": ["sensitive"], "desc": "May cause irritation or allergic reactions", "aliases": ["parfum"]},
                    "alcohol denat": {"bad_compat": ["dry", "sensitive"], "desc": "Can be drying with overuse"},
                    "essential oils": {"bad_compat": ["sensitive"], "desc": "Potential irritant"},
                    "kojic acid": {"bad_compat": ["sensitive"], "desc": "Brightening but can irritate"},
                    "lactic acid": {"bad_compat": ["sensitive"], "desc": "Exfoliant, start slow"},
                    "glycolic acid": {"bad_compat": ["sensitive", "dry"], "desc": "Strong exfoliant, use with care"},
                    "witch hazel": {"bad_compat": ["dry", "sensitive"], "desc": "Can be drying"},
                    "tea tree": {"bad_compat": ["sensitive"], "desc": "Antibacterial, must be diluted", "aliases": ["melaleuca", "tea tree oil"]},
                    "lemon": {"bad_compat": ["sensitive"], "desc": "Brightening but photosensitizing", "aliases": ["citrus limon"]},
                    "piper longum": {"compat": ["all"], "bad_compat": [], "desc": "Antioxidant, limited skin data"},
                    "triethanolamine": {"bad_compat": ["sensitive"], "desc": "pH adjuster, avoid if sensitive", "aliases": ["tea"]},
                    "dimethicone": {"bad_compat": ["oily"], "desc": "Smoothing but can trap debris", "aliases": ["silicone"]},
                    "sodium hydroxide": {"bad_compat": ["sensitive"], "desc": "pH balancer, used in tiny amounts", "aliases": ["potassium hydroxide"]},
                    "phenoxyethanol": {"bad_compat": ["sensitive"], "desc": "Preservative, generally safe at low %"},
                    "butylene glycol": {"bad_compat": ["sensitive"], "desc": "Humectant, potential irritant for sensitive", "aliases": ["propylene glycol"]},
                    "benzyl alcohol": {"bad_compat": ["sensitive"], "desc": "Preservative, may irritate sensitive skin"}
                }
                avoid_db = {
                    "sodium lauryl sulfate": {"desc": "Strips natural oils, causes irritation", "aliases": ["sls"], "bad_compat": ["sensitive", "dry"]},
                    "paraben": {"desc": "Potential hormone disruptor", "aliases": ["parabens", "methylparaben"], "bad_compat": ["all"]},
                    "formaldehyde": {"desc": "Carcinogenic preservative", "bad_compat": ["all"]},
                    "mineral oil": {"desc": "Clogs pores", "bad_compat": ["oily", "acne", "acne-prone"]},
                    "oxybenzone": {"desc": "Chemical sunscreen irritant", "bad_compat": ["sensitive"]},
                    "artificial dyes": {"desc": "May cause allergic reactions", "aliases": ["ci numbers", "ci "], "bad_compat": ["sensitive"]},
                }
                
                import re
                words = re.split(r'[,.\n|]+', ingredients_text)
                found_ings = [w.strip() for w in words if len(w.strip()) > 3]
                
                if not found_ings:
                    found_ings = ["No clear ingredients parsed"]
                st_normalized = skin_type.lower()
                seen = set()
                
                def is_good_for_skin_type(ingredient_skin_types, user_skin_type):
                    if "all" in ingredient_skin_types:
                        return True
                    return user_skin_type.lower() in [s.lower() for s in ingredient_skin_types]
                seen = set()
                
                for ing in found_ings:
                    matched = False
                    
                    # Check Safe
                    for key, data in safe_db.items():
                        if matched: break
                        aliases = [key] + data.get("aliases", [])
                        if any(a in ing for a in aliases):
                            if key in seen:
                                matched = True; break
                            seen.add(key)
                            is_compat = is_good_for_skin_type(data.get("compat", []), st_normalized) or is_good_for_skin_type(data.get("compat", []), st_normalized + "-prone")
                            parsed_results.append({
                                "name": key.title(),
                                "status": "Safe",
                                "reason": data["desc"],
                                "skinTypeCompatibility": is_compat
                            })
                            matched = True
                            
                    # Check Caution
                    for key, data in caution_db.items():
                        if matched: break
                        aliases = [key] + data.get("aliases", [])
                        if any(a in ing for a in aliases):
                            if key in seen:
                                matched = True; break
                            seen.add(key)
                            is_compat = False if ("all" in data.get("bad_compat", []) or st_normalized in data.get("bad_compat", [])) else True
                            parsed_results.append({
                                "name": key.title(),
                                "status": "Caution",
                                "reason": data["desc"],
                                "skinTypeCompatibility": is_compat
                            })
                            matched = True
                            
                    # Check Avoid
                    for key, data in avoid_db.items():
                        if matched: break
                        aliases = [key] + data.get("aliases", [])
                        if any(a in ing for a in aliases):
                            if key in seen:
                                matched = True; break
                            seen.add(key)
                            is_compat = False if ("all" in data.get("bad_compat", []) or st_normalized in data.get("bad_compat", [])) else True
                            parsed_results.append({
                                "name": key.title(),
                                "status": "Avoid",
                                "reason": data["desc"],
                                "skinTypeCompatibility": is_compat
                            })
                            matched = True
                            
                    # Unknown
                    if not matched and len(parsed_results) < 15 and len(ing.split()) <= 4:
                        if ing not in seen:
                            seen.add(ing)
                            parsed_results.append({
                                "name": ing.title(),
                                "status": "Unknown",
                                "reason": "Not enough data available",
                                "skinTypeCompatibility": False
                            })

            # Verdict Logic based on list of dicts
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

            # Overall skin type suitability verdict
            total = len(parsed_results)
            compatible_count = sum(1 for r in parsed_results if r.get("skinTypeCompatibility"))
            if total > 0:
                compat_ratio = compatible_count / total
                if compat_ratio >= 0.7:
                    skin_suitable = True
                    suitable_msg = "✅ This product is suitable for your skin type"
                else:
                    skin_suitable = False
                    suitable_msg = "⚠️ This product may not be ideal for your skin type"
            else:
                skin_suitable = None
                suitable_msg = ""

            scan_results = {
                "parsed_items": parsed_results,
                "summary": overall,
                "status": status_class,
                "mode": mode_used,
                "skin_suitable": skin_suitable,
                "suitable_msg": suitable_msg,
                "skin_type": skin_type
            }

        except Exception as e:
            print(f"OCR Error: {e}")
            flash("⚠️ Could not process image. Please try another one.")
            scan_results = None

        # Log History (Simplified for now)
        if scan_results:
            scan_history = IngredientScanHistory(
                user_id=current_user.id,
                image_path=filename,
                result_summary=scan_results['summary']
            )
            db.session.add(scan_history)
            db.session.commit()

    return render_template('ingredient_scan.html', scan_results=scan_results)



@app.route('/trend-verification', methods=['GET', 'POST'])
@login_required
def trend_verification():
    result = explanation = status = None
    if request.method == 'POST':
        result, explanation, status = verify_trend(
            request.form.get('trend'),
            request.form.get('skin_type')
        )

        
        # Log History
        if result:
            trend_log = TrendHistory(
                user_id=current_user.id,
                trend=request.form.get('trend'),
                result=result,
                status=status
            )
            db.session.add(trend_log)
            db.session.commit()

    return render_template('trend_verification.html',
                           result=result,
                           explanation=explanation,
                           status=status)


@app.route('/history')
@login_required
def history():
    # Fetch all history types
    skin_reports = SkinReport.query.filter_by(user_id=current_user.id).order_by(SkinReport.id.desc()).all()
    trend_history = TrendHistory.query.filter_by(user_id=current_user.id).order_by(TrendHistory.id.desc()).all()
    scan_history = IngredientScanHistory.query.filter_by(user_id=current_user.id).order_by(IngredientScanHistory.id.desc()).all()
    
    return render_template('history.html', 
                          skin_reports=skin_reports, 
                          trend_history=trend_history, 
                          scan_history=scan_history)


@app.route('/natural-remedies')
@login_required
def natural_remedies():
    remedies = [
        {
            "name": "Aloe Vera Gel",
            "icon": "🪴",
            "benefit": "Soothes inflammation and hydrates without clogging pores.",
            "skin_type": "Oily / Sensitive",
            "rating": "10/10",
            "usage": "Apply fresh gel directly to face for 15 mins, then wash."
        },
        {
            "name": "Honey & Turmeric",
            "icon": "🍯",
            "benefit": "Anti-bacterial and brightens dull skin.",
            "skin_type": "Acne-Prone / Dull",
            "rating": "9.5/10",
            "usage": "Mix 1 tbsp honey with pinch of turmeric. Leave on for 10 mins."
        },
        {
            "name": "Oatmeal Scrub",
            "icon": "🥣",
            "benefit": "Gentle exfoliation for dead skin cells.",
            "skin_type": "Dry / Sensitive",
            "rating": "9/10",
            "usage": "Mix ground oats with milk/yogurt. Gently massage."
        },
        {
            "name": "Green Tea Toner",
            "icon": "🍵",
            "benefit": "Controls oil production and reduces redness.",
            "skin_type": "Oily / Combination",
            "rating": "9/10",
            "usage": "Brew green tea, cool it, and apply with cotton pad."
        },
        {
            "name": "Cucumber Slices",
            "icon": "🥒",
            "benefit": "Hydrates and reduces puffiness.",
            "skin_type": "All Skin Types",
            "rating": "8.5/10",
            "usage": "Place chilled slices on eyes or face for cooling effect."
        },
        {
            "name": "Yogurt Mask",
            "icon": "🥛",
            "benefit": "Lactic acid gently exfoliates and moisturizes.",
            "skin_type": "Dry / Normal",
            "rating": "9/10",
            "usage": "Apply plain yogurt to face for 20 mins."
        },
        {
            "name": "Multani Mitti (Fuller's Earth)",
            "icon": "🪨",
            "benefit": "Absorbs excess oil and cleans pores.",
            "skin_type": "Oily / Acne-prone",
            "rating": "9.5/10",
            "usage": "Mix with rose water, apply for 10-15 mins, then wash."
        },
        {
            "name": "Rose Water",
            "icon": "🌹",
            "benefit": "Refreshes skin and balances pH.",
            "skin_type": "All skin types",
            "rating": "10/10",
            "usage": "Spray directly or apply with cotton."
        },
        {
            "name": "Turmeric + Milk",
            "icon": "🥛",
            "benefit": "Brightens skin and reduces spots.",
            "skin_type": "Normal / Dry",
            "rating": "9/10",
            "usage": "Mix a pinch of turmeric with milk, apply for 10 mins."
        },
        {
            "name": "Banana Face Mask",
            "icon": "🍌",
            "benefit": "Moisturizes and softens skin.",
            "skin_type": "Dry skin",
            "rating": "8.5/10",
            "usage": "Mash banana, apply for 15 mins."
        },
        {
            "name": "Neem Paste",
            "icon": "🌿",
            "benefit": "Anti-bacterial and reduces pimples.",
            "skin_type": "Acne-prone",
            "rating": "9.5/10",
            "usage": "Grind neem leaves with water and apply for 10 mins."
        },
        {
            "name": "Tomato Juice",
            "icon": "🍅",
            "benefit": "Helps reduce tan and excess oil.",
            "skin_type": "Oily skin",
            "rating": "8.5/10",
            "usage": "Apply fresh tomato juice for 5-10 mins."
        },
        {
            "name": "Papaya Face Pack",
            "icon": "🧡",
            "benefit": "Removes dead skin cells and adds glow.",
            "skin_type": "Dull / Normal",
            "rating": "9/10",
            "usage": "Mash ripe papaya and apply for 10-15 mins."
        },
        {
            "name": "Potato Juice",
            "icon": "🥔",
            "benefit": "Helps reduce dark spots and pigmentation.",
            "skin_type": "All skin types",
            "rating": "9/10",
            "usage": "Apply fresh potato juice with cotton for 10 mins."
        },
        {
            "name": "Coconut Oil",
            "icon": "🥥",
            "benefit": "Deep moisturization and soft skin.",
            "skin_type": "Dry skin",
            "rating": "8.5/10",
            "usage": "Apply a small amount before sleep."
        },
        {
            "name": "Rice Water Toner",
            "icon": "🌾",
            "benefit": "Tightens pores and brightens skin.",
            "skin_type": "Oily / Combination",
            "rating": "9/10",
            "usage": "Apply fermented or soaked rice water with cotton."
        },
        {
            "name": "Lemon + Honey Mask",
            "icon": "🍋",
            "benefit": "Controls oil and brightens skin.",
            "skin_type": "Oily skin",
            "rating": "8.5/10",
            "usage": "Mix a few drops of lemon with honey, apply for 5-8 mins."
        },
        {
            "name": "Aloe Vera + Cucumber Gel",
            "icon": "🥒",
            "benefit": "Cooling and soothing effect.",
            "skin_type": "Sensitive skin",
            "rating": "9.5/10",
            "usage": "Mix fresh aloe gel with cucumber juice and apply."
        },
        {
            "name": "Gram Flour (Besan) Pack",
            "icon": "🥣",
            "benefit": "Removes tan and cleans skin.",
            "skin_type": "Oily / Normal",
            "rating": "9/10",
            "usage": "Mix besan with milk or rose water, apply for 10-15 mins."
        },
        {
            "name": "Sandalwood Paste",
            "icon": "🪵",
            "benefit": "Reduces redness and pimples.",
            "skin_type": "Acne-prone / Sensitive",
            "rating": "9.5/10",
            "usage": "Mix sandalwood powder with rose water and apply."
        },
        {
            "name": "Milk Cream (Malai) Mask",
            "icon": "🥛",
            "benefit": "Deep hydration and smooth texture.",
            "skin_type": "Dry skin",
            "rating": "9/10",
            "usage": "Apply fresh malai for 10 mins, then wash."
        }
    ]
    return render_template('natural_remedies.html', remedies=remedies)


@app.route('/products')
@login_required
def products():
    product_list = [
        {
            "name": "Cetaphil Gentle Skin Cleanser",
            "icon": "🧴",
            "derm_name": "Dr. Jaishree Sharad",
            "derm_quote": "My go-to recommendation for sensitive and dry skin patients. pH balanced and non-stripping.",
            "skin_type": "Normal / Dry / Sensitive",
            "price": "₹330",
            "key_ingredient": "Niacinamide, Panthenol",
            "derm_rating": "9.5/10",
            "link": "https://www.amazon.in/s?k=Cetaphil+Gentle+Skin+Cleanser",
            "category": "Cleansers",
            "concern": "Dryness"
        },
        {
            "name": "La Roche-Posay Toleriane Hydrating Cleanser",
            "icon": "🧴",
            "derm_name": "Dr. Chytra V Anand",
            "derm_quote": "Recommended for rosacea and reactive skin. Maintains the skin barrier.",
            "skin_type": "Sensitive / Dry",
            "price": "₹1200",
            "key_ingredient": "Ceramides, Niacinamide",
            "derm_rating": "9.8/10",
            "link": "https://www.amazon.in/s?k=La+Roche+Posay+Toleriane+Cleanser",
            "category": "Cleansers",
            "concern": "Sensitive"
        },
        {
            "name": "Minimalist 2% Salicylic Acid Face Wash",
            "icon": "🧴",
            "derm_name": "Dr. Nivedita Dadu",
            "derm_quote": "Best budget BHA cleanser available in India for acne-prone patients.",
            "skin_type": "Oily / Acne-Prone",
            "price": "₹299",
            "key_ingredient": "Salicylic Acid 2%",
            "derm_rating": "9/10",
            "link": "https://www.amazon.in/s?k=Minimalist+Salicylic+Acid+Face+Wash",
            "category": "Cleansers",
            "concern": "Acne"
        },
        {
            "name": "CeraVe Hydrating Cleanser",
            "icon": "🧴",
            "derm_name": "Dr. Rashmi Shetty",
            "derm_quote": "Contains essential ceramides that restore skin barrier. Safe for daily use.",
            "skin_type": "Dry / Normal",
            "price": "₹799",
            "key_ingredient": "Ceramides, Hyaluronic Acid",
            "derm_rating": "9.7/10",
            "link": "https://www.amazon.in/s?k=CeraVe+Hydrating+Cleanser",
            "category": "Cleansers",
            "concern": "Dryness"
        },
        {
            "name": "CeraVe Moisturizing Cream",
            "icon": "🫧",
            "derm_name": "Dr. Shuba Dhavale",
            "derm_quote": "The gold standard moisturizer. I prescribe this to almost every patient.",
            "skin_type": "Dry / Normal / Sensitive",
            "price": "₹450",
            "key_ingredient": "Ceramides 1,3,6-II",
            "derm_rating": "9.8/10",
            "link": "https://www.amazon.in/s?k=CeraVe+Moisturizing+Cream",
            "category": "Moisturizers",
            "concern": "Dryness"
        },
        {
            "name": "Neutrogena Hydro Boost Water Gel",
            "icon": "🫧",
            "derm_name": "Dr. Soma Sarkar",
            "derm_quote": "Perfect oil-free hydration for oily skin without clogging pores.",
            "skin_type": "Oily / Combination",
            "price": "₹649",
            "key_ingredient": "Hyaluronic Acid",
            "derm_rating": "9.2/10",
            "link": "https://www.amazon.in/s?k=Neutrogena+Hydro+Boost+Water+Gel",
            "category": "Moisturizers",
            "concern": "Pores"
        },
        {
            "name": "Ponds Super Light Gel",
            "icon": "🫧",
            "derm_name": "Dr. Jamuna Pai",
            "derm_quote": "Best affordable moisturizer for Indian oily skin in humid weather.",
            "skin_type": "Oily / Combination",
            "price": "₹150",
            "key_ingredient": "Hyaluronic Acid, Vitamin E",
            "derm_rating": "8.5/10",
            "link": "https://www.amazon.in/s?k=Ponds+Super+Light+Gel",
            "category": "Moisturizers",
            "concern": "Pores"
        },
        {
            "name": "Minimalist 10% Niacinamide Serum",
            "icon": "✨",
            "derm_name": "Dr. Nivedita Dadu",
            "derm_quote": "Most effective budget niacinamide serum. Controls sebum and minimizes pores.",
            "skin_type": "Oily / Acne-Prone / Combination",
            "price": "₹599",
            "key_ingredient": "Niacinamide 10%, Zinc 1%",
            "derm_rating": "9.3/10",
            "link": "https://www.amazon.in/s?k=Minimalist+Niacinamide+Serum",
            "category": "Serums",
            "concern": "Pores"
        },
        {
            "name": "The Ordinary Hyaluronic Acid 2% + B5",
            "icon": "✨",
            "derm_name": "Dr. Rashmi Shetty",
            "derm_quote": "Excellent multi-weight HA formula. Works for all skin types needing hydration.",
            "skin_type": "All Types / Dry",
            "price": "₹590",
            "key_ingredient": "Hyaluronic Acid 2%, Vitamin B5",
            "derm_rating": "9.5/10",
            "link": "https://www.amazon.in/s?k=The+Ordinary+Hyaluronic+Acid+B5",
            "category": "Serums",
            "concern": "Dryness"
        },
        {
            "name": "Dot & Key Vitamin C + E Serum",
            "icon": "✨",
            "derm_name": "Dr. Chytra V Anand",
            "derm_quote": "Best Indian Vitamin C serum for brightening. Stable formulation.",
            "skin_type": "Dull / Normal / Combination",
            "price": "₹595",
            "key_ingredient": "Vitamin C 10%, Vitamin E",
            "derm_rating": "8.8/10",
            "link": "https://www.amazon.in/s?k=Dot+and+Key+Vitamin+C+Serum",
            "category": "Serums",
            "concern": "Brightening"
        },
        {
            "name": "The Derma Co 1% Hyaluronic Sunscreen",
            "icon": "☀️",
            "derm_name": "Dr. Jaishree Sharad",
            "derm_quote": "SPF 50 PA++++ with no white cast. Best sunscreen for Indian skin tones.",
            "skin_type": "All Types",
            "price": "₹499",
            "key_ingredient": "SPF 50, Hyaluronic Acid",
            "derm_rating": "9.6/10",
            "link": "https://www.amazon.in/s?k=Derma+Co+Hyaluronic+Sunscreen",
            "category": "Sunscreens",
            "concern": "Anti-Aging"
        },
        {
            "name": "Re'equil Oxybenzone Free Sunscreen",
            "icon": "☀️",
            "derm_name": "Dr. Soma Sarkar",
            "derm_quote": "My top pick for sensitive and reactive skin. Zero irritating filters.",
            "skin_type": "Sensitive / All Types",
            "price": "₹575",
            "key_ingredient": "Zinc Oxide, Titanium Dioxide",
            "derm_rating": "9.4/10",
            "link": "https://www.amazon.in/s?k=Reqeuil+Oxybenzone+Free+Sunscreen",
            "category": "Sunscreens",
            "concern": "Sensitive"
        },
        {
            "name": "Minimalist SPF 50 Sunscreen",
            "icon": "☀️",
            "derm_name": "Dr. Nivedita Dadu",
            "derm_quote": "Lightweight, non-greasy formula. Perfect for daily use under makeup.",
            "skin_type": "Oily / Combination",
            "price": "₹399",
            "key_ingredient": "SPF 50 PA++++",
            "derm_rating": "9.1/10",
            "link": "https://www.amazon.in/s?k=Minimalist+SPF+50+Sunscreen",
            "category": "Sunscreens",
            "concern": "Anti-Aging"
        },
        {
            "name": "Mamaearth Bye Bye Blemishes Cream",
            "icon": "🌿",
            "derm_name": "Dr. Shuba Dhavale",
            "derm_quote": "Safe kojic acid formula for mild hyperpigmentation in Indian patients.",
            "skin_type": "All Types / Pigmentation",
            "price": "₹349",
            "key_ingredient": "Kojic Acid, Mulberry Extract",
            "derm_rating": "8.3/10",
            "link": "https://www.amazon.in/s?k=Mamaearth+Bye+Bye+Blemishes",
            "category": "Treatments",
            "concern": "Dark Spots"
        },
        {
            "name": "Sebamed Clear Face Gel",
            "icon": "🌿",
            "derm_name": "Dr. Rashmi Shetty",
            "derm_quote": "pH 5.5 formula is clinically proven for acne-prone skin. Dermatologist tested.",
            "skin_type": "Acne-Prone / Sensitive",
            "price": "₹475",
            "key_ingredient": "L-Carnitine, Aloe Vera",
            "derm_rating": "9/10",
            "link": "https://www.amazon.in/s?k=Sebamed+Clear+Face+Gel",
            "category": "Treatments",
            "concern": "Acne"
        }
    ]
    return render_template('products.html', products=product_list)



@app.route('/dermatologists')
@login_required
def dermatologists():
    clinical_doctors = [
        {
            "name": "Dr. Jamuna Pai",
            "city": "Mumbai / Delhi",
            "specialization": "Cosmetologist",
            "contact": "+91 92232-24044",
            "hospital": "SkinLab"
        },
        {
            "name": "Dr. Chytra V Anand",
            "city": "Bangalore",
            "specialization": "Cosmetic Dermatologist",
            "contact": "+91 80468-12455",
            "hospital": "Kosmoderma Clinics"
        },
        {
            "name": "Dr. Nivedita Dadu",
            "city": "Delhi",
            "specialization": "Dermatologist & Hair Specialist",
            "contact": "+91 98109-39319",
            "hospital": "Dadu Medical Centre"
        },
        {
            "name": "Dr. Kiran Sethi",
            "city": "Delhi",
            "specialization": "Aesthetic & Integrative Dermatology",
            "contact": "+91 96673-77709",
            "hospital": "Isya Aesthetics"
        },
        {
            "name": "Dr. Jaishree Sharad",
            "city": "Mumbai",
            "specialization": "Cosmetologist & Dermatologist",
            "contact": "+91 92232-19239",
            "hospital": "Skinfiniti Aesthetic Clinic"
        },
        {
            "name": "Dr. Rashmi Shetty",
            "city": "Mumbai / Hyderabad",
            "specialization": "Non-surgical Aesthetic Medicine",
            "contact": "+91 98330-55236",
            "hospital": "Ra Skin and Aesthetics"
        }
    ]

    social_doctors = [
        {
            "name": "Dr. Shereene Idriss",
            "handle": "@shereeneidriss",
            "platform": "Instagram / YouTube",
            "link": "https://www.instagram.com/shereeneidriss/",
            "bio": "Pillowtalk Derm - Science-backed skincare advice."
        },
        {
            "name": "Dr. Dray",
            "handle": "Dr. Dray",
            "platform": "YouTube",
            "link": "https://www.youtube.com/c/DrDrayzday",
            "bio": "Dermatologist vlogger focusing on affordable skincare."
        },
        {
            "name": "Dr. Jushya Sarin",
            "handle": "@drjushya_sarinskin",
            "platform": "Instagram",
            "link": "https://www.instagram.com/drjushya_sarinskin/",
            "bio": "Approachable advice on Indian skin concerns."
        },
        {
            "name": "Dr. Ranella Hirsch",
            "handle": "@ranellamd",
            "platform": "Instagram",
            "link": "https://www.instagram.com/ranellamd/",
            "bio": "Board-certified dermatologist busting skincare myths with science."
        },
        {
            "name": "Hyram Yarbro",
            "handle": "Skincare by Hyram",
            "platform": "YouTube / TikTok",
            "link": "https://www.youtube.com/c/Hyram",
            "bio": "Skincare specialist known for ingredient breakdowns and brand reviews."
        },
        {
            "name": "Dr. Aamina Mahmood",
            "handle": "@doctor.aamina",
            "platform": "Instagram",
            "link": "https://www.instagram.com/doctor.aamina/",
            "bio": "Medical doctor giving evidence-based skincare routines and tips."
        }
    ]
    return render_template('dermatologists.html', clinical=clinical_doctors, social=social_doctors)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


# ================== RUN ==================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    port = int(os.environ.get("PORT", 5000))
    print(f"SkinSense Application Initializing on port {port}...")
    app.run(debug=True, port=port)
