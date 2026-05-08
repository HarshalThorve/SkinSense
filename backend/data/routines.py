"""
Skincare Routines Data — Morning/Night routines for each skin type.
"""

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
