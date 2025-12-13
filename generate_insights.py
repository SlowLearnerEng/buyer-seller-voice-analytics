import pandas as pd
import numpy as np
import json
import logging
import sys
import glob
import os
from collections import Counter

# Configuration
INPUT_FILE_PATTERN = "output_20251212_*.csv"  # Flexible pattern to catch latest file
RAW_DATA_FILE = "Raw data.csv"
OUTPUT_SELLER = "seller_level.csv"
OUTPUT_BUYER = "buyer_level.csv"
OUTPUT_CATEGORY = "category_product_level.csv"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_latest_input_file():
    files = glob.glob(INPUT_FILE_PATTERN)
    if not files:
        logger.error(f"No files matching pattern {INPUT_FILE_PATTERN} found.")
        sys.exit(1)
    # Sort by modification time, latest first
    files.sort(key=os.path.getmtime, reverse=True)
    latest_file = files[0]
    logger.info(f"Using latest input file: {latest_file}")
    return latest_file

def load_raw_data_map():
    """Loans Raw data.csv and returns a dict mapping normalized call_id to details."""
    if not os.path.exists(RAW_DATA_FILE):
        logger.warning(f"{RAW_DATA_FILE} not found. ID enrichment will be skipped.")
        return {}
    
    try:
        # Load raw data
        # Note: 'pns_call_receiver_glusr_id' is expected column name in file
        df = pd.read_csv(RAW_DATA_FILE)
        
        mapping = {}
        for _, row in df.iterrows():
            # Normalize call_id: remove commas, strip
            raw_cid = str(row.get('pns_call_record_id', '')).replace(',', '').strip()
            seller_id = str(row.get('pns_call_receiver_glusr_id', '')).strip()
            buyer_id = str(row.get('pns_call_caller_glusr_id', '')).strip()
            
            if raw_cid:
                mapping[raw_cid] = {
                    'seller_id': seller_id,
                    'buyer_id': buyer_id
                }
        logger.info(f"Loaded ID mapping for {len(mapping)} calls from {RAW_DATA_FILE}")
        return mapping
    except Exception as e:
        logger.error(f"Error loading {RAW_DATA_FILE}: {e}")
        return {}

def clean_money(val):
    if pd.isna(val) or val == '':
        return np.nan
    try:
        # Remove currency symbols/commas if any (simple approach)
        val_str = str(val).replace(',', '').strip()
        return float(val_str)
    except:
        return np.nan

def normalize_call_id(cid):
    return str(cid).replace(',', '').strip()

def generate_seller_level(df, id_map):
    logger.info("Generating Seller Level Insights...")
    
    seller_rows = []
    
    # Group strategy: To handle multi-row inputs per call
    grouped = df.groupby('call_id')
    
    for call_id_raw, group in grouped:
        # Normalize call_id for lookup
        call_id = normalize_call_id(call_id_raw)
        
        # Lookup IDs
        mapped_ids = id_map.get(call_id, {})
        
        # Extract static fields from first row
        first_row = group.iloc[0]
        
        # Use mapped ID if available, else empty (or fallback if it was in input)
        seller_id = mapped_ids.get('seller_id', first_row.get('seller_id', ''))
        
        product_id = first_row.get('product_id', '')
        product_name = first_row.get('product_name', '')
        product_kw = first_row.get('product_kw', '')
        
        # Price Analysis
        prices = []
        currencies = []
        types = []
        
        for _, row in group.iterrows():
            p_val = clean_money(row.get('price_value'))
            if not pd.isna(p_val):
                prices.append(p_val)
                currencies.append(str(row.get('price_currency','')).strip())
                types.append(str(row.get('price_type','')).strip())
        
        # Initial, Inter, Final
        initial_price = prices[0] if prices else np.nan
        final_price = prices[-1] if prices else np.nan
        
        intermediate_price = ""
        if len(prices) > 2:
            mid_prices = prices[1:-1]
            intermediate_price = "|".join([str(p) for p in mid_prices])
            
        # Discount
        discount_percent = np.nan
        if not pd.isna(initial_price) and not pd.isna(final_price) and initial_price > 0:
            discount_percent = round(((initial_price - final_price) / initial_price) * 100, 2)
            
        # Currency (mode or first)
        price_currency = currencies[0] if currencies else first_row.get('moq_currency', '')
        
        # MOQ data
        moq_val = first_row.get('moq_value', '')
        moq_unit = first_row.get('moq_unit', '')
        moq_price = first_row.get('moq_price', '')
        
        # Unit Price
        unit_price = first_row.get('unit_price', '')
        
        # Price Type (mode)
        price_type = Counter(types).most_common(1)[0][0] if types else ''
        
        # Negotiation Flag
        distinct_prices = len(set(prices))
        negotiation_flag = "yes" if distinct_prices > 1 and (discount_percent > 0 if not pd.isna(discount_percent) else False) else "no"
        
        number_of_price_revisions = len(prices) if distinct_prices > 1 else 0
        
        # Other cols
        other_cond_notes = first_row.get('other_conditions_notes', '')
        other_cond_pay = first_row.get('other_conditions_payment_terms', '')
        del_resp = first_row.get('delivery_responsibility', '')
        seller_delivers = first_row.get('seller_delivers_to_buyer_location', '')
        seller_sentiment = first_row.get('Seller Sentiment', '')
        
        row_dict = {
            'call_id': call_id, # Use normalized ID for output consistency? Or raw? User requested "normalized string".
            'seller_id': seller_id,
            'product_id': product_id,
            'product_name': product_name,
            'product_kw': product_kw,
            'initial_price': initial_price,
            'intermediate_price': intermediate_price,
            'final_price': final_price,
            'discount_percent': discount_percent,
            'price_currency': price_currency,
            'moq_value': moq_val,
            'moq_unit': moq_unit,
            'moq_price': moq_price,
            'unit_price': unit_price,
            'price_type': price_type,
            'other_conditions_notes': other_cond_notes,
            'other_conditions_payment_terms': other_cond_pay,
            'delivery_responsibility': del_resp,
            'seller_delivers_to_buyer_location': seller_delivers,
            'seller_sentiment': seller_sentiment,
            'negotiation_flag': negotiation_flag,
            'number_of_price_revisions': number_of_price_revisions,
            'notes': ''
        }
        seller_rows.append(row_dict)
        
    pd.DataFrame(seller_rows).to_csv(OUTPUT_SELLER, index=False)
    logger.info(f"Saved {OUTPUT_SELLER}")

def generate_buyer_level(df, id_map):
    logger.info("Generating Buyer Level Insights...")
    
    buyer_rows = []
    grouped = df.groupby('call_id')
    
    for call_id_raw, group in grouped:
        call_id = normalize_call_id(call_id_raw)
        mapped_ids = id_map.get(call_id, {})
        first_row = group.iloc[0]
        
        buyer_id = mapped_ids.get('buyer_id', first_row.get('buyer_id', ''))
        
        # Combined quantity
        qty_val = str(first_row.get('quantity_required_value', '')).replace('nan', '').strip()
        qty_unit = str(first_row.get('quantity_required_unit', '')).replace('nan', '').strip()
        quantity_required = f"{qty_val} {qty_unit}".strip()
        
        # Variant attributes flat
        var_attr_raw = first_row.get('variant_attributes', '')
        flat_attr = ""
        try:
            if var_attr_raw and var_attr_raw != 'nan':
                attr_dict = json.loads(var_attr_raw)
                flat_attr = ";".join([f"{k}:{v}" for k,v in attr_dict.items()])
        except:
            flat_attr = var_attr_raw 
            
        # Price expectation
        price_expectation = clean_money(first_row.get('unit_price', ''))
        
        # High Intent Logic
        intent = str(first_row.get('Intent for purchase', ''))
        buyer_sentiment = str(first_row.get('Buyer Sentiment', '')).lower()
        final_price_present = any(not pd.isna(clean_money(r.get('price_value'))) for _, r in group.iterrows())
        
        is_high_intent = (
            bool(intent and intent != 'nan' and intent != 'unknown') and 
            (buyer_sentiment in ['positive', 'neutral']) and 
            final_price_present
        )
        
        row_dict = {
            'call_id': call_id,
            'buyer_id': buyer_id,
            'product_id': first_row.get('product_id', ''),
            'product_name': first_row.get('product_name', ''),
            'quantity_required': quantity_required,
            'requirement_volume_type': first_row.get('requirement_volume_type', ''),
            'Buyer_Requirement_Type': first_row.get('Buyer Requirement Type', ''),
            'business_category': first_row.get('Business Category', ''),
            'variant_attributes_flat': flat_attr,
            'applies_to_specifications': first_row.get('applies_to_specifications', ''),
            'Intent_for_purchase': first_row.get('Intent for purchase', ''),
            'buyer_sentiment': first_row.get('Buyer Sentiment', ''),
            'Is_Seller_deals_in_product': first_row.get('Is_Seller_deals_in_product ', ''),
            'delivery_location': first_row.get('delivery_location', ''),
            'price_expectation': price_expectation,
            'is_high_intent': is_high_intent,
            'notes': ''
        }
        buyer_rows.append(row_dict)
        
    pd.DataFrame(buyer_rows).to_csv(OUTPUT_BUYER, index=False)
    logger.info(f"Saved {OUTPUT_BUYER}")

def generate_category_level(seller_df, buyer_df):
    logger.info("Generating Category Level Insights...")
    
    # We aggregate based on unique products found in seller_df/buyer_df
    # Group by product_name, product_id, product_kw, business_category
    
    # Join business_category from buyer_df to seller_df for aggregation?
    # Or just use buyer_df for base?
    # Seller DF has pricing info. Buyer DF has business category info.
    # Let's merge them on call_id.
    
    # Read output files back in or pass DFs? Passing DFs.
    # But seller_df and buyer_df passed here are not dataframes yet.
    # Let's rebuild basic DFs from the generated files to be safe/clean
    
    sdf = pd.read_csv(OUTPUT_SELLER)
    bdf = pd.read_csv(OUTPUT_BUYER)
    
    # Merge on call_id to get full picture
    merged = sdf.merge(bdf[['call_id', 'Business Category']], on='call_id', how='left') # Wait, BDF cols might differ
    # Actually bdf has 'Business Category' ?? Check code above. 
    # generate_buyer_level mapping uses 'Business Category' from input DF.
    # Ah, I need to check if I included 'Business Category' in buyer_level.csv. 
    # Looking at generate_buyer_level, I did NOT include 'business_category' explicitly in the requested columns list!
    # User requested columns for B: ..., Intent_for_purchase, buyer_sentiment, ...
    # Wait, "Category/product level insights... group by ... Business Category if available"
    # So I should probably fetch Business Category from source df again.
    
    # Let's assume input DF is available to this func or just merge from source.
    # Easier: Aggregate from source DF directly.
    pass

def generate_category_level_from_source(df, seller_df_path):
    logger.info("Generating Category Level Insights...")
    
    # Re-read seller results for calculated metrics (like Negotiation Flag)
    sdf = pd.read_csv(seller_df_path)
    
    # Prepare global view
    # We need Business Category. It is in source df.
    # We need metrics from seller_level (discount, negotiation).
    
    # Merge source (for categorization) with seller_level (for metrics)
    # Using call_id as key.
    # Source df has multiple rows. Group source first to get category per product.
    
    source_grouped = df.groupby(['product_id', 'call_id']).first().reset_index()
    
    # Ensure join keys are strings
    source_grouped['call_id'] = source_grouped['call_id'].astype(str).str.replace(',', '').str.strip()
    sdf['call_id'] = sdf['call_id'].astype(str).str.replace(',', '').str.strip()
    
    # Merge
    merged = source_grouped.merge(sdf, on=['call_id', 'product_id'], how='inner', suffixes=('', '_seller'))
    
    # Now group by Product Identity
    # Group Key: product_name, product_id, product_kw, Business Category
    # 'Business Category' is the column name in source
    
    results = []
    
    # Grouping
    group_cols = ['product_name', 'product_id', 'product_kw', 'Business Category']
    # Handle missing cols
    actual_group_cols = [c for c in group_cols if c in merged.columns]
    
    grouped = merged.groupby(actual_group_cols)
    
    for name, group in grouped:
        # Unpack name
        p_name = name[0]
        p_id = name[1]
        p_kw = name[2]
        p_biz = name[3] if len(name) > 3 else ''
        
        curr_seller_df = group # This group contains joined data
        
        call_count = group['call_id'].nunique()
        unique_seller_count = group['seller_id'].nunique() if 'seller_id' in group.columns and not group['seller_id'].isna().all() else call_count # Approximation if seller_id missing
        unique_buyer_count = group['buyer_id'].nunique() if 'buyer_id' in group.columns and not group['buyer_id'].isna().all() else call_count
        
        # Metrics
        median_initial = curr_seller_df['initial_price'].median()
        median_final = curr_seller_df['final_price'].median()
        avg_discount = curr_seller_df['discount_percent'].mean()
        
        # Negotiation Rate
        negot_yes = (curr_seller_df['negotiation_flag'] == 'yes').sum()
        negotiation_rate = round((negot_yes / len(curr_seller_df)) * 100, 2)
        
        # Top Specs
        # Source: 'variant_attributes' from source DF.
        all_specs = []
        for raw in group['variant_attributes']:
             try:
                 # Try parse JSON
                 d = json.loads(raw)
                 for k,v in d.items():
                     all_specs.append(f"{k}:{v}")
             except:
                 pass
        
        top_specs_counts = Counter(all_specs).most_common(5)
        top_requested_specs = "|".join([x[0] for x in top_specs_counts])
        
        # Quantity Mode
        qty_counts = group['quantity_required_value'].astype(str) + " " + group['quantity_required_unit'].astype(str)
        # Filter out empty/nan
        valid_qtys = [q for q in qty_counts if 'nan' not in q and q.strip() != '']
        most_common_quantity = Counter(valid_qtys).most_common(1)[0][0] if valid_qtys else ''
        
        # Sentiments
        # Map: positive=1, neutral=0, negative=-1
        def map_sentiment(s):
            s = str(s).lower()
            if 'positive' in s: return 1
            if 'negative' in s: return -1
            return 0
            
        buyer_sent_scores = group['Buyer Sentiment'].apply(map_sentiment)
        seller_sent_scores = group['Seller Sentiment'].apply(map_sentiment) # Using merged col
        
        buyer_sentiment_avg = round(buyer_sent_scores.mean(), 2)
        seller_sentiment_avg = round(seller_sent_scores.mean(), 2)
        
        price_range_low = curr_seller_df['final_price'].min()
        price_range_high = curr_seller_df['final_price'].max()
        
        results.append({
            'product_name': p_name,
            'product_id': p_id,
            'product_kw': p_kw,
            'business_category': p_biz,
            'call_count': call_count,
            'unique_seller_count': unique_seller_count,
            'unique_buyer_count': unique_buyer_count,
            'median_initial_price': median_initial,
            'median_final_price': median_final,
            'avg_discount_percent': round(avg_discount, 2),
            'negotiation_rate_percent': negotiation_rate,
            'top_requested_specs': top_requested_specs,
            'most_common_quantity': most_common_quantity,
            'seller_sentiment_avg': seller_sentiment_avg,
            'price_range_low': price_range_low,
            'price_range_high': price_range_high
        })
        
    pd.DataFrame(results).to_csv(OUTPUT_CATEGORY, index=False)
    logger.info(f"Saved {OUTPUT_CATEGORY}")

def generate_category_level(seller_df, buyer_df):
    logger.info("Generating Category Level Insights...")
    
    # We aggregate based on unique products found in seller_df/buyer_df
    # Group by product_name, product_id, product_kw, business_category
    
    # Join business_category from buyer_df to seller_df for aggregation?
    # Or just use buyer_df for base?
    # Seller DF has pricing info. Buyer DF has business category info.
    # Let's merge them on call_id.
    
    # Read output files back in or pass DFs? Passing DFs.
    # But seller_df and buyer_df passed here are not dataframes yet.
    # Let's rebuild basic DFs from the generated files to be safe/clean
    
    sdf = pd.read_csv(OUTPUT_SELLER)
    bdf = pd.read_csv(OUTPUT_BUYER)
    
    # Merge on call_id to get full picture
    merged = sdf.merge(bdf[['call_id', 'Business Category']], on='call_id', how='left') # Wait, BDF cols might differ
    # Actually bdf has 'Business Category' ?? Check code above. 
    # generate_buyer_level mapping uses 'Business Category' from input DF.
    # Ah, I need to check if I included 'Business Category' in buyer_level.csv. 
    # Looking at generate_buyer_level, I did NOT include 'business_category' explicitly in the requested columns list!
    # User requested columns for B: ..., Intent_for_purchase, buyer_sentiment, ...
    # Wait, "Category/product level insights... group by ... Business Category if available"
    # So I should probably fetch Business Category from source df again.
    
    # Let's assume input DF is available to this func or just merge from source.
    # Easier: Aggregate from source DF directly.
    pass

def generate_category_level_from_source(df, seller_df_path):
    logger.info("Generating Category Level Insights...")
    
    # Re-read seller results for calculated metrics (like Negotiation Flag)
    sdf = pd.read_csv(seller_df_path)
    
    # Prepare global view
    # We need Business Category. It is in source df.
    # We need metrics from seller_level (discount, negotiation).
    
    # Merge source (for categorization) with seller_level (for metrics)
    # Using call_id as key.
    # Source df has multiple rows. Group source first to get category per product.
    
    source_grouped = df.groupby(['product_id', 'call_id']).first().reset_index()
    
    # Ensure join keys are strings
    source_grouped['call_id'] = source_grouped['call_id'].astype(str).str.replace(',', '').str.strip()
    sdf['call_id'] = sdf['call_id'].astype(str).str.replace(',', '').str.strip()
    
    # Merge
    merged = source_grouped.merge(sdf, on=['call_id', 'product_id'], how='inner', suffixes=('', '_seller'))
    
    # Now group by Product Identity
    # Group Key: product_name, product_id, product_kw, Business Category
    # 'Business Category' is the column name in source
    
    results = []
    
    # Grouping
    group_cols = ['product_name', 'product_id', 'product_kw', 'Business Category']
    # Handle missing cols
    actual_group_cols = [c for c in group_cols if c in merged.columns]
    
    grouped = merged.groupby(actual_group_cols)
    
    for name, group in grouped:
        # Unpack name
        p_name = name[0]
        p_id = name[1]
        p_kw = name[2]
        p_biz = name[3] if len(name) > 3 else ''
        
        curr_seller_df = group # This group contains joined data
        
        call_count = group['call_id'].nunique()
        unique_seller_count = group['seller_id'].nunique() if 'seller_id' in group.columns and not group['seller_id'].isna().all() else call_count # Approximation if seller_id missing
        unique_buyer_count = group['buyer_id'].nunique() if 'buyer_id' in group.columns and not group['buyer_id'].isna().all() else call_count
        
        # Metrics
        median_initial = curr_seller_df['initial_price'].median()
        median_final = curr_seller_df['final_price'].median()
        avg_discount = curr_seller_df['discount_percent'].mean()
        
        # Negotiation Rate
        negot_yes = (curr_seller_df['negotiation_flag'] == 'yes').sum()
        negotiation_rate = round((negot_yes / len(curr_seller_df)) * 100, 2)
        
        # Top Specs
        # Source: 'variant_attributes' from source DF.
        all_specs = []
        for raw in group['variant_attributes']:
             try:
                 # Try parse JSON
                 d = json.loads(raw)
                 for k,v in d.items():
                     all_specs.append(f"{k}:{v}")
             except:
                 pass
        
        top_specs_counts = Counter(all_specs).most_common(5)
        top_requested_specs = "|".join([x[0] for x in top_specs_counts])
        
        # Quantity Mode
        qty_counts = group['quantity_required_value'].astype(str) + " " + group['quantity_required_unit'].astype(str)
        # Filter out empty/nan
        valid_qtys = [q for q in qty_counts if 'nan' not in q and q.strip() != '']
        most_common_quantity = Counter(valid_qtys).most_common(1)[0][0] if valid_qtys else ''
        
        # Sentiments
        # Map: positive=1, neutral=0, negative=-1
        def map_sentiment(s):
            s = str(s).lower()
            if 'positive' in s: return 1
            if 'negative' in s: return -1
            return 0
            
        buyer_sent_scores = group['Buyer Sentiment'].apply(map_sentiment)
        seller_sent_scores = group['Seller Sentiment'].apply(map_sentiment) # Using merged col
        
        buyer_sentiment_avg = round(buyer_sent_scores.mean(), 2)
        seller_sentiment_avg = round(seller_sent_scores.mean(), 2)
        
        price_range_low = curr_seller_df['final_price'].min()
        price_range_high = curr_seller_df['final_price'].max()
        
        results.append({
            'product_name': p_name,
            'product_id': p_id,
            'product_kw': p_kw,
            'business_category': p_biz,
            'call_count': call_count,
            'unique_seller_count': unique_seller_count,
            'unique_buyer_count': unique_buyer_count,
            'median_initial_price': median_initial,
            'median_final_price': median_final,
            'avg_discount_percent': round(avg_discount, 2),
            'negotiation_rate_percent': negotiation_rate,
            'top_requested_specs': top_requested_specs,
            'most_common_quantity': most_common_quantity,
            'buyer_sentiment_avg': buyer_sentiment_avg,
            'seller_sentiment_avg': seller_sentiment_avg,
            'price_range_low': price_range_low,
            'price_range_high': price_range_high
        })
        
    pd.DataFrame(results).to_csv(OUTPUT_CATEGORY, index=False)
    logger.info(f"Saved {OUTPUT_CATEGORY}")

def generate_aggregated_seller_level(output_seller, output_buyer):
    logger.info("Generating Aggregated Seller Profile...")
    OUTPUT_AGG = "seller_aggregated.csv"
    
    try:
        sdf = pd.read_csv(output_seller)
        bdf = pd.read_csv(output_buyer)
        
        # Merge to get buyer_id and volume info into seller data
        # Ensure join keys are strings
        sdf['call_id'] = sdf['call_id'].astype(str).str.replace(',', '').str.strip()
        bdf['call_id'] = bdf['call_id'].astype(str).str.replace(',', '').str.strip()
        
        # Merge
        merged = sdf.merge(bdf[['call_id', 'buyer_id', 'requirement_volume_type']], on='call_id', how='left')
        
        aggregated_rows = []
        
        # Group by seller_id
        # Handle missing seller_ids by grouping by call_id? No, User said "For each unique seller_id". 
        # If seller_id is missing, we exclude or handle as "Unknown"? 
        # User defined seller_level.csv generation: "if no seller_id available use call_id + product"
        # Since we use seller_level.csv as input, 'seller_id' should be populated (or fallback logic applied earlier).
        # We will filter out empty seller_ids for this profile specific view, or group 'empty' as one.
        # Ideally we only aggregate known sellers.
        
        # Filter for valid seller_ids
        valid_sellers = merged[merged['seller_id'].notna() & (merged['seller_id'] != '')]
        
        grouped = valid_sellers.groupby('seller_id')
        
        for seller_id, group in grouped:
            total_calls = group['call_id'].nunique()
            unique_products = group['product_id'].nunique()
            unique_buyers = group['buyer_id'].nunique()
            
            # Dominant Product
            dominant_product = group['product_name'].mode()[0] if not group['product_name'].mode().empty else ''
            
            # Sentiment Map
            def map_sentiment(s):
                s = str(s).lower()
                if 'positive' in s: return 1
                if 'negative' in s: return -1
                return 0
            
            sent_scores = group['seller_sentiment'].apply(map_sentiment)
            avg_seller_sentiment_num = round(sent_scores.mean(), 2)
            
            # Pricing
            median_initial = group['initial_price'].median()
            median_final = group['final_price'].median()
            avg_discount = group['discount_percent'].mean()
            
            # Negotiation Rate
            negot_yes = (group['negotiation_flag'] == 'yes').sum()
            negotiation_rate = round((negot_yes / len(group)) * 100, 2)
            
            number_of_price_revisions_avg = round(group['number_of_price_revisions'].mean(), 2)
            price_variance = round(group['final_price'].var(), 2)
            seller_min_price = group['final_price'].min()
            seller_max_price = group['final_price'].max()
            
            # MOQ
            median_moq_val = group['moq_value'].apply(lambda x: clean_money(x)).median()
            median_moq_price = group['moq_price'].apply(lambda x: clean_money(x)).median()
            
            # Volume Mix Indicator (% bulk)
            # Check what 'requirement_volume_type' contains. 
            # Assuming 'wholesale', 'bulk' vs 'retail'.
            def is_bulk(v):
                v_str = str(v).lower()
                return 'wholesale' in v_str or 'bulk' in v_str
                
            bulk_count = group['requirement_volume_type'].apply(is_bulk).sum()
            volume_mix_indicator = round((bulk_count / len(group)) * 100, 2)
            
            # Seller Type
            # If > 50% bulk -> Wholesale, else Retail (or based on known types)
            if volume_mix_indicator > 50:
                seller_type = 'wholesale'
            elif volume_mix_indicator < 10 and unique_buyers > 5: # Arbitrary heuristic for retail?
                 seller_type = 'retail'
            else:
                 seller_type = 'mixed/unknown'
            
            row = {
                'seller_id': seller_id,
                'total_calls': total_calls,
                'unique_products': unique_products,
                'unique_buyers': unique_buyers,
                'seller_type': seller_type,
                'dominant_product': dominant_product,
                'avg_seller_sentiment_num': avg_seller_sentiment_num,
                'median_initial_price': median_initial,
                'median_final_price': median_final,
                'avg_discount_percent': round(avg_discount, 2),
                'negotiation_rate_percent': negotiation_rate,
                'number_of_price_revisions_avg': number_of_price_revisions_avg,
                'price_variance': price_variance,
                'seller_minimum_price': seller_min_price,
                'seller_maximum_price': seller_max_price,
                'median_moq_value': median_moq_val,
                'median_moq_price': median_moq_price,
                'volume_mix_indicator': volume_mix_indicator
            }
            aggregated_rows.append(row)
            
        pd.DataFrame(aggregated_rows).to_csv(OUTPUT_AGG, index=False)
        logger.info(f"Saved {OUTPUT_AGG}")
        
    except Exception as e:
        logger.error(f"Error generating agg profile: {e}")

def generate_call_level_insights(seller_file, buyer_file):
    logger.info("Generating Call Level Insights & Confusion Matrix...")
    OUTPUT_CALL_LEVEL = "call_level_insight.csv"
    OUTPUT_MATRIX = "buyer_seller_intent_confusion_matrix.csv"
    
    try:
        sdf = pd.read_csv(seller_file)
        bdf = pd.read_csv(buyer_file)
        
        # Ensure join keys are strings
        sdf['call_id'] = sdf['call_id'].astype(str).str.replace(',', '').str.strip()
        bdf['call_id'] = bdf['call_id'].astype(str).str.replace(',', '').str.strip()
        
        # Merge
        merged = sdf.merge(bdf, on='call_id', how='inner', suffixes=('_seller', '_buyer'))
        
        # --- Logic for Labels ---
        def get_buyer_intent(row):
            # 1. High: is_high_intent flag
            if row.get('is_high_intent', False):
                return 'High'
            # 2. Low: Everything else (Removing 'Medium')
            return 'Low'

        def get_seller_intent(row):
            sent = str(row.get('seller_sentiment', '')).lower()
            negot = str(row.get('negotiation_flag', '')).lower()
            
            # High Intent: Positive + Negotiates (Consultative)
            if 'positive' in sent and negot == 'yes':
                return 'High'
            # Low Intent: Transactional, Passive, Negative, or No Negotation
            else:
                return 'Low'

        merged['Buyer_Intent_Label'] = merged.apply(get_buyer_intent, axis=1)
        merged['Seller_Intent_Label'] = merged.apply(get_seller_intent, axis=1)
        
        # Select columns for output
        # Note: seller_id and buyer_id are unique to their files usually, so they won't have suffixes unless both files had both columns.
        # Based on inspection: seller_level has seller_id, buyer_level has buyer_id. No collision.
        
        final_df = merged.copy()
        
        # Resolve potentially specific columns if they collided
        # product_name collision -> product_name_seller, product_name_buyer
        if 'product_name_seller' in final_df.columns:
            final_df['product_name'] = final_df['product_name_seller']
        elif 'product_name' in final_df.columns:
             pass # No collision
             
        # Columns to keep
        keep_cols = [
            'call_id', 'buyer_id', 'seller_id', 
            'Buyer_Intent_Label', 'Seller_Intent_Label',
            'buyer_sentiment', 'seller_sentiment', 'is_high_intent', 'negotiation_flag',
            'product_name', 'final_price',
            'delivery_responsibility', 'seller_delivers_to_buyer_location'
        ]
        
        # Add any other useful columns
        # Filter only existing columns
        existing_cols = [c for c in keep_cols if c in final_df.columns]
        
        # Save
        final_df[existing_cols].to_csv(OUTPUT_CALL_LEVEL, index=False)
        logger.info(f"Saved {OUTPUT_CALL_LEVEL}")
        
        # --- Confusion Matrix ---
        confusion = pd.crosstab(final_df['Seller_Intent_Label'], final_df['Buyer_Intent_Label'])
        
        # Also percentages
        confusion_pct = pd.crosstab(final_df['Seller_Intent_Label'], final_df['Buyer_Intent_Label'], normalize='all') * 100
        confusion_pct = confusion_pct.round(2)
        
        # We can save separate or combined. User asked for "counts + normalized percentages". 
        # Making a combined readable format or just saving raw counts for Streamlit to handle?
        # Streamlit heatmap usually takes raw matrix.
        # Let's save the Raw Counts for plotting.
        confusion.to_csv(OUTPUT_MATRIX)
        logger.info(f"Saved {OUTPUT_MATRIX}")
        
    except Exception as e:
        logger.error(f"Error generating call level insights: {e}", exc_info=True)


def main():
    input_file = get_latest_input_file()
    id_map = load_raw_data_map()
    
    df = pd.read_csv(input_file)
    logger.info(f"Loaded {len(df)} rows from {input_file}")
    
    generate_seller_level(df, id_map)
    generate_buyer_level(df, id_map)
    generate_category_level_from_source(df, OUTPUT_SELLER)
    generate_aggregated_seller_level(OUTPUT_SELLER, OUTPUT_BUYER)
    
    # New Step
    generate_call_level_insights(OUTPUT_SELLER, OUTPUT_BUYER)
    
    logger.info("Done.")

if __name__ == "__main__":
    main()
