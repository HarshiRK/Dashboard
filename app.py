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

        # --- SMART CATEGORY ---
        def smart_cat(x):
            original = str(x).lower().strip()
            cleaned = re.sub(r'[^a-z0-9 ]', ' ', original)

            words = cleaned.split()
            words = [w[:-1] if w.endswith('s') else w for w in words]
            cleaned = " ".join(words)

            for key in sorted(mapping_dict.keys(), key=len, reverse=True):
                key_clean = re.sub(r'[^a-z0-9 ]', ' ', key)
                key_words = key_clean.split()
                key_words = [w[:-1] if w.endswith('s') else w for w in key_words]
                key_clean = " ".join(key_words)

                if key_clean in cleaned or key in original:
                    return mapping_dict[key]

            for word in words:
                for key in mapping_dict:
                    if word in key:
                        return mapping_dict[key]

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

        # --- MONTH FILTER ---
        months = list(data['Month'].unique())

        sel_month = st.sidebar.selectbox("Select Month", months)
        compare_month = st.sidebar.selectbox("Compare With", months)

        view = data[data['Month'] == sel_month]
        prev_view = data[data['Month'] == compare_month]

        # --- CORE VALUES ---
        assets = abs(view[view['Category'] == 'Assets']['Amount'].sum())
        liab = abs(view[view['Category'] == 'Liabilities']['Amount'].sum())
        revenue = abs(view[view['Category'] == 'Revenue']['Amount'].sum())
        expenses = abs(view[view['Category'] == 'Expenses']['Amount'].sum())
        prev_revenue = abs(prev_view[prev_view['Category'] == 'Revenue']['Amount'].sum())

        profit = revenue - expenses

        # --- RATIOS ---
        expense_ratio = (expenses / revenue * 100) if revenue else 0
        revenue_growth = ((revenue - prev_revenue) / prev_revenue * 100) if prev_revenue else 0
        profit_margin = (profit / revenue * 100) if revenue else 0
        asset_turnover = (revenue / assets) if assets else 0
        debt_ratio = (liab / assets) if assets else 0
        efficiency_ratio = (revenue / expenses) if expenses else 0

        # --- KPI SELECTOR ---
        kpi_options = [
            "Profit","Profit Margin","Expense Ratio",
            "Revenue Growth","Asset Turnover",
            "Debt Ratio","Efficiency Ratio"
        ]

        selected_kpis = st.sidebar.multiselect(
            "Select KPIs",
            kpi_options,
            default=["Profit","Profit Margin"]
        )

        st.subheader("📈 Key Performance Indicators")

        cols = st.columns(len(selected_kpis))

        for i, kpi in enumerate(selected_kpis):
            if kpi == "Profit":
                cols[i].metric("Profit", f"₹{profit:,.0f}")
            elif kpi == "Profit Margin":
                cols[i].metric("Profit Margin", f"{profit_margin:.1f}%")
            elif kpi == "Expense Ratio":
                cols[i].metric("Expense Ratio", f"{expense_ratio:.1f}%")
            elif kpi == "Revenue Growth":
                cols[i].metric("Revenue Growth", f"{revenue_growth:.1f}%")
            elif kpi == "Asset Turnover":
                cols[i].metric("Asset Turnover", f"{asset_turnover:.2f}")
            elif kpi == "Debt Ratio":
                cols[i].metric("Debt Ratio", f"{debt_ratio:.2f}")
            elif kpi == "Efficiency Ratio":
                cols[i].metric("Efficiency Ratio", f"{efficiency_ratio:.2f}")

        st.divider()

        # --- VARIANCE ---
        st.subheader("📊 Variance Analysis")

        current_summary = view.groupby('Category')['Amount'].sum()
        prev_summary = prev_view.groupby('Category')['Amount'].sum()

        variance_df = pd.DataFrame({
            'Current': current_summary,
            'Previous': prev_summary
        }).fillna(0)

        variance_df['Change'] = variance_df['Current'] - variance_df['Previous']
        variance_df['% Change'] = variance_df.apply(
            lambda x: (x['Change'] / x['Previous'] * 100) if x['Previous'] != 0 else 0,
            axis=1
        )

        st.dataframe(variance_df)

        st.divider()

        # --- AUTO INSIGHTS ---
        st.subheader("🧠 Auto Insights")

        if revenue_growth > 20:
            st.write("📈 Revenue increased strongly")
        elif revenue_growth < -10:
            st.write("📉 Revenue declined")

        if expense_ratio > 100:
            st.write("🚨 Expenses exceed revenue")

        if profit > 0:
            st.write("✅ Profitable business")
        else:
            st.write("❌ Loss making business")

        if asset_turnover < 0.5:
            st.write("⚠️ Low asset utilization")

        if liab > assets:
            st.write("⚠️ High financial risk")

        st.divider()

        # --- CHARTS ---
        col1, col2 = st.columns(2)

        with col1:
            fig = px.pie(view, values=view['Amount'].abs(), names='Category', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            trend = data.groupby('Month')['Amount'].sum().reset_index()
            fig2 = px.line(trend, x='Month', y='Amount', markers=True)
            st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        # --- TABLE ---
        st.subheader("Detailed Data")
        st.dataframe(view[['Account','Category','Amount']], use_container_width=True)
