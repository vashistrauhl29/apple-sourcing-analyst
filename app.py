import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="🍎 Apple Global Sourcing Command Center")

# --- 1. INTELLIGENCE LAYER ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("apple_products.csv")
    except FileNotFoundError:
        st.error("🚨 'apple_products.csv' not found. Please ensure it is in the project folder.")
        st.stop()
    
    def clean_pct(val):
        if isinstance(val, str):
            return float(val.replace("%", "").strip()) / 100
        return float(val)

    df["Base_Duty_Rate"] = df["Base_Duty_Rate"].apply(clean_pct)
    df["Section_301_Tariff"] = df["Section_301_Tariff"].apply(clean_pct)
    return df

product_df = load_data()

# --- 2. LOGIC ENGINE (TCO) ---
def calculate_tco(fob_price, freight, lead_time_weeks, interest_rate, base_duty, section_301, country_type):
    """
    Calculates Total Cost of Ownership including Duties and Inventory Carrying Cost.
    """
    if country_type == "Mexico":
        applied_duty = 0.0
        tariff_301 = 0.0
    elif country_type == "China":
        applied_duty = base_duty
        tariff_301 = section_301
    else: # Vietnam, India, etc.
        applied_duty = base_duty
        tariff_301 = 0.0
    
    cost_duty = fob_price * applied_duty
    cost_301 = fob_price * tariff_301
    cost_inventory = fob_price * (interest_rate / 52) * lead_time_weeks
    
    total_landed_cost = fob_price + freight + cost_duty + cost_301 + cost_inventory
    
    return {
        "FOB Price": fob_price,
        "Freight": freight,
        "Base Duty": cost_duty,
        "Section 301 Penalty": cost_301,
        "Inventory Cost": cost_inventory,
        "Total TCO": total_landed_cost
    }

# --- 3. AI ANALYST ENGINE (UPDATED) ---
def generate_ai_insight(res_a, res_b, savings, alt_origin, lead_time_diff):
    """
    Generates a text-based executive summary based on the data deltas.
    """
    # 1. The Verdict
    if savings > 0:
        verdict = "✅ **Recommendation: DIVERSIFY to " + alt_origin + "**"
        reason = f"Yields a net saving of **${savings:,.2f} per unit**."
    else:
        verdict = "⚠️ **Recommendation: REMAIN in China**"
        reason = f"Moving to {alt_origin} increases cost by **${abs(savings):,.2f} per unit**."

    # 2. The "Why" (Drivers) - Fixed Thresholds
    drivers = []
    
    # A. Tariff Impact
    tariff_a = res_a['Section 301 Penalty'] + res_a['Base Duty']
    tariff_b = res_b['Section 301 Penalty'] + res_b['Base Duty']
    tariff_gap = tariff_a - tariff_b
    
    if tariff_gap > 0.01:
        drivers.append(f"Avoiding China tariffs saves **${tariff_gap:,.2f}** in duties.")
    elif tariff_gap < -0.01:
        drivers.append(f"However, tariffs are higher in {alt_origin} by **${abs(tariff_gap):,.2f}**.")
    
    # B. Logistics Impact (Freight)
    freight_gap = res_b['Freight'] - res_a['Freight']
    if freight_gap > 0.01:
        drivers.append(f"Logistics costs increase by **${freight_gap:,.2f}** due to distance/mode.")
    elif freight_gap < -0.01:
        drivers.append(f"Logistics costs decrease by **${abs(freight_gap):,.2f}**.")

    # C. Inventory Impact (Cost of Capital)
    inventory_gap = res_b['Inventory Cost'] - res_a['Inventory Cost']
    if inventory_gap > 0.01:
        drivers.append(f"Extended lead times add **${inventory_gap:,.2f}** in hidden inventory holding costs.")
    elif inventory_gap < -0.01:
        drivers.append(f"Faster lead times save **${abs(inventory_gap):,.2f}** in inventory costs.")
        
    # Fallback if nothing changed
    if not drivers:
        drivers.append("No significant cost drivers detected (Deltas < $0.01).")
        
    return verdict, reason, drivers

# --- 4. SIDEBAR CONTROLS ---
st.sidebar.title("🍎 Control Tower")
selected_product_name = st.sidebar.selectbox("Select Target SKU", product_df["Product_Name"].unique())
product_data = product_df[product_df["Product_Name"] == selected_product_name].iloc[0]

st.sidebar.markdown("---")
st.sidebar.markdown("### 💰 Financial Inputs")
interest_rate = st.sidebar.slider("Cost of Capital (Annual %)", 5.0, 20.0, 12.0, step=0.5) / 100

# --- 5. MAIN INTERFACE ---
st.title("🍎 Global Sourcing Command Center")
st.markdown(f"### TCO Analysis: **{selected_product_name}**")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Unit Cost (FOB)", f"${product_data['Unit_Price_USD']:,.2f}")
col2.metric("Weight", f"{product_data['Weight_kg']} kg")
col3.metric("Tariff Risk (301)", f"{product_data['Section_301_Tariff']:.1%}",
            delta_color="inverse", delta="Active" if product_data['Section_301_Tariff'] > 0 else "None")
col4.metric("Cost of Capital", f"{interest_rate:.1%}")

st.markdown("---")

# --- SCENARIO INPUTS ---
col_a, col_b = st.columns(2)

def estimate_freight(weight, mode):
    if mode == "Air": return weight * 8.50 
    return weight * 0.50

# OPTION A: CHINA
with col_a:
    st.header("🇨🇳 Option A: China")
    a_mode = st.radio("Logistics Mode (A)", ["Ocean 🚢", "Air ✈️"], horizontal=True, index=0)
    
    if "Ocean" in a_mode:
        def_a_lead, def_a_freight = 5, estimate_freight(product_data['Weight_kg'], "Ocean")
    else:
        def_a_lead, def_a_freight = 1, estimate_freight(product_data['Weight_kg'], "Air")
        
    col_a1, col_a2 = st.columns(2)
    
    # FIX: Added dynamic keys (f"{a_mode}") to force reset when mode changes
    a_lead = col_a1.number_input("Lead Time (Wks)", value=float(def_a_lead), key=f"a_lead_{a_mode}")
    a_freight = col_a2.number_input("Freight (USD)", value=float(f"{def_a_freight:.2f}"), key=f"a_freight_{a_mode}")

    res_a = calculate_tco(
        product_data['Unit_Price_USD'], a_freight, a_lead, interest_rate,
        product_data['Base_Duty_Rate'], product_data['Section_301_Tariff'], "China"
    )
    st.metric("Total TCO", f"${res_a['Total TCO']:,.2f}", delta="Baseline", delta_color="off")

# OPTION B: CHALLENGER
with col_b:
    st.header("🌏 Option B: Challenger")
    alt_origin = st.selectbox("Select Origin", ["Vietnam", "India", "Mexico", "Thailand"])
    b_mode = st.radio("Logistics Mode (B)", ["Ocean 🚢", "Air ✈️"], horizontal=True, index=0)
    
    if "Ocean" in b_mode:
        def_b_lead = 7 if alt_origin != "Mexico" else 2 
        def_b_freight = estimate_freight(product_data['Weight_kg'], "Ocean") * 1.2
    else:
        def_b_lead = 1
        def_b_freight = estimate_freight(product_data['Weight_kg'], "Air") * 1.1

    col_b1, col_b2 = st.columns(2)
    
    # FIX: Added dynamic keys (f"{b_mode}") here as well
    b_lead = col_b1.number_input("Lead Time (Wks)", value=float(def_b_lead), key=f"b_lead_{b_mode}")
    b_freight = col_b2.number_input("Freight (USD)", value=float(f"{def_b_freight:.2f}"), key=f"b_freight_{b_mode}")
    
    b_type = "Mexico" if alt_origin == "Mexico" else "Standard"

    res_b = calculate_tco(
        product_data['Unit_Price_USD'], b_freight, b_lead, interest_rate,
        product_data['Base_Duty_Rate'], product_data['Section_301_Tariff'], b_type
    )
    
    savings = res_a['Total TCO'] - res_b['Total TCO']
    st.metric("Total TCO", f"${res_b['Total TCO']:,.2f}", 
              delta=f"${savings:,.2f} Savings" if savings > 0 else f"-${abs(savings):,.2f} Cost Increase")

# --- 6. VISUALIZATION (THE FIX) ---
st.markdown("---")
col_viz_1, col_viz_2 = st.columns([3, 1])

with col_viz_1:
    st.subheader("📊 Cost Structure Analysis")
with col_viz_2:
    # THE SCALING FIX: Checkbox to hide FOB
    exclude_fob = st.checkbox("🔍 Focus View (Exclude Product Cost)", value=False)

categories = ["FOB Price", "Freight", "Base Duty", "Section 301 Penalty", "Inventory Cost"]
if exclude_fob:
    categories.remove("FOB Price") # Drop the massive bar

values_a = [res_a[cat] for cat in categories]
values_b = [res_b[cat] for cat in categories]

fig = go.Figure(data=[
    go.Bar(name='China', x=categories, y=values_a, marker_color='#FF4B4B'),
    go.Bar(name=alt_origin, x=categories, y=values_b, marker_color='#00CC96')
])

fig.update_layout(barmode='group', height=400, title_text="Landed Cost Breakdown")
st.plotly_chart(fig, use_container_width=True)

# --- 7. EXECUTIVE AI SUMMARY ---
st.subheader("AI Sourcing Analyst Recommendation")

verdict, reason, drivers = generate_ai_insight(res_a, res_b, savings, alt_origin, b_lead - a_lead)

with st.container():
    st.markdown(f"### {verdict}")
    st.markdown(f"**Reason:** {reason}")
    st.markdown("**Key Drivers:**")
    for driver in drivers:
        st.markdown(f"- {driver}")
