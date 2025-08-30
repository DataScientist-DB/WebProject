import pickle
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Loan Approval Predictor", page_icon="💳")

st.title("💳 Loan Approval Predictor")
st.write("Use this app to predict whether a loan application would be approved based on applicant details.")

# ----------------------------
# Utilities
# ----------------------------
@st.cache_resource
def load_model(path: str):
    with open(path, "rb") as f:
        return pickle.load(f)

def encode_inputs(form_data: dict) -> pd.DataFrame:
    """Convert friendly form inputs into the numeric features expected by the model."""
    mapping = {
        "Gender": {"Female": 0, "Male": 1},
        "Married": {"No": 0, "Yes": 1},
        "Dependents": {"0": 0, "1": 1, "2": 2, "3+": 3},
        "Education": {"Graduate": 0, "Not Graduate": 1},
        "Self_Employed": {"No": 0, "Yes": 1},
        "Property_Area": {"Rural": 0, "Semiurban": 1, "Urban": 2},
    }
    row = {
        "Gender": mapping["Gender"][form_data["Gender"]],
        "Married": mapping["Married"][form_data["Married"]],
        "Dependents": mapping["Dependents"][form_data["Dependents"]],
        "Education": mapping["Education"][form_data["Education"]],
        "Self_Employed": mapping["Self_Employed"][form_data["Self_Employed"]],
        "ApplicantIncome": form_data["ApplicantIncome"],
        "CoapplicantIncome": form_data["CoapplicantIncome"],
        "LoanAmount": form_data["LoanAmount"],
        "Loan_Amount_Term": form_data["Loan_Amount_Term"],
        "Credit_History": 1 if form_data["Credit_History"] == "Good (1)" else 0,
        "Property_Area": mapping["Property_Area"][form_data["Property_Area"]],
    }
    return pd.DataFrame([row])

def predict_label(y):
    return "✅ Loan Approved" if int(y) == 1 else "❌ Loan Rejected"

# ----------------------------
# Load model
# ----------------------------
MODEL_PATH = "loan_model.pkl"   # Make sure loan_model.pkl is in same folder
try:
    model = load_model(MODEL_PATH)
    st.success(f"Model loaded: {MODEL_PATH}")
except Exception as e:
    st.error(f"Could not load model at '{MODEL_PATH}'. Place loan_model.pkl in this folder. Error: {e}")
    st.stop()

# ----------------------------
# Tabs: Single | Batch
# ----------------------------
tab_single, tab_batch = st.tabs(["Single Prediction", "Batch Predictions"])

with tab_single:
    st.subheader("Single Applicant")
    with st.form("single_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            gender = st.selectbox("Gender", ["Male", "Female"], index=0)
            married = st.selectbox("Married", ["Yes", "No"], index=0)
            dependents = st.selectbox("Dependents", ["0", "1", "2", "3+"], index=0)
            education = st.selectbox("Education", ["Graduate", "Not Graduate"], index=0)
        with col2:
            self_emp = st.selectbox("Self Employed", ["No", "Yes"], index=0)
            applicant_income = st.number_input("Applicant Income", min_value=0, value=5000, step=100)
            coapplicant_income = st.number_input("Coapplicant Income", min_value=0, value=0, step=100)
            loan_amount = st.number_input("Loan Amount (thousands)", min_value=0, value=150, step=10)
        with col3:
            loan_term = st.selectbox("Loan Term (months)", [12, 36, 60, 84, 120, 180, 240, 300, 360], index=8)
            credit_hist = st.selectbox("Credit History", ["Good (1)", "Bad (0)"], index=0)
            property_area = st.selectbox("Property Area", ["Urban", "Semiurban", "Rural"], index=0)

        submitted = st.form_submit_button("Predict")
        if submitted:
            features = encode_inputs({
                "Gender": gender,
                "Married": married,
                "Dependents": dependents,
                "Education": education,
                "Self_Employed": self_emp,
                "ApplicantIncome": applicant_income,
                "CoapplicantIncome": coapplicant_income,
                "LoanAmount": loan_amount,
                "Loan_Amount_Term": loan_term,
                "Credit_History": credit_hist,
                "Property_Area": property_area,
            })
            y_pred = model.predict(features)[0]
            st.markdown(f"### Result: **{predict_label(y_pred)}**")

with tab_batch:
    st.subheader("Batch Predictions via CSV")
    st.write("Upload a CSV with the following columns (case-sensitive):")
    st.code("Gender,Married,Dependents,Education,Self_Employed,ApplicantIncome,CoapplicantIncome,LoanAmount,Loan_Amount_Term,Credit_History,Property_Area", language="text")
    uploaded = st.file_uploader("Upload applicants CSV", type=["csv"])
    if uploaded:
        df = pd.read_csv(uploaded)
        required_cols = ["Gender","Married","Dependents","Education","Self_Employed",
                         "ApplicantIncome","CoapplicantIncome","LoanAmount","Loan_Amount_Term",
                         "Credit_History","Property_Area"]
        if not all(c in df.columns for c in required_cols):
            st.error("CSV is missing one or more required columns listed above.")
        else:
            def normalize_row(r):
                mapping = {
                    "Gender": {"Female": 0, "Male": 1},
                    "Married": {"No": 0, "Yes": 1},
                    "Dependents": {"0": 0, "1": 1, "2": 2, "3+": 3},
                    "Education": {"Graduate": 0, "Not Graduate": 1},
                    "Self_Employed": {"No": 0, "Yes": 1},
                    "Property_Area": {"Rural": 0, "Semiurban": 1, "Urban": 2},
                }
                out = {}
                for k in required_cols:
                    v = r[k]
                    if k in mapping:
                        if isinstance(v, str) and v in mapping[k]:
                            out[k] = mapping[k][v]
                        else:
                            out[k] = int(v)
                    elif k == "Credit_History":
                        if isinstance(v, str):
                            out[k] = 1 if v.strip() in ["1", "1.0", "Good (1)", "good", "Good"] else 0
                        else:
                            out[k] = int(v)
                    else:
                        out[k] = v
                return out

            encoded = pd.DataFrame([normalize_row(r) for _, r in df.iterrows()])
            preds = model.predict(encoded)
            labels = ["✅ Loan Approved" if p == 1 else "❌ Loan Rejected" for p in preds]
            result = df.copy()
            result["Prediction"] = labels
            st.dataframe(result, use_container_width=True)

            # Offer CSV download
            csv_bytes = result.to_csv(index=False).encode("utf-8")
            st.download_button("Download results CSV", data=csv_bytes,
                               file_name="loan_predictions.csv", mime="text/csv")

st.caption("Note: Category encodings mirror the training pipeline (LabelEncoder with sorted categories).")
