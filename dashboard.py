import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

SELLER_AGG_FILE = "seller_aggregated.csv"
SELLER_LEVEL_FILE = "seller_level.csv"

def render_dashboard():
    st.markdown("### 📈 Seller Analytics Dashboard")
    
    # Check files
    if not os.path.exists(SELLER_AGG_FILE):
        st.warning(f"Data file `{SELLER_AGG_FILE}` not found. Please run the insights generation script first.")
        return

    try:
        df_agg = pd.read_csv(SELLER_AGG_FILE)
    except Exception as e:
        st.error(f"Error loading aggregate data: {e}")
        return
        
    # Load detail file if available
    df_detail = None
    if os.path.exists(SELLER_LEVEL_FILE):
        try:
            df_detail = pd.read_csv(SELLER_LEVEL_FILE)
            # Ensure seller_id is string for consistent matching
            df_detail['seller_id'] = df_detail['seller_id'].fillna('').astype(str).str.replace(r'\.0$', '', regex=True)
            df_agg['seller_id'] = df_agg['seller_id'].fillna('').astype(str).str.replace(r'\.0$', '', regex=True)
        except Exception as e:
            st.warning(f"Could not load detailed call data: {e}")

    # View Selection
    seller_options = ["All Sellers"] + sorted(df_agg['seller_id'].unique().tolist())
    selected_view = st.selectbox("Select Dashboard View", seller_options)

    if selected_view == "All Sellers":
        render_all_sellers_view(df_agg)
    else:
        render_single_seller_view(selected_view, df_agg, df_detail)

def render_all_sellers_view(df):
    st.markdown(f"**Total Sellers Analyzed:** {len(df)}")

    # KPIS - User requested removal of Wholesale, Sentiment, Discount
    # Remaining meaningful consolidated metrics
    kpi1, kpi2, kpi3 = st.columns(3)
    
    total_buyers = df['unique_buyers'].sum()
    total_calls = df['total_calls'].sum()
    total_products = df['unique_products'].sum()

    kpi1.metric("Total Unique Buyers", f"{total_buyers}")
    kpi2.metric("Total Calls Analyzed", f"{total_calls}")
    kpi3.metric("Total Unique Products", f"{total_products}")

    st.markdown("---")

    # Row 1: Seller Type & Top Products
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Seller Type Distribution")
        fig_type = px.pie(df, names='seller_type', title='Seller Types', hole=0.4)
        st.plotly_chart(fig_type, use_container_width=True)

    with c2:
        st.subheader("Top Dominant Products")
        top_products = df['dominant_product'].value_counts().head(10).reset_index()
        top_products.columns = ['Product', 'Count']
        fig_bar = px.bar(top_products, x='Count', y='Product', orientation='h', title="Top Products by Seller Dominance")
        st.plotly_chart(fig_bar, use_container_width=True)

    # Row 2: Price Variance (Hist is fine)
    st.subheader("Price Variance Distribution")
    fig_hist = px.histogram(df, x='price_variance', nbins=20, title="Distribution of Price Variance across Sellers")
    st.plotly_chart(fig_hist, use_container_width=True)

    # Detailed Data View
    st.markdown("### 📋 Consolidated Seller Data")
    st.dataframe(df, use_container_width=True)

def render_single_seller_view(seller_id, df_agg, df_detail):
    # Filter for specific seller
    seller_data = df_agg[df_agg['seller_id'] == seller_id].iloc[0]
    
    st.markdown(f"## Seller Profile: `{seller_id}`")
    
    # Profile Header
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Seller Type", seller_data['seller_type'].title())
    col2.metric("Dominant Product", seller_data['dominant_product'])
    col3.metric("Total Calls", seller_data['total_calls'])
    col4.metric("Unique Buyers", seller_data['unique_buyers'])
    
    # Performance Metrics
    st.markdown("### Performance Metrics")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Negotiation Rate", f"{seller_data['negotiation_rate_percent']}%")
    m2.metric("Avg Discount", f"{seller_data['avg_discount_percent']}%")
    m3.metric("Sentiment Score", f"{seller_data['avg_seller_sentiment_num']}")
    m4.metric("Price Variance", f"{seller_data['price_variance']}")
    
    st.markdown("---")
    
    # Detailed Call History
    if df_detail is not None:
        seller_calls = df_detail[df_detail['seller_id'] == seller_id].copy()
        
        if not seller_calls.empty:
            st.markdown(f"### 📞 Call History ({len(seller_calls)} calls)")
            
            # Show table with key call details
            display_cols = ['call_id', 'product_name', 'initial_price', 'final_price', 'negotiation_flag', 'price_variance', 'seller_sentiment']
            # Filter cols that exist
            actual_cols = [c for c in display_cols if c in seller_calls.columns]
            
            st.dataframe(seller_calls[actual_cols], use_container_width=True)
            
            # Chart: Price distribution for this seller
            if 'final_price' in seller_calls.columns:
                st.subheader("Final Price Distribution")
                # Drop NAs
                valid_prices = seller_calls.dropna(subset=['final_price'])
                if not valid_prices.empty:
                    fig = px.box(valid_prices, y='final_price', points="all", title="Final Price Range")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No detailed call records found for this seller in the current dataset.")
    else:
        st.warning("Detailed call data file not found.")
