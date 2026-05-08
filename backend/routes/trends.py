"""
Trend Verification Routes
"""
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from backend import db
from backend.models import TrendHistory

trends_bp = Blueprint('trends', __name__)


def verify_trend(text, skin_type):
    """Verify a skincare trend against known safe/harmful databases."""
    text = text.lower().strip()

    harmful_keywords = {
        "lemon": "Lemon is highly acidic (pH 2) and can disrupt the skin barrier.",
        "lime": "Lime causes phytophotodermatitis and is too acidic for skin.",
        "baking soda": "Baking soda is too alkaline (pH 9) and destroys the acid mantle.",
        "toothpaste": "Toothpaste contains drying agents that can chemically burn the skin.",
        "bleach": "Bleach causes severe chemical burns and permanent damage.",
        "glue": "Pore strips or glue can tear the skin and cause broken capillaries.",
        "vinegar": "Undiluted vinegar can burn the skin. Always dilute.",
        "garlic": "Garlic can cause severe chemical burns on skin contact.",
        "cinnamon": "Cinnamon is a common allergen and can cause contact dermatitis.",
        "rubbing alcohol": "Strips natural oils completely, damaging the skin barrier."
    }

    safe_keywords = {
        "aloe": "Aloe Vera is soothing and hydrating.",
        "aleovera": "Aloe Vera is soothing and hydrating (Typo detected).",
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
        "ice": "Icing reduces inflammation and puffiness (use a cloth).",
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
        caution_items = [item for item in good_matches if item in ["besan", "gram flour", "lemon", "clay"]]
        if skin_type in ["Sensitive", "Dry"] and caution_items:
            caution_items_str = ", ".join([f"'{item}'" for item in caution_items])
            return "⚠️ Use with Caution", f"Detected {items}. {reasons} Note: {caution_items_str} can be drying for {skin_type} skin.", "warning"
        return "✅ Safe Trend", f"Detected {items}: {reasons} Generally safe for {skin_type} skin.", "success"

    return "⚠️ Unverified Trend", "No specific dermatological evidence found for this query in our database. Patch test required.", "warning"


@trends_bp.route('/trend-verification', methods=['GET', 'POST'])
@login_required
def trend_verification():
    result = explanation = status = None
    if request.method == 'POST':
        result, explanation, status = verify_trend(
            request.form.get('trend'),
            request.form.get('skin_type')
        )

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
                           result=result, explanation=explanation, status=status)
