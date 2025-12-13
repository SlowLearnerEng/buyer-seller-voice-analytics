import streamlit as st
import pandas as pd
import plotly.express as px
import os

BUYER_LEVEL_FILE = "buyer_level.csv"

def render_buyer_dashboard():
    st.markdown("### 📉 Buyer Analytics Dashboard")
    
    if not os.path.exists(BUYER_LEVEL_FILE):
        st.warning(f"Data file `{BUYER_LEVEL_FILE}` not found.")
        return

    try:
        df = pd.read_csv(BUYER_LEVEL_FILE)
        # Clean buyer_id
        df['buyer_id'] = df['buyer_id'].fillna('').astype(str).str.replace(r'\.0$', '', regex=True)
        # Map sentiment to numeric for aggregation
        sentiment_map = {'positive': 1, 'neutral': 0, 'negative': -1, 'unknown': 0}
        df['sentiment_score'] = df['buyer_sentiment'].astype(str).str.lower().map(sentiment_map).fillna(0)
        
        # Filter: Only show buyers where business_category is not null/empty
        if 'business_category' in df.columns:
            df = df.dropna(subset=['business_category'])
            df = df[df['business_category'].astype(str).str.strip() != '']
            df = df[df['business_category'].astype(str).str.lower() != 'nan']
    except Exception as e:
        st.error(f"Error loading buyer data: {e}")
        return

    # View Selection
    buyer_ids = sorted([b for b in df['buyer_id'].unique() if b and b != 'nan'])
    view_options = ["All Buyers Overview"] + buyer_ids
    selected_view = st.selectbox("Select Buyer View", view_options)

    if selected_view == "All Buyers Overview":
        render_all_buyers_overview(df)
    else:
        render_single_buyer_view(selected_view, df)

def render_all_buyers_overview(df):
    st.markdown(f"**Total Calls/Interactions Analyzed:** {len(df)}")
    
    # KPIs
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    total_unique = df['buyer_id'].nunique()
    high_intent_pct = (df['is_high_intent'] == True).mean() * 100
    avg_sentiment = df['sentiment_score'].mean()
    
    kpi1.metric("Total Unique Buyers", f"{total_unique}")
    kpi2.metric("High Intent Calls", f"{high_intent_pct:.1f}%")
    kpi3.metric("Avg Buyer Sentiment", f"{avg_sentiment:.2f}", help="-1 to 1")
    # Most common vol type
    top_vol = df['requirement_volume_type'].mode()[0] if not df['requirement_volume_type'].empty else "N/A"
    kpi4.metric("Top Vol Type", f"{str(top_vol).title()}")
    
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Purchase Intent Distribution")
        fig_intent = px.pie(df, names='Intent_for_purchase', title='Intent Classification', hole=0.4)
        st.plotly_chart(fig_intent, use_container_width=True)
        
    with c2:
        st.subheader("Requirement Volume Type")
        fig_vol = px.bar(df['requirement_volume_type'].value_counts().reset_index(), 
                         x='count', y='requirement_volume_type', orientation='h', title="Volume Types")
        st.plotly_chart(fig_vol, use_container_width=True)
        
    st.subheader("Interactions Data")
    st.dataframe(df, use_container_width=True)

def render_single_buyer_view(buyer_id, df):
    # Filter
    buyer_df = df[df['buyer_id'] == buyer_id].copy()
    
    st.markdown(f"## Buyer Profile: `{buyer_id}`")
    
    # Key Metrics: Modified as per request
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Interactions", len(buyer_df))
    
    # Last Interaction Info for static fields (or mode usually)
    last_call = buyer_df.iloc[-1]
    
    # Buyer Type
    b_type = str(last_call.get('Buyer_Requirement_Type', 'N/A'))
    if b_type == 'nan': b_type = 'N/A'
    col2.metric("Buyer Type", b_type)
    
    # Business Category
    b_cat = str(last_call.get('business_category', 'N/A'))
    if b_cat == 'nan': b_cat = 'N/A'
    col3.metric("Business Category", b_cat)
    
    # Sentiment
    sent = str(last_call.get('buyer_sentiment', 'N/A')).title()
    col4.metric("Last Sentiment", sent)
    
    st.markdown("### 🛒 Interaction History")
    
    display_cols = ['call_id', 'product_name', 'quantity_required', 'price_expectation', 'Intent_for_purchase', 'buyer_sentiment', 'is_high_intent']
    actual_cols = [c for c in display_cols if c in buyer_df.columns]
    
    st.dataframe(buyer_df[actual_cols], use_container_width=True)
    
    # Specs requested
    all_specs = []
    for raw in buyer_df.get('variant_attributes_flat', []):
        if pd.notna(raw) and raw:
            all_specs.extend(str(raw).split(';'))
            
    if all_specs:
        st.markdown("### 📋 Requested Specifications (Aggregated)")
        from collections import Counter
        counts = Counter(all_specs).most_common(10)
        spec_df = pd.DataFrame(counts, columns=['Specification', 'Count'])
        st.dataframe(spec_df, use_container_width=True)
