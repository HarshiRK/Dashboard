import streamlit as st
import pandas as pd
import plotly.express as px
import re
import os

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
        # --- LOAD BASE MAPPING ---
        if mapping_file:
            map_df = pd.read_csv(mapping_file)
            mapping_dict = {
                str(row['Account']).lower().strip(): row['Category']
                for _, row in map_df.iterrows()
            }
        else:
            mapping_dict = {}

        # --- LOAD LEARNED MAPPING ---
        if os.path.exists("learned_mapping.csv"):
            learned_df = pd.read_csv("learned_mapping.csv")
            learned_dict = {
                str(row['Account']).lower().strip(): row['Category']
                for _, row in learned_df.iterrows()
            }
        else:
            learned_dict = {}

        # --- SMART CATEGORY ---
        def smart_cat(x):
            original = str(x).lower().strip()
            cleaned = re.sub(r'[^a-z0-9 ]', ' ', original)

            # spelling fixes
            cleaned = cleaned.replace("maintanance", "maintenance")
            cleaned = cleaned.replace("insurence", "insurance")
            cleaned = cleaned.replace("interst", "interest")
            cleaned = cleaned.replace("taxes", "tax")
            cleaned = cleaned.replace("charges", "charge")

            # learned mapping first
            if original in learned_dict:
                return learned_dict[original]

            words = cleaned.split()
            words = [w[:-1] if w.endswith('s') else w for w in words]
            cleaned = " ".join(words)

            # base mapping
            for key in sorted(mapping_dict.keys(), key=len, reverse=True):
                if key in cleaned:
                    return mapping_dict[key]

            # keyword fallback
            if any(i in cleaned for i in ['cash','bank','receivable','debtor','inventory','stock','furniture','vehicle','equipment','asset']):
                return 'Assets'
            if any(i in cleaned for i in ['loan','payable','creditor','capital','reserve','liability']):
                return 'Liabilities'
            if any(i in cleaned for i in ['sale','income','revenue','interest']):
                return 'Revenue'
            if any(i in cleaned for i in ['expense','salary','rent','tax','insurance','maintenance','professional','charge']):
                return 'Expenses'

            return "Others"

        data['Category'] = data['Account'].apply(smart_cat)

        # --- AUTO LEARNING UI ---
        st.subheader("🧠 Auto-Learning Mapping")

        unmapped = data[data['Category']=="Others"]['Account'].unique()

        if len(unmapped) > 0:
            for acc in unmapped:
                col1, col2 = st.columns([3,1])
                with col1:
                    cat = st.selectbox(f"Map: {acc}", ["Assets","Liabilities","Revenue","Expenses"], key=acc)
                with col2:
                    if st.button(f"Save", key=f"btn_{acc}"):
                        new_row = pd.DataFrame([[acc, cat]], columns=['Account','Category'])
                        new_row.to_csv("learned_mapping.csv", mode='a', header=not os.path.exists("learned_mapping.csv"), index=False)
                        st.success(f"{acc} saved! Refresh app.")

        else:
            st.success("🎉 No unmapped accounts!")

        st.divider()

        # --- MONTH FILTER ---
        months = list(data['Month'].unique())
        sel_month = st.sidebar.selectbox("Select Month", months)
        compare_month = st.sidebar.selectbox("Compare With", months)

        view = data[data['Month'] == sel_month]
        prev_view = data[data['Month'] == compare_month]

        # --- CORE VALUES (CORRECT LOGIC) ---
        revenue = -view[view['Category'] == 'Revenue']['Amount'].sum()
        expenses = view[view['Category'] == 'Expenses']['Amount'].sum()
        assets = abs(view[view['Category'] == 'Assets']['Amount'].sum())
        liab = abs(view[view['Category'] == 'Liabilities']['Amount'].sum())
        prev_revenue = -prev_view[prev_view['Category'] == 'Revenue']['Amount'].sum()

        profit = revenue - expenses

        # --- KPIs ---
        expense_ratio = (expenses / revenue * 100) if revenue else 0
        profit_margin = (profit / revenue * 100) if revenue else 0
        revenue_growth = ((revenue - prev_revenue) / prev_revenue * 100) if prev_revenue else 0

        st.subheader("📈 KPIs")
        c1, c2, c3 = st.columns(3)
        c1.metric("Profit", f"₹{profit:,.0f}")
        c2.metric("Profit Margin", f"{profit_margin:.1f}%")
        c3.metric("Expense Ratio", f"{expense_ratio:.1f}%")

        # --- CHART ---
        fig = px.pie(view, values=view['Amount'].abs(), names='Category')
        st.plotly_chart(fig, use_container_width=True)

        # --- TABLE ---
        st.subheader("Detailed Data")
        st.dataframe(view[['Account','Category','Amount']], use_container_width=True)
