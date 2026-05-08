"""
Skin Health Score Calculation Service
"""


def calculate_skin_score(ai_findings, user_data):
    """
    Calculate the skin health score based on AI findings and user questionnaire data.
    Returns (score, score_breakdown_list).
    """
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
            if cond != "skin texture" and cond != "oiliness":
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
    except:
        pass

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
