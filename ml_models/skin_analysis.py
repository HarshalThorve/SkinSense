import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

data = {
    "skin_type": [0,1,2,3,0,1,2,3],
    "concern": [0,1,2,3,0,1,2,3],
    "facewash": [1,1,0,1,0,1,0,1],
    "moisturizer": [1,0,1,1,0,1,0,1],
    "sunscreen": [1,0,0,1,0,1,0,1],
    "sleep": [1,0,1,0,0,1,0,1],
    "water": [1,0,1,0,0,1,0,1],
    "label": [0,2,1,2,2,0,2,0]
}

df = pd.DataFrame(data)

X = df.drop("label", axis=1)
y = df["label"]

model = RandomForestClassifier(n_estimators=100)
model.fit(X, y)

# ✅ CORRECT SAVE
joblib.dump(model, "skin_model.pkl")

print("✅ Skin analysis ML model trained & saved successfully")