import streamlit as st
import pandas as pd
import plotly.express as px
import re

st.set_page_config(page_title="Advanced Financial Dashboard", layout="wide")

# --- CLEAN FUNCTION ---
def clean_to_float(v):
    if pd.isna(v) or str(v).strip() == "":
        return 0.0
    
    s = str(v).upper().strip()
    is_credit = any(x in s for x in ["CR", "-", "("])
    
    s = re.sub(r'[^0-9.]', '', s)
    
    try:
        val = float(s) if s else 0.0
        return -val if is_credit else val
    except:
        return 0.0


# --- PARSER ---
def universal_parser(file):
    df = pd.read_csv(file, header=None)

    header_idx = None
    for i, row in df.iterrows():
        if any("particular" in str(x).lower() for x in row.values):
            header_idx = i
            break

    if header_idx is None:
        return None, "Header not found"

    header_row = df.iloc[header_idx]
    data_rows = df.iloc[header_idx + 1:]

    account_cols = [i for i, v in enumerate(header_row) if "particular" in str(v).lower()]

    all_data = []
    month_keywords = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec","202"]

    for i, val in enumerate(header_row):
        if "closing" in str(val).lower():

            acc_col = None
            for ac in reversed(account_cols):
                if ac < i:
                    acc_col = ac
                    break

            if acc_col is None:
                continue

            month = "Total"
            for r in range(header_idx):
                for c in range(i, acc_col - 1, -1):
                    cell = str(df.iloc[r, c]).lower()
                    if any(m in cell for m in month_keywords):
                        month = df.iloc[r, c]
                        break

            temp = pd.DataFrame()
            temp['Account'] = data_rows.iloc[:, acc_col].astype(str).str.strip()
            temp = temp[~temp['Account'].str.match(r'^[0-9.\sDrCr()-]+$', na=False)]

            temp['Amount'] = data_rows.iloc[:, i].apply(clean_to_float)
            temp['Month'] = month

            all_data.append(temp)

    if not all_data:
        return None, "No Closing Balance found"

    return pd.concat(all_data).reset_index(drop=True), None


# --- UI ---
st.title("📊 Advanced Financial Dashboard")
st.markdown("Smart MIS Dashboard with Insights 🚀")

uploaded = st.sidebar.file_uploader("Upload Trial Balance CSV", type="csv")
mapping_file = st.sidebar.file_uploader("Upload Mapping File", type="csv")

if uploaded:
    data, err = universal_parser(uploaded)

    if err:
        st.error(err)

    else:
        # --- LOAD MAPPING ---
        if mapping_file:
            map_df = pd.read_csv(mapping_file)
            mapping_dict = {
                str(row['Account']).lower().strip(): row['Category']
                for _, row in map_df.iterrows()
            }
        else:
            mapping_dict = {}

        # --- STRONG SMART CATEGORY ---
        def smart_cat(x):
            original = str(x).lower().strip()
            cleaned = re.sub(r'[^a-z0-9 ]', ' ', original)

            # normalize
            words = cleaned.split()
            words = [w[:-1] if w.endswith('s') else w for w in words]
            cleaned = " ".join(words)

            # --- STEP 1: EXACT / CLEAN MATCH ---
            for key in sorted(mapping_dict.keys(), key=len, reverse=True):
                key_clean = re.sub(r'[^a-z0-9 ]', ' ', key)
                key_words = key_clean.split()
                key_words = [w[:-1] if w.endswith('s') else w for w in key_words]
                key_clean = " ".join(key_words)

                if key_clean in cleaned or key in original:
                    return mapping_dict[key]

            # --- STEP 2: WORD LEVEL MATCH ---
            for word in words:
                for key in mapping_dict:
                    if word in key:
                        return mapping_dict[key]

            # --- STEP 3: STRONG KEYWORD FALLBACK ---
            if any(i in cleaned for i in ['cash','bank','receivable','debtor','inventory','stock','furniture','fixture','vehicle','equipment','asset','deposit','investment']):
                return 'Assets'

            if any(i in cleaned for i in ['loan','payable','creditor','capital','reserve','liability','provision']):
                return 'Liabilities'

            if any(i in cleaned for i in ['sale','income','revenue','interest','commission']):
                return 'Revenue'

            if any(i in cleaned for i in [
                'expense','rent','salary','wage','cost','tax','insurance',
                'maintenance','repair','professional','consultancy',
                'courier','transport','printing','internet',
                'depreciation','amortisation','penalty',
                'electricity','telephone','office','admin',
                'bonus','welfare','charges'
            ]):
                return 'Expenses'

            return "Others"

        data['Category'] = data['Account'].apply(smart_cat)

        st.write("Unmapped Accounts:", data[data['Category']=="Others"]['Account'].unique())

        # --- MONTH ---
        months = list(data['Month'].unique())

        sel_month = st.sidebar.selectbox("Select Month", months)
        compare_month = st.sidebar.selectbox("Compare With", months)

        view = data[data['Month'] == sel_month]
        prev_view = data[data['Month'] == compare_month]

        # --- METRICS ---
        assets = abs(view[view['Category'] == 'Assets']['Amount'].sum())
        liab = abs(view[view['Category'] == 'Liabilities']['Amount'].sum())

        st.metric("Assets", f"₹{assets:,.0f}")
        st.metric("Liabilities", f"₹{liab:,.0f}")

        revenue = abs(view[view['Category'] == 'Revenue']['Amount'].sum())
        expenses = abs(view[view['Category'] == 'Expenses']['Amount'].sum())
        prev_revenue = abs(prev_view[prev_view['Category'] == 'Revenue']['Amount'].sum())

        profit = revenue - expenses

        st.subheader("📈 KPIs")
        st.write(f"Profit: ₹{profit:,.0f}")
        st.write(f"Profit Margin: {(profit/revenue*100) if revenue else 0:.1f}%")

        st.subheader("Detailed Data")
        st.dataframe(view[['Account','Category','Amount']], use_container_width=True)
