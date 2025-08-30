import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score
import pickle

# -------------------------------
# 1️⃣ Load Dataset
# -------------------------------
data = pd.read_csv('loan_dataset.csv')

# Quick check
print("Dataset Shape:", data.shape)
print("Columns:", data.columns.tolist())
print(data.head())

# -------------------------------
# 2️⃣ Handle Missing Values
# -------------------------------
data.fillna({
    'Gender': data['Gender'].mode()[0],
    'Married': data['Married'].mode()[0],
    'Dependents': data['Dependents'].mode()[0],
    'Self_Employed': data['Self_Employed'].mode()[0],
    'LoanAmount': data['LoanAmount'].median(),
    'Loan_Amount_Term': data['Loan_Amount_Term'].median(),
    'Credit_History': data['Credit_History'].mode()[0]
}, inplace=True)

# -------------------------------
# 3️⃣ Encode Categorical Variables
# -------------------------------
categorical_cols = ['Gender', 'Married', 'Education', 'Self_Employed', 'Property_Area']
le = LabelEncoder()
for col in categorical_cols:
    data[col] = le.fit_transform(data[col])

# -------------------------------
# 4️⃣ Define Features & Target
# -------------------------------
X = data[['ApplicantIncome','CoapplicantIncome','LoanAmount',
          'Loan_Amount_Term','Credit_History']]
y = data['Loan_Status'].map({'Y':1, 'N':0})  # Convert Y/N to 1/0

# -------------------------------
# 5️⃣ Train-Test Split
# -------------------------------
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# -------------------------------
# 6️⃣ Train Model
# -------------------------------
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# -------------------------------
# 7️⃣ Evaluate Model
# -------------------------------
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"Model Accuracy: {accuracy*100:.2f}%")

# -------------------------------
# 8️⃣ Save Model
# -------------------------------
with open('loan_model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("✅ Model saved as loan_model.pkl")
