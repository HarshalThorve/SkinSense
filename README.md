# SkinSense

SkinSense is an AI-powered web platform designed to analyze your skin health and provide highly personalized, realistic routines utilizing Google's Gemini Vision AI.

## Features

- **AI Skin Analysis:** Upload a photo or scan your face to get analytical insights into conditions like Pimples/Acne, Oiliness, Dark Spots, Skin Tone, and Estimated Age.
- **Personalized Skincare Routine:** Combines AI vision findings with a detailed user questionnaire to generate actionable Morning/Evening routines, ingredients to pursue, and lifestyle tips.
- **Smart Ingredient Scanner:** Uses OCR and Gemini AI to scan the ingredient list on the back of product packaging and verify its safety against your skin type.
- **Trend Verification Check:** Allows users to paste a viral TikTok/Instagram skincare trend to check whether it's safe or harmful for their specific skin type.
- **Dashboards & History Tracking:** Saves past scans and tracks cumulative progress (overall skin score variations). Includes PDF export capabilities.

## Installation

1. Clone this repository.
2. Install the requirement dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install [Tesseract-OCR](https://github.com/UB-Mannheim/tesseract/wiki) on your system. Make sure to update the `tesseract_cmd` path located in `app.py` based on your installation folder.
4. Create a `.env` file in the root directory with your secret API Key for Google Gemini:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
5. Run the DB Migration script to initialize the database:
   ```bash
   python migrate_db.py
   ```
6. Start the Flask application:
   ```bash
   python app.py
   ```

## Technologies Used
- **Backend**: Python, Flask, SQLite, SQLAlchemy
- **AI/ML Integration**: Google Gemini Vision API (Multimodal prompt execution), pytesseract (OCR)
- **Frontend**: HTML5, Vanilla CSS, JavaScript
- **PDF Generation**: ReportLab
