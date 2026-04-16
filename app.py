import streamlit as st
import pandas as pd
import plotly.express as px
import re

st.set_page_config(page_title="Advanced Financial Dashboard", layout="wide")

# --- CLEAN FUNCTION ---
def clean_to_float(v):
    if pd.isna(v) or str(v).strip() == "":
        return 0.0
    
    s = str(v)
    s = re.sub(r'[^0-9.-]', '', s)

    try:
        return float(s)
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
                        month = str(df.iloc[r, c]).strip()
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

        # --- SMART CATEGORY (OLD WORKING LOGIC) ---
        def smart_cat(x):
            x_str = str(x).lower().strip()
            x_str = re.sub(r'[^a-z0-9 ]', ' ', x_str)

            # Fix spelling issues
            x_str = x_str.replace("maintanance", "maintenance")
            x_str = x_str.replace("insurence", "insurance")
            x_str = x_str.replace("interst", "interest")

            # singular/plural fix
            words = x_str.split()
            words = [w[:-1] if w.endswith('s') else w for w in words]
            x_str = " ".join(words)

            # --- STEP 1: MAPPING FILE ---
            for key in sorted(mapping_dict.keys(), key=len, reverse=True):
                if key in x_str:
                    return mapping_dict[key]

            # --- STEP 2: KEYWORD FALLBACK ---
            if any(i in x_str for i in ['cash','bank','receivable','debtor','asset','inventory','stock','deposit','investment','equipment','vehicle','furniture']):
                return 'Assets'

            if any(i in x_str for i in ['payable','creditor','loan','liability','capital','reserve','provision']):
                return 'Liabilities'

            if any(i in x_str for i in ['sale','revenue','income','interest received','commission']):
                return 'Revenue'

            if any(i in x_str for i in [
                'expense','charges','cost','rent','salary','wage','supplie',
                'tax','insurance','maintenance','repair','professional',
                'consultancy','courier','transport','printing','internet',
                'depreciation','amortisation','interest paid','penalty',
                'electricity','telephone','office','admin'
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

        # --- CORRECT SIGN HANDLING ---
        assets = view[view['Category'] == 'Assets']['Amount'].sum()
        liabilities = -view[view['Category'] == 'Liabilities']['Amount'].sum()

        revenue = -view[view['Category'] == 'Revenue']['Amount'].sum()
        expenses = view[view['Category'] == 'Expenses']['Amount'].sum()

        prev_revenue = -prev_view[prev_view['Category'] == 'Revenue']['Amount'].sum()

        profit = revenue - expenses

        # --- RATIOS ---
        expense_ratio = (expenses / revenue * 100) if revenue != 0 else 0
        revenue_growth = ((revenue - prev_revenue) / prev_revenue * 100) if prev_revenue != 0 else 0
        profit_margin = (profit / revenue * 100) if revenue != 0 else 0
        asset_turnover = (revenue / assets) if assets != 0 else 0
        debt_ratio = (liabilities / assets) if assets != 0 else 0
        efficiency_ratio = (revenue / expenses) if expenses != 0 else 0

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

        k_cols = st.columns(len(selected_kpis))

        for i, kpi in enumerate(selected_kpis):
            if kpi == "Profit":
                k_cols[i].metric("Profit", f"₹{profit:,.0f}")
            elif kpi == "Profit Margin":
                k_cols[i].metric("Profit Margin", f"{profit_margin:.1f}%")
            elif kpi == "Expense Ratio":
                k_cols[i].metric("Expense Ratio", f"{expense_ratio:.1f}%")
            elif kpi == "Revenue Growth":
                k_cols[i].metric("Revenue Growth", f"{revenue_growth:.1f}%")
            elif kpi == "Asset Turnover":
                k_cols[i].metric("Asset Turnover", f"{asset_turnover:.2f}")
            elif kpi == "Debt Ratio":
                k_cols[i].metric("Debt Ratio", f"{debt_ratio:.2f}")
            elif kpi == "Efficiency Ratio":
                k_cols[i].metric("Efficiency Ratio", f"{efficiency_ratio:.2f}")

        st.divider()

        # --- CHARTS ---
        col1, col2 = st.columns(2)

        with col1:
            fig = px.pie(view, values=view['Amount'].abs(), names='Category')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            trend = data.groupby('Month')['Amount'].sum().reset_index()
            fig2 = px.line(trend, x='Month', y='Amount')
            st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        st.subheader("Detailed Data")
        st.dataframe(view[['Account','Category','Amount']], use_container_width=True)
