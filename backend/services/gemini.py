"""
Gemini API Service — All AI/Vision API calls to Google Gemini.
"""
import os
import io
import json
import time
import base64
import urllib.request
import urllib.error
from PIL import Image

_last_gemini_call = 0


def get_api_key():
    """Get Gemini API key from environment."""
    return os.environ.get("GEMINI_API_KEY", "")


def call_gemini_text(prompt, api_key=None, temperature=0.2):
    """Call Gemini with a text-only prompt and return parsed JSON."""
    api_key = api_key or get_api_key()
    if not api_key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "responseMimeType": "application/json"}
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            text = res_body["candidates"][0]["content"]["parts"][0]["text"]
            clean = text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
    except Exception as e:
        print(f"Gemini text call failed: {e}")
        return None


def analyze_face_image(image_data=None, file_obj=None):
    """
    Analyze a face image using Gemini Vision API.
    Accepts either base64 image_data string or a file object.
    Returns parsed JSON with findings, or None on failure.
    """
    api_key = get_api_key()
    if not api_key:
        return None

    img = None
    if image_data and "base64" in image_data:
        try:
            header, encoded = image_data.split(",", 1)
            data = base64.b64decode(encoded)
            img = Image.open(io.BytesIO(data))
        except Exception as e:
            return {"error": f"Invalid base64: {str(e)}"}
    elif file_obj:
        img = Image.open(file_obj)

    if not img:
        return {"error": "No image provided"}

    # Encode image to base64 for Gemini
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
    for model_name in MODELS_TO_TRY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
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
                clean = text.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(clean)

                # Backward compatibility flags
                parsed["pimples"] = any(f["condition"] == "Pimples / Acne" and f["detected"] for f in parsed.get("findings", []))
                parsed["oily"] = any(f["condition"] == "Oiliness" and f["severity"] == "High" for f in parsed.get("findings", []))
                parsed["spots"] = any(f["condition"] == "Dark Spots / Hyperpigmentation" and f["detected"] for f in parsed.get("findings", []))

                return parsed

        except Exception as e:
            print(f"Gemini error with {model_name}: {e}")
            continue

    return {"error": "All AI models failed"}


def analyze_ingredient_image(image_path, skin_type):
    """
    Analyze a product ingredient label image using Gemini Vision API.
    Returns list of ingredient dicts, or None on failure.
    """
    global _last_gemini_call
    api_key = get_api_key()

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
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        ext = image_path.split('.')[-1].lower()
        mime_type = f"image/{ext}" if ext != 'jpg' else "image/jpeg"
        if ext == 'jfif':
            mime_type = "image/jpeg"
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

    for model_name in MODELS_TO_TRY:
        for attempt in range(2):
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

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
                    clean = text.replace("```json", "").replace("```", "").strip()
                    try:
                        parsed = json.loads(clean)
                        print(f"SUCCESS with model {model_name}: {len(parsed)} ingredients")
                        return parsed
                    except Exception as je:
                        finish_reason = result["candidates"][0].get("finishReason", "UNKNOWN")
                        print(f"Failed to parse JSON for {model_name}. Finish reason: {finish_reason}")
                        print(f"Raw text first 200 chars: {clean[:200]}")
                        raise je

            except urllib.error.HTTPError as e:
                error_body = e.read().decode()
                print(f"Model {model_name} attempt {attempt+1}: HTTP {e.code}")
                if e.code == 429:
                    if "GenerateRequestsPerDay" in error_body or "RESOURCE_EXHAUSTED" in error_body:
                        print("Quota exhausted for this model, trying next...")
                        break
                    print("Rate limited, waiting 10s...")
                    time.sleep(10)
                    continue
                elif e.code == 404:
                    print(f"Model {model_name} not found, trying next...")
                    break
                else:
                    print(f"Error: {error_body[:200]}")
                    break
            except Exception as e:
                print(f"Model {model_name} error: {e}")
                break

    print("All models failed, using offline fallback")
    return None


def generate_personalized_routine(data, ai_results_enriched):
    """
    Call Gemini to generate a personalized skincare routine based on user data.
    Returns dict with routine, lifestyle, key_ingredients, warnings — or empty defaults.
    """
    api_key = get_api_key()
    if not api_key:
        return {"routine": None, "lifestyle": [], "key_ingredients": [], "warnings": []}

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

    result = call_gemini_text(prompt, api_key)
    if result:
        return {
            "routine": result.get("routine"),
            "lifestyle": result.get("lifestyle", []),
            "key_ingredients": result.get("key_ingredients", []),
            "warnings": result.get("warnings", [])
        }

    return {"routine": None, "lifestyle": [], "key_ingredients": [], "warnings": []}
