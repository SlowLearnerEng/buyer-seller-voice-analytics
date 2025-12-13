import streamlit as st
import pandas as pd
import plotly.express as px
import os

PRODUCT_CAT_FILE = "category_product_level.csv"
SELLER_LEVEL_FILE = "seller_level.csv"

def render_product_dashboard():
    st.markdown("### 📦 Product Analytics Dashboard")
    
    if not os.path.exists(PRODUCT_CAT_FILE):
        st.warning(f"Data file `{PRODUCT_CAT_FILE}` not found.")
        return

    try:
        df = pd.read_csv(PRODUCT_CAT_FILE)
    except Exception as e:
        st.error(f"Error loading product data: {e}")
        return

    # View Selection
    products = sorted([p for p in df['product_name'].unique() if pd.notna(p)])
    view_options = ["All Products Overview"] + products
    selected_view = st.selectbox("Select Product View", view_options)

    if selected_view == "All Products Overview":
        render_all_products_overview(df)
    else:
        render_single_product_view(selected_view, df)

def render_all_products_overview(df):
    st.markdown(f"**Total Distinct Products:** {len(df)}")
    
    # KPIs
    kpi1, kpi2, kpi3 = st.columns(3)
    
    total_calls = df['call_count'].sum()
    avg_price = df['median_final_price'].mean()
    avg_negot = df['negotiation_rate_percent'].mean()
    
    kpi1.metric("Total Product Inquiries", f"{total_calls}")
    kpi2.metric("Avg Market Price (Est)", f"₹{avg_price:,.0f}")
    kpi3.metric("Avg Negotiation Rate", f"{avg_negot:.1f}%")
    
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Most In-Demand Products")
        fig_pop = px.bar(df.sort_values('call_count', ascending=False).head(10), 
                         x='call_count', y='product_name', orientation='h', title="Top Products by Volume")
        fig_pop.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_pop, use_container_width=True)
        
    with c2:
        st.subheader("Price vs Negotiation")
        fig_scatter = px.scatter(df, x='median_final_price', y='negotiation_rate_percent',
                                 size='call_count', hover_name='product_name',
                                 title="Price vs Negotiation Rate (Size=Volume)")
        st.plotly_chart(fig_scatter, use_container_width=True)
        
    st.dataframe(df, use_container_width=True)

def render_single_product_view(product_name, df):
    # Filter specific product row
    prod_data = df[df['product_name'] == product_name].iloc[0]
    
    st.markdown(f"## Product: `{product_name}`")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Inquiries", prod_data['call_count'])
    m2.metric("Median Final Price", f"₹{prod_data['median_final_price']:,.0f}")
    m3.metric("Discount Rate", f"{prod_data['avg_discount_percent']}%")
    m4.metric("Negotiation freq", f"{prod_data['negotiation_rate_percent']}%")
    
    st.markdown("---")
    
    # Specs
    st.subheader("📋 Top Requested Specifications")
    specs_raw = str(prod_data['top_requested_specs'])
    if specs_raw and specs_raw != 'nan':
        specs = specs_raw.split('|')
        st.write(" • " + "\n • ".join(specs))
    else:
        st.info("No specific specification data aggregated.")
        
    # Transactions Drill Down
    if os.path.exists(SELLER_LEVEL_FILE):
        try:
            sdf = pd.read_csv(SELLER_LEVEL_FILE)
            # Filter
            trans_df = sdf[sdf['product_name'] == product_name].copy()
            
            if not trans_df.empty:
                st.markdown(f"### 🛒 Recent Transactions ({len(trans_df)})")
                t_cols = ['call_id', 'seller_id', 'initial_price', 'final_price', 'negotiation_flag', 'price_variance']
                act_cols = [c for c in t_cols if c in trans_df.columns]
                st.dataframe(trans_df[act_cols], use_container_width=True)
                
                # Histogram of prices
                if 'final_price' in trans_df.columns and not trans_df['final_price'].isna().all():
                    fig_p = px.histogram(trans_df, x='final_price', nbins=15, title=f"Price Distribution for {product_name}")
                    st.plotly_chart(fig_p, use_container_width=True)
                    
        except Exception as e:
            st.warning("Could not load transaction details.")
