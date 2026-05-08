"""
Ingredient Databases — Safe, Caution, and Avoid ingredient dictionaries for offline fallback.
"""

SAFE_DB = {
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

CAUTION_DB = {
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

AVOID_DB = {
    "sodium lauryl sulfate": {"desc": "Strips natural oils, causes irritation", "aliases": ["sls"], "bad_compat": ["sensitive", "dry"]},
    "paraben": {"desc": "Potential hormone disruptor", "aliases": ["parabens", "methylparaben"], "bad_compat": ["all"]},
    "formaldehyde": {"desc": "Carcinogenic preservative", "bad_compat": ["all"]},
    "mineral oil": {"desc": "Clogs pores", "bad_compat": ["oily", "acne", "acne-prone"]},
    "oxybenzone": {"desc": "Chemical sunscreen irritant", "bad_compat": ["sensitive"]},
    "artificial dyes": {"desc": "May cause allergic reactions", "aliases": ["ci numbers", "ci "], "bad_compat": ["sensitive"]},
}
