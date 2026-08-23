import os
import streamlit as st
import requests
import pandas as pd

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:7860")
PREDICT_URL = f"{BACKEND_URL}/v1/predict"
BATCH_URL = f"{BACKEND_URL}/v1/predictbatch"
REQUEST_TIMEOUT = 60

# Columns the backend expects for batch upload
REQUIRED_COLUMNS = [
    'Product_Weight', 'Product_Sugar_Content', 'Product_Allocated_Area',
    'Product_MRP', 'Store_Size', 'Store_Location_City_Type',
    'Store_Type', 'Store_Age_Years', 'Product_Type_Category', 'Product_Id_char'
]

st.set_page_config(page_title="SuperKart Sales Prediction", layout="centered")

st.title("SuperKart Sales Prediction 📈")

# ==================================================================
# SECTION 1 — SINGLE PREDICTION
# ==================================================================
st.header("Single Prediction")

col1, col2 = st.columns(2)

with col1:
    Product_Weight = st.number_input(
        "Product Weight", min_value=0.0, value=12.66,
        help="Weight of the product (numerical value)")

    Product_Sugar_Content = st.selectbox(
        "Product Sugar Content", ["Low Sugar", "Regular", "No Sugar"])

    Product_Allocated_Area = st.number_input(
        "Product Allocated Area", min_value=0.0, value=0.068,
        help="Ratio of allocated display area to total display area")

    Product_MRP = st.number_input(
        "Product MRP", min_value=0.0, value=116.7,
        help="Maximum retail price of each product")

    Store_Size = st.selectbox("Store Size", ["Small", "Medium", "High"])

with col2:
    Store_Location_City_Type = st.selectbox(
        "Store Location City Type", ["Tier 1", "Tier 2", "Tier 3"])

    Store_Type = st.selectbox(
        "Store Type",
        ["Supermarket Type1", "Supermarket Type2", "Departmental Store", "Food Mart"])

    Store_Age_Years = st.number_input(
        "Store Age (Years)", min_value=0, value=17, help="Age of the store")

    Product_Type_Category = st.selectbox(
        "Product Type Category", ["Perishables", "Non Perishables"])

    Product_Id_char = st.selectbox("Product Id Char", ["FD", "NC", "DR"])

if st.button("Run Prediction", type="primary"):

    if Product_Weight == 0.0:
        st.warning("Please enter a valid Product Weight")
    elif Product_MRP == 0.0:
        st.warning("Please enter a valid Product MRP")
    else:
        product_data = {
            "Product_Weight": Product_Weight,
            "Product_Sugar_Content": Product_Sugar_Content,
            "Product_Allocated_Area": Product_Allocated_Area,
            "Product_MRP": Product_MRP,
            "Store_Size": Store_Size,
            "Store_Location_City_Type": Store_Location_City_Type,
            "Store_Type": Store_Type,
            "Store_Age_Years": Store_Age_Years,
            "Product_Type_Category": Product_Type_Category,
            "Product_Id_char": Product_Id_char
        }

        with st.spinner("Running prediction..."):
            try:
                response = requests.post(
                    PREDICT_URL, json=product_data,
                    headers={"Content-Type": "application/json"},
                    timeout=REQUEST_TIMEOUT
                )
                if response.status_code == 200:
                    predicted_sales = response.json().get("Sales", 0)
                    st.success("Prediction Complete!")
                    st.metric(label="Predicted Sales", value=f"£{predicted_sales:.2f}")
                else:
                    try:
                        msg = response.json().get("error", response.text)
                    except Exception:
                        msg = response.text
                    st.error(f"API error {response.status_code}: {msg}")
            except requests.exceptions.ConnectionError:
                st.error(f"Cannot reach backend at {BACKEND_URL}. Is it running and Public?")
            except requests.exceptions.Timeout:
                st.error("Request timed out — try again.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

st.divider()

# ==================================================================
# SECTION 2 — BATCH PREDICTION
# ==================================================================
st.header("📁 Batch Prediction")

with st.expander("Required CSV columns / download template"):
    st.write("Your CSV must contain these columns:")
    st.code(", ".join(REQUIRED_COLUMNS), language="text")

    template_df = pd.DataFrame([{
        "Product_Weight": 12.66, "Product_Sugar_Content": "Low Sugar",
        "Product_Allocated_Area": 0.068, "Product_MRP": 116.7,
        "Store_Size": "Medium", "Store_Location_City_Type": "Tier 2",
        "Store_Type": "Supermarket Type1", "Store_Age_Years": 17,
        "Product_Type_Category": "Perishables", "Product_Id_char": "FD"
    }])
    st.download_button(
        "Download CSV template",
        data=template_df.to_csv(index=False).encode("utf-8"),
        file_name="superkart_template.csv",
        mime="text/csv"
    )

uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

if uploaded_file is not None:
    try:
        preview_df = pd.read_csv(uploaded_file)
        st.write(f"Preview — {preview_df.shape[0]} rows, {preview_df.shape[1]} columns")
        st.dataframe(preview_df.head(), use_container_width=True)

        missing = [c for c in REQUIRED_COLUMNS if c not in preview_df.columns]
        if missing:
            st.error(f"Missing required columns: {missing}")
        else:
            if st.button("Run Batch Prediction", type="primary"):
                with st.spinner("Running batch prediction..."):
                    try:
                        uploaded_file.seek(0)
                        files = {"file": (uploaded_file.name, uploaded_file, "text/csv")}
                        response = requests.post(BATCH_URL, files=files, timeout=REQUEST_TIMEOUT)

                        if response.status_code == 200:
                            result = response.json()
                            results_df = pd.DataFrame(result["predictions"])
                            pred_col = "Predicted_Sales"

                            if pred_col in results_df.columns:
                                results_df = results_df.sort_values(
                                    pred_col, ascending=False).reset_index(drop=True)

                            st.success(f"Predicted {result['n_records']} records!")

                            m1, m2, m3, m4 = st.columns(4)
                            m1.metric("Records", f"{len(results_df)}")
                            m2.metric("Total Sales", f"£{results_df[pred_col].sum():,.0f}")
                            m3.metric("Avg Sales", f"£{results_df[pred_col].mean():,.2f}")
                            m4.metric("Max Sales", f"£{results_df[pred_col].max():,.2f}")

                            st.divider()

                            st.subheader("Prediction Results")
                            styled = (
                                results_df.style
                                .background_gradient(subset=[pred_col], cmap="Greens")
                                .format({pred_col: "£{:.2f}"})
                                .set_properties(**{"text-align": "center"})
                            )
                            st.dataframe(styled, use_container_width=True)

                            st.subheader("Predicted Sales Distribution")
                            st.bar_chart(results_df[pred_col])

                            st.download_button(
                                "Download predictions as CSV",
                                data=results_df.to_csv(index=False).encode("utf-8"),
                                file_name="superkart_predictions.csv",
                                mime="text/csv"
                            )
                        else:
                            try:
                                msg = response.json().get("error", response.text)
                            except Exception:
                                msg = response.text
                            st.error(f"API error {response.status_code}: {msg}")

                    except requests.exceptions.ConnectionError:
                        st.error(f"Cannot reach backend at {BACKEND_URL}. Is it running and Public?")
                    except requests.exceptions.Timeout:
                        st.error("Request timed out — try a smaller file.")
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")

    except Exception as e:
        st.error(f"Could not read CSV: {str(e)}")
