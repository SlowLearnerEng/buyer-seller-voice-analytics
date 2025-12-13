import streamlit as st
import pandas as pd
import plotly.express as px
import os

INPUT_FILE = "Products-mapping - matched_by_llm.csv"

def render_price_opportunity_dashboard():
    st.markdown("### 💰 Price Correction & Product Opportunities")
    st.markdown("Identifies calls where the price variance for the same product exceeds **30%**, highlighting inconsistencies or negotiation gaps.")
    
    if not os.path.exists(INPUT_FILE):
        st.error(f"Input file `{INPUT_FILE}` not found. Please ensure it is present in the root directory.")
        return

    try:
        # Load Data
        df = pd.read_csv(INPUT_FILE)
        
        # Clean numeric fields
        df['call_price'] = pd.to_numeric(df['call_price'], errors='coerce')
        df['catalog_price'] = pd.to_numeric(df['catalog_price'], errors='coerce')
        df['price_diff_percent'] = pd.to_numeric(df['price_diff_percent'], errors='coerce')
        
        # Clean call_id (Remove quotes, commas)
        if 'call_id' in df.columns:
            df['call_id'] = df['call_id'].astype(str).str.replace('"', '').str.replace(',', '').str.strip()
        
        # Filter valid comparison rows
        # We need both prices and the diff
        df_clean = df.dropna(subset=['call_price', 'catalog_price', 'price_diff_percent', 'call_id'])
        
        # Sort by variance descending
        df_clean = df_clean.sort_values('price_diff_percent', ascending=False)
        
        # Filter segments
        opportunities_high = df_clean[df_clean['price_diff_percent'] > 30].copy()
        opportunities_low = df_clean[(df_clean['price_diff_percent'] <= 30) & (df_clean['price_diff_percent'] > 0)].copy()
        opportunities_exact = df_clean[df_clean['price_diff_percent'] == 0].copy()
        
        # Total Matched Count (where final_matched_pc_item_id exists in original df)
        total_matched = df['final_matched_pc_item_id'].notna().sum()
        
        # Total Unique Calls (from original DF for accurate count)
        total_calls = df['call_id'].nunique()
        
        # Summary Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Unique Calls", total_calls)
        m2.metric("Matched", total_matched)
        m3.metric("deviations >30%", len(opportunities_high))
        m4.metric("Exact Matches", len(opportunities_exact))
        
        st.markdown("---")
        
        # HIGH VARIANCE SECTION
        if not opportunities_high.empty:
            st.subheader("🚨 High Deviation Opportunities (>30%)")
            st.markdown("Call price deviates significantly from Catalog price.")
            
            display_high = opportunities_high.copy()
            display_high['price_diff_percent'] = display_high['price_diff_percent'].apply(lambda x: f"{x:.2f}%")
            
            # Chart
            st.subheader("Deviation Distribution")
            fig = px.scatter(
                opportunities_high, 
                x="product_name", 
                y="price_diff_percent",
                size="call_price",
                color="price_diff_percent",
                hover_data=['call_id', 'call_price', 'catalog_price'],
                title="Products with > 30% Deviation from Catalog",
                labels={"price_diff_percent": "Deviation (%)", "product_name": "Product"},
                color_continuous_scale="Reds"
            )
            # Enable click selection
            fig.update_layout(clickmode='event+select')
            selection = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key="price_opp_chart")
            
            # Filter Logic based on Selection
            filtered_df = display_high
            
            if selection and "selection" in selection and "points" in selection["selection"]:
                 points = selection["selection"]["points"]
                 if points:
                     # Filter by selected products
                     # Scatter points have 'x' as product_name here
                     selected_products = [p['x'] for p in points]
                     if selected_products:
                         st.info(f"Filtered by selection: {', '.join(selected_products[:3])}...")
                         filtered_df = display_high[display_high['product_name'].isin(selected_products)]
            
            # Updated Columns
            cols = ['call_id', 'product_name', 'call_price', 'catalog_price', 'price_diff_percent']
            st.dataframe(filtered_df[cols], use_container_width=True, hide_index=True)
            
        else:
            st.success("✅ No quotes with > 30% deviation found.")
            
        st.markdown("---")
        
        # LOW VARIANCE SECTION
        if not opportunities_low.empty:
            st.subheader("✅ Consistent Pricing (0% < Deviation <= 30%)")
            st.markdown("Quotes within acceptable range. Suggestion: Competitive maintenance.")
            
            display_low = opportunities_low.copy()
            display_low['price_diff_percent'] = display_low['price_diff_percent'].apply(lambda x: f"{x:.2f}%")
            display_low['Suggestion'] = "Monitor market rates."
            
            cols_low = ['call_id', 'product_name', 'call_price', 'catalog_price', 'price_diff_percent', 'Suggestion']
            st.dataframe(display_low[cols_low], use_container_width=True, hide_index=True)
        else:
            st.info("No quotes with 0% < deviation <= 30%.")

        st.markdown("---")

        # EXACT MATCH SECTION
        if not opportunities_exact.empty:
            st.subheader("🎯 Exact Match (0% deviation)")
            st.markdown("Perfect alignment with catalog price.")
            
            display_exact = opportunities_exact.copy()
            display_exact['price_diff_percent'] = "0.00%"
            
            cols_exact = ['call_id', 'product_name', 'call_price', 'catalog_price', 'price_diff_percent']
            st.dataframe(display_exact[cols_exact], use_container_width=True, hide_index=True)
        else:
            st.info("No exact price matches found.")
            
        with st.expander("View Full Data"):
            st.dataframe(df_clean, use_container_width=True)

    except Exception as e:
        st.error(f"Error processing price data: {e}")
