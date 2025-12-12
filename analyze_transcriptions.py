"""
Transcription Analysis Script

This script processes call transcriptions using an LLM to extract structured insights
about B2B buyer-seller conversations. It reads transcriptions from a CSV file,
applies a detailed prompt template, and outputs structured JSON results.

Author: Based on test.py structure
Python Version: 3.10+
"""

import os
import sys
from typing import Optional
import pandas as pd
from openai import OpenAI
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# ============================================================================
# Configuration
# ============================================================================

class Config:
    """Configuration settings for the transcription analyzer."""
    
    # OpenAI API Configuration (supports OpenRouter)
    OPENAI_API_KEY = os.getenv("LLM_API_KEY", "your-api-key-here")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "openai/gpt-5-mini")
    BASE_URL = os.getenv("BASE_URL", "https://imllm.intermesh.net/v1")
    
    # File paths
    INPUT_CSV = "Input.csv"
    OUTPUT_CSV = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    PROMPT_FILE = "prompt.txt"
    
    # CSV column names
    COL_RECEIVER_ID = "Reciever Seller ID"
    COL_CALL_ID = "call_id"
    COL_TRANSCRIPTION = "call_transcription"
    COL_ANALYSIS = "analysis_json"
    COL_STATUS = "status"
    COL_ERROR = "error_message"


# ============================================================================
# Core Analyzer Class
# ============================================================================

class TranscriptionAnalyzer:
    """
    Main class for analyzing call transcriptions using LLM.
    """
    
    def __init__(self, api_key: str, model: str = Config.OPENAI_MODEL, base_url: str = Config.BASE_URL):
        """
        Initialize the analyzer with OpenAI client.
        
        Args:
            api_key: OpenAI/OpenRouter API key
            model: Model to use
            base_url: API base URL
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model
        self.analysis_count = 0
        self.error_count = 0
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """
        Load the prompt template from prompt.txt file.
        
        Returns:
            Prompt template as string
        """
        try:
            with open(Config.PROMPT_FILE, 'r', encoding='utf-8') as f:
                prompt = f.read()
            print(f"[OK] Loaded prompt template from {Config.PROMPT_FILE}")
            return prompt
        except FileNotFoundError:
            print(f"[ERROR] Prompt file '{Config.PROMPT_FILE}' not found")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Failed to load prompt template: {e}")
            sys.exit(1)
    
    def analyze_transcription(self, transcription: str) -> Optional[dict]:
        """
        Analyze a single call transcription using LLM.
        
        Args:
            transcription: The call transcription text
            
        Returns:
            Parsed JSON response as dictionary or None if error occurred
        """
        try:
            # Construct the full prompt
            full_prompt = f"{self.prompt_template}\n\n# TRANSCRIPTION TO ANALYZE:\n\n{transcription}"
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert B2B call analyzer. Extract structured insights. CRITICAL: You must extract EVERY price mentioned (market price, initial quote, final quote, etc.) as a separate entry in 'prices_discussed'. Do not summarize. Respond ONLY with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ],
                #temperature=0.1,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            response_text = response.choices[0].message.content
            response_data = json.loads(response_text)
            
            # Debug logging
            products = response_data.get("products_discussed", [])
            for p in products:
                prices = p.get("prices_discussed", {}).get("price_entries", [])
                print(f"   [DEBUG] Found {len(prices)} price entries for product {p.get('product_id')}")

            self.analysis_count += 1
            return response_data
            
        except json.JSONDecodeError as e:
            print(f"   [WARN] JSON parsing error: {e}")
            self.error_count += 1
            return None
            
        except Exception as e:
            print(f"   [WARN] Unexpected error: {e}")
            self.error_count += 1
            return None
    
    def _extract_product_data(self, analysis_json: dict, seller_id: str, call_id: str) -> list:
        """
        Extract detailed product data, creating multiple rows for different price entries.
        
        Args:
            analysis_json: Parsed JSON from LLM analysis
            seller_id: Seller/Receiver ID
            call_id: Call ID
            
        Returns:
            List of dictionaries, one per price entry per product
        """
        rows = []
        
        try:
            # Extract Global Insights & Call-Level Attributes
            buyer_profile = analysis_json.get("buyer_profile", {})
            call_insights = analysis_json.get("call_insights", {})
            buyer_req = analysis_json.get("buyer_requirement_classification", {})

            # Mapped Global Fields
            buyer_type = buyer_profile.get("buyer_type", "")
            business_category = buyer_profile.get("business_category", "")
            intent_for_purchase = buyer_profile.get("intent_for_purchase", "")
            
            buyer_sentiment = call_insights.get("buyer_sentiment", {}).get("value", "")
            seller_sentiment = call_insights.get("seller_sentiment", {}).get("value", "")
            
            req_type = buyer_req.get("requirement_type", "")
            req_vol_type = buyer_req.get("requirement_volume_type", "")
            
            # Products
            products_discussed = analysis_json.get("products_discussed", [])
            
            for product in products_discussed:
                # Common Product Data
                product_id = product.get("product_id", "")
                product_name = product.get("product_name", "")
                product_kw = product.get("product_kw", "")
                
                # Variant Attributes (from specifications)
                specs = product.get("specifications", {})
                spec_attributes = specs.get("attributes", [])
                
                # Convert to JSON string
                attr_dict = {attr.get('name'): attr.get('value') for attr in spec_attributes if attr.get('name') and attr.get('value')}
                variant_attributes = json.dumps(attr_dict)
                
                # Quantity Required
                qty_data = product.get("quantity_required", {})
                qty_val = qty_data.get("value", "")
                qty_unit = qty_data.get("unit", "")
                
                # Global MOQ for product
                global_moq = product.get("moq", {})
                moq_val = global_moq.get("value", "")
                moq_unit = global_moq.get("unit", "")
                moq_price = global_moq.get("price", "")
                moq_curr = global_moq.get("currency", "")
                
                # Final Price
                final_price = product.get("final_quoted_seller_price")
                final_quoted_price = str(final_price) if final_price is not None else ""
                
                # Delivery Terms
                delivery = product.get("delivery_terms", {})
                del_resp = delivery.get("responsibility", "")
                seller_delivers = delivery.get("seller_delivers_to_buyer_location", "")
                del_loc = delivery.get("delivery_location", "")
                
                # New Field: Seller Deals in Product
                is_seller_deals = product.get("seller_deals_in_product", {}).get("value", "")

                # Prices
                prices = product.get("prices_discussed", {})
                price_entries = prices.get("price_entries", [])
                
                if not price_entries:
                    # Create one row with empty price details
                    rows.append({
                        "call_id": call_id,
                        "product_id": product_id,
                        "product_name": product_name,
                        "product_kw": product_kw,
                        "variant_attributes": variant_attributes,
                        "quantity_required_value": qty_val,
                        "quantity_required_unit": qty_unit,
                        "moq_value": moq_val,
                        "moq_unit": moq_unit,
                        "moq_price": moq_price,
                        "moq_currency": moq_curr,
                        "price_value": "",
                        "price_currency": "",
                        "price_type": "",
                        "applies_to_quantity_min": "",
                        "applies_to_quantity_max": "",
                        "applies_to_quantity_unit": "",
                        "applies_to_specifications": "",
                        "unit_price": "",
                        "other_conditions_basis": "",
                        "other_conditions_payment_terms": "",
                        "other_conditions_notes": "",
                        "moq_applies_value": "",
                        "moq_applies_unit": "",
                        "final_quoted_seller_price": final_quoted_price,
                        "delivery_responsibility": del_resp,
                        "seller_delivers_to_buyer_location": seller_delivers,
                        "delivery_location": del_loc,
                        # NEW FIELDS
                        "Buyer Requirement Type": req_type,
                        "requirement_volume_type": req_vol_type,
                        "Is_Seller_deals_in_product ": is_seller_deals,
                        "Buyer Sentiment": buyer_sentiment,
                        "Seller Sentiment": seller_sentiment,
                        "Buyer Type": buyer_type,
                        "Business Category": business_category,
                        "Intent for purchase": intent_for_purchase
                    })
                else:
                    # Create a row for EACH price entry
                    for entry in price_entries:
                        # Price specific fields
                        p_val = entry.get("price_value", "")
                        p_curr = entry.get("currency", "")
                        p_type = entry.get("price_type", "")
                        p_unit_price = entry.get("unit_price", "")
                        
                        # Quantity range
                        qty_range = entry.get("applies_to_quantity", {})
                        p_min = qty_range.get("min_quantity", "")
                        p_max = qty_range.get("max_quantity", "")
                        p_unit = qty_range.get("unit", "")
                        
                        # Specs specific to this price
                        p_specs = entry.get("applies_to_specifications", {})
                        rel_attrs = p_specs.get("related_spec_attributes", [])
                        p_spec_str = "; ".join([f"{attr.get('name')}: {attr.get('value')}" for attr in rel_attrs])
                        
                        # MOQ specific to this price
                        p_moq = entry.get("moq_applies", {})
                        p_moq_val = p_moq.get("value", "")
                        p_moq_unit = p_moq.get("unit", "")
                        
                        # Conditions
                        conds = entry.get("other_conditions", {})
                        c_basis = conds.get("basis", "")
                        c_pay = conds.get("payment_terms", "")
                        c_note = conds.get("additional_condition_notes", "")
                        
                        rows.append({
                            "call_id": call_id,
                            "product_id": product_id,
                            "product_name": product_name,
                            "product_kw": product_kw,
                            "variant_attributes": variant_attributes,
                            "quantity_required_value": qty_val,
                            "quantity_required_unit": qty_unit,
                            "moq_value": moq_val,
                            "moq_unit": moq_unit,
                            "moq_price": moq_price,
                            "moq_currency": moq_curr,
                            "price_value": p_val,
                            "price_currency": p_curr,
                            "price_type": p_type,
                            "applies_to_quantity_min": p_min,
                            "applies_to_quantity_max": p_max,
                            "applies_to_quantity_unit": p_unit,
                            "applies_to_specifications": p_spec_str,
                            "unit_price": p_unit_price,
                            "other_conditions_basis": c_basis,
                            "other_conditions_payment_terms": c_pay,
                            "other_conditions_notes": c_note,
                            "moq_applies_value": p_moq_val,
                            "moq_applies_unit": p_moq_unit,
                            "final_quoted_seller_price": final_quoted_price,
                            "delivery_responsibility": del_resp,
                            "seller_delivers_to_buyer_location": seller_delivers,
                            "delivery_location": del_loc,
                            # NEW FIELDS
                            "Buyer Requirement Type": req_type,
                            "requirement_volume_type": req_vol_type,
                            "Is_Seller_deals_in_product ": is_seller_deals,
                            "Buyer Sentiment": buyer_sentiment,
                            "Seller Sentiment": seller_sentiment,
                            "Buyer Type": buyer_type,
                            "Business Category": business_category,
                            "Intent for purchase": intent_for_purchase
                        })
                        
        except Exception as e:
            print(f"   [WARN] Error extracting granular product data: {e}")
            # Return basic empty row on error
            rows.append({"call_id": call_id})
        
        return rows
    
    def process_csv(self, input_path: str, output_path: str) -> None:
        """
        Process an entire CSV file of transcriptions.
        
        Args:
            input_path: Path to input CSV file
            output_path: Path to output CSV file
        """
        print(f"[*] Loading input CSV: {input_path}")
        
        try:
            # Load the CSV with automatic encoding detection
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(input_path, encoding=encoding)
                    print(f"[OK] Successfully loaded CSV with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise ValueError(f"Could not read CSV file with any supported encoding. Please save the file as UTF-8.")
            
            # Validate required columns
            required_cols = [Config.COL_RECEIVER_ID, Config.COL_CALL_ID, Config.COL_TRANSCRIPTION]
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
            
            print(f"[OK] Loaded {len(df)} rows")
            print(f"[AI] Starting AI analysis using model: {self.model_name}\n")
            
            # List to store all product rows
            all_products = []
            
            # Process each row
            for idx, row in df.iterrows():
                receiver_id = str(row[Config.COL_RECEIVER_ID])
                call_id = str(row[Config.COL_CALL_ID])
                transcription = str(row[Config.COL_TRANSCRIPTION])
                
                print(f"[{idx + 1}/{len(df)}] Analyzing Call ID: {call_id} (Receiver: {receiver_id})")
                
                # Analyze the transcription
                result = self.analyze_transcription(transcription)
                
                if result:
                    print(f"   [+] Analysis completed successfully")
                    # Extract product data and add to list
                    product_rows = self._extract_product_data(result, receiver_id, call_id)
                    all_products.extend(product_rows)
                    print(f"   [+] Extracted {len(product_rows)} product(s)")
                else:
                    print(f"   [X] Error occurred - adding empty row")
                    # Add empty row on error
                    all_products.append({
                        "Seller_ID": receiver_id,
                        "Call_ID": call_id,
                        "Product_ID": "",
                        "Product_name": "",
                        "Product_keyword": "",
                        "Product_price": "",
                        "Is_Seller_deals_in_product": "",
                        "Specification": ""
                    })
                
                print()  # Blank line for readability
            
            # Create output DataFrame
            output_df = pd.DataFrame(all_products)
            
            # Save the results
            output_df.to_csv(output_path, index=False, encoding='utf-8')
            print(f"[SAVE] Results saved to: {output_path}")
            print(f"\n[SUMMARY]")
            print(f"   Total calls processed: {len(df)}")
            print(f"   Total product rows generated: {len(output_df)}")
            print(f"   Successfully analyzed: {self.analysis_count}")
            print(f"   Errors: {self.error_count}")
            
        except FileNotFoundError:
            print(f"[ERROR] Input file '{input_path}' not found")
            sys.exit(1)
            
        except ValueError as e:
            print(f"[ERROR] {e}")
            sys.exit(1)
            
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Main entry point for the script."""
    
    print("=" * 70)
    print("B2B Call Transcription Analyzer".center(70))
    print("=" * 70)
    print()
    
    # Check for API key
    if Config.OPENAI_API_KEY == "your-api-key-here":
        print("[WARNING] Using placeholder API key!")
        print("          Please set the LLM_API_KEY environment variable in .env file.\n")
        sys.exit(1)
    
    # Initialize the analyzer
    analyzer = TranscriptionAnalyzer(
        api_key=Config.OPENAI_API_KEY,
        model=Config.OPENAI_MODEL,
        base_url=Config.BASE_URL
    )
    
    # Process the CSV
    analyzer.process_csv(
        input_path=Config.INPUT_CSV,
        output_path=Config.OUTPUT_CSV
    )
    
    print("\n" + "=" * 70)
    print("Analysis Complete!".center(70))
    print("=" * 70)


if __name__ == "__main__":
    main()
