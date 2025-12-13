import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

CALL_LEVEL_FILE = "call_level_insight.csv"
MATRIX_FILE = "buyer_seller_intent_confusion_matrix.csv"

def render_matrix_dashboard():
    # 1. Update Title as requested
    st.markdown("### 📞 Call Level Insight & Intent Matrix")
    
    if not os.path.exists(CALL_LEVEL_FILE) or not os.path.exists(MATRIX_FILE):
        st.error("Insights files not found. Please run the generation script.")
        return

    try:
        df_call = pd.read_csv(CALL_LEVEL_FILE)
        # Ensure call_id is string
        df_call['call_id'] = df_call['call_id'].astype(str).str.strip().str.replace(',', '')
        
        # Load Matrix (Index is Seller Intent, Cols are Buyer Intent)
        df_matrix = pd.read_csv(MATRIX_FILE, index_col=0)
        
        # Enforce Order: High, Low
        desired_order = ['High', 'Low']
        # Filter strictly to what exists in matrix + desired
        existing_cols = [c for c in desired_order if c in df_matrix.columns]
        existing_idx = [i for i in desired_order if i in df_matrix.index]
        
        # Reorder
        df_matrix = df_matrix.loc[existing_idx, existing_cols]
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return

    # Call Search Input
    c1, c2 = st.columns([1, 2])
    with c1:
        search_call_id = st.text_input("Enter Call ID (pns_call_record_id)", placeholder="e.g. 12345678").strip()
    
    current_call_intent = None
    match = pd.DataFrame() # Initialize as empty
    search_clean = ""

    if search_call_id:
        # Normalize search input as well
        search_clean = search_call_id.replace(',', '').strip()
        match = df_call[df_call['call_id'] == search_clean]
        
        if not match.empty:
            row = match.iloc[0]
            b_intent = row['Buyer_Intent_Label']
            s_intent = row['Seller_Intent_Label']
            current_call_intent = (b_intent, s_intent)
            
            st.success(f"✅ Call `{search_clean}` Found!")
            
            # Display Call Details
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Buyer Intent", b_intent, help=f"Sentiment: {row.get('buyer_sentiment','')}")
            m2.metric("Seller Intent", s_intent, help=f"Sentiment: {row.get('seller_sentiment','')}")
            m3.metric("Product", row.get('product_name', 'N/A'))
            m4.metric("Final Price", f"₹{row.get('final_price', 'N/A')}")
            
            with st.expander("Show Raw Call Details"):
                st.write(row.to_dict())
                
        else:
            st.warning(f"❌ Call ID `{search_call_id}` not found in insights data.")
    
    st.markdown("---")
    
    # Heatmap Logic
    plot_df = None
    title = ""
    
    desired_order = ['High', 'Low']
    
    if current_call_intent and not match.empty:
        st.subheader(f"Intent Matrix for Call `{search_clean}`")
        st.markdown("This matrix shows the classification of the selected call.")
        
        single_matrix = pd.crosstab(match['Seller_Intent_Label'], match['Buyer_Intent_Label'])
        plot_df = single_matrix.reindex(index=desired_order, columns=desired_order, fill_value=0)
        title = f"Confusion Matrix for ID {search_clean}"
        
    else:
        st.subheader("Global Intent Confusion Matrix")
        st.markdown("Distribution of Seller Intent vs Buyer Intent across all calls.")
        plot_df = df_matrix
        title = "Global Confusion Matrix"

    # Plot with Interaction
    # Reindex again just to be safe if desired_order keys missing in global view
    plot_df = plot_df.reindex(index=desired_order, columns=desired_order, fill_value=0)
    
    fig = px.imshow(
        plot_df, 
        text_auto=True, 
        aspect="auto",
        labels=dict(x="Buyer Intent", y="Seller Intent", color="Count"),
        color_continuous_scale="Blues",
        title=title
    )
    
    # Update layout to improve clickability
    # 'dragmode': 'select' makes the cursor a box-select tool by default
    # 'clickmode': 'event+select' enables select on click
    fig.update_layout(dragmode=False, clickmode='event+select')
    
    # Enable selection
    # Use key for uniqueness
    selection = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key="confusion_matrix_chart")
    
    # Determine Selection Source (Chart vs Manual)
    selected_buyer = None
    selected_seller = None
    
    # 1. Check Chart Selection
    if selection and "selection" in selection and "points" in selection["selection"]:
        points = selection["selection"]["points"]
        if points:
            clicked_pt = points[0]
            # Helper logic for indices logic
            def resolve_label(val, order):
                if isinstance(val, int) and 0 <= val < len(order):
                    return order[val]
                return val 
            
            selected_buyer = resolve_label(clicked_pt.get("x"), desired_order)
            selected_seller = resolve_label(clicked_pt.get("y"), desired_order)
            
    # 2. Manual Fallback
    st.markdown("---")
    c_man1, c_man2 = st.columns([1,3])
    with c_man1:
         st.markdown("**Or Filter Manually:**")
    with c_man2:
         # Create options like "Buyer:High vs Seller:Low"
         # Cartesian product
         options = ["Select a Segment..."] + [f"Buyer:{b} vs Seller:{s}" for b in desired_order for s in desired_order]
         manual_sel = st.selectbox("", options, label_visibility="collapsed")
         
         if manual_sel != "Select a Segment...":
             # Parse back
             # Format: Buyer:High vs Seller:Low
             parts = manual_sel.split(" vs ")
             b_part = parts[0].split(":")[1]
             s_part = parts[1].split(":")[1]
             
             # Override chart selection if manual is used (priority to manual if set, or just last action?)
             # Usually manual override is safer if chart failed
             selected_buyer = b_part
             selected_seller = s_part
    
    # Process Filter
    if selected_buyer and selected_seller:
        st.success(f"Selected Segment: Buyer **{selected_buyer}** vs Seller **{selected_seller}**")
        
        # Filter Data
        filtered_calls = df_call[
            (df_call['Buyer_Intent_Label'] == selected_buyer) & 
            (df_call['Seller_Intent_Label'] == selected_seller)
        ]
        
        # Display
        if not filtered_calls.empty:
            st.markdown(f"**Found {len(filtered_calls)} calls in this segment:**")
            cols = ['call_id', 'product_name', 'final_price', 'buyer_sentiment', 'negotiation_flag']
            st.dataframe(filtered_calls[cols], use_container_width=True, hide_index=True)
        else:
            st.info("No detailed call records found for this segment.")
    
    # Normalized Grid
    with st.expander("View Normalized Grid (%)"):
        if current_call_intent:
             df_pct = plot_df / plot_df.sum().sum() * 100 if plot_df.sum().sum() > 0 else plot_df
        else:
             total = df_call.shape[0] # Approx total
             # Or calc from df
             df_pct = pd.crosstab(df_call['Seller_Intent_Label'], df_call['Buyer_Intent_Label'], normalize='all') * 100
             df_pct = df_pct.reindex(index=desired_order, columns=desired_order, fill_value=0)
             
        st.dataframe(df_pct.style.format("{:.2f}%").background_gradient(cmap="Blues"), use_container_width=True)

    st.markdown("---")
    
    # 2. Start of New Section: ShipWith Analysis
    st.markdown("### 🚚 Delivery & ShipWith Analysis")
    st.markdown("Identifying opportunities where **Buyer is responsible for delivery** but **Seller capability is Unknown/No**.")
    
    # Check if columns exist (they should after regen)
    if 'delivery_responsibility' in df_call.columns and 'seller_delivers_to_buyer_location' in df_call.columns:
        
        # Create temp normalized columns for easier filtering
        df_call['del_resp_norm'] = df_call['delivery_responsibility'].astype(str).str.lower().str.strip()
        df_call['seller_del_norm'] = df_call['seller_delivers_to_buyer_location'].astype(str).str.lower().str.strip()
        
        # Logic: Buyer responsible AND (Seller No OR Seller Unknown OR Seller Empty)
        # Note: 'nan' is handled by astype(str) -> 'nan'
        target_seller_vals = ['no', 'unknown', 'nan', '']
        
        opportunities = df_call[
            (df_call['del_resp_norm'] == 'buyer') & 
            (df_call['seller_del_norm'].isin(target_seller_vals))
        ].copy()
        
        if not opportunities.empty:
            st.success(f"✅ **{len(opportunities)}** Potential ShipWith Leads Found")
            st.markdown("**Action:** Generate intent for **ShipWith**.")
            
            # Display Table
            cols_to_show = ['call_id', 'product_name', 'final_price', 'delivery_responsibility', 'seller_delivers_to_buyer_location']
            # Intersection with existing columns
            cols_to_show = [c for c in cols_to_show if c in opportunities.columns]
            
            st.dataframe(opportunities[cols_to_show], use_container_width=True, hide_index=True)
            
            # Simple Metric
            # Count by Product Name (Top 5)
            st.markdown("#### Top Products for ShipWith")
            top_prods = opportunities['product_name'].value_counts().head(5)
            st.bar_chart(top_prods)
            
        else:
            st.info("No ShipWith opportunities found (No calls match criteria: Buyer Delivery + Seller Unknown/No).")
            
    else:
        st.warning("Delivery columns (`delivery_responsibility`, `seller_delivers_to_buyer_location`) not found in data. Please ensure insights were regenerated.")
