"""
AI Search Term Auditor

This script automates the verification of search term to product category mappings
using an LLM (OpenAI o4-mini). It processes CSV files containing search terms and their
mapped categories, then outputs an audited CSV with AI labels, confidence scores,
and reasoning.

Author: Vidyanand Sahu
Python Version: 3.10+
"""

import os
import sys
from typing import Optional, Dict
import pandas as pd
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError
import json
from datetime import datetime
from dotenv import load_dotenv
import urllib.parse
import requests

# Load environment variables from .env file
load_dotenv()


# ============================================================================
# Pydantic Models for Structured Output
# ============================================================================

class AuditResult(BaseModel):
    """
    Structured response model for LLM audit results.
    
    Attributes:
        label: Classification of the mapping (Relevant, Related, or Remove)
        reasoning: Detailed explanation for the classification
        confidence: Confidence score between 0.0 and 1.0
    """
    label: str = Field(
        ...,
        description="Must be one of: 'Relevant', 'Related', or 'Remove'"
    )
    reasoning: str = Field(
        ...,
        description="Detailed explanation for why this label was assigned"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0"
    )


# ============================================================================
# Configuration
# ============================================================================

class Config:
    """Configuration settings for the auditor."""
    
    # OpenAI API Configuration (supports OpenRouter)
    OPENAI_API_KEY = os.getenv("LLM_API_KEY", "your-api-key-here")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "google/gemini-2.5-flash")  # Using o4-mini model
    BASE_URL = os.getenv("BASE_URL", "https://imllm.intermesh.net/v1")  # OpenRouter base URL
    
    # File paths
    INPUT_CSV = "input_mappings.csv"
    OUTPUT_CSV = f"audited_mappings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # CSV column names
    COL_SEARCH_TERM = "search_term"
    COL_MAPPED_CATEGORY = "mapped_category"
    COL_AI_LABEL = "ai_label"
    COL_AI_CONFIDENCE = "ai_confidence"
    COL_AI_REASONING = "ai_reasoning"


# ============================================================================
# Search API Integration
# ============================================================================

# Search API Configuration
SEARCH_API_BASE_URL = "http://34.93.37.48:8983/tools/related_info?source=dir.search&debug=true&q={keyword}"


def call_search_api(keyword: str) -> Optional[Dict]:
    """
    Call the Search API to get category recommendations.
    
    Args:
        keyword: Search keyword
        
    Returns:
        API response as dictionary or None if error
    """
    kw_encoded = urllib.parse.quote(keyword, safe='')
    
    try:
        response = requests.get(
            SEARCH_API_BASE_URL.format(keyword=kw_encoded), 
            timeout=10
        )
        
        if not response.ok:
            print(f"   [WARN] Search API error: {response.status_code}")
            return None
        
        return response.json()
        
    except requests.exceptions.Timeout:
        print("   [WARN] Search API request timed out")
        return None
    except requests.exceptions.RequestException as e:
        print(f"   [WARN] Search API request failed: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        print(f"   [WARN] Failed to parse Search API JSON response: {str(e)}")
        return None
    except Exception as e:
        print(f"   [WARN] Unexpected Search API error: {str(e)}")
        return None


# ============================================================================
# Search Context Parser
# ============================================================================

def parse_search_context(api_response: Optional[Dict]) -> str:
    """
    Parse Search API response to extract contextual category hierarchy.
    
    This function extracts ONLY the essential category hierarchy information
    from the Search API response to provide context to the LLM without
    overwhelming it with raw JSON data.
    
    Args:
        api_response: Raw API response dictionary from call_search_api()
        
    Returns:
        Clean formatted hierarchy string or "No context available" on error
        
    Example Output:
        "Context: Testing & Measuring Equipments > Lab Instruments & Supplies > Material Testing Equipment > Dyne Test Pen"
    """
    if not api_response:
        return "No context available"
    
    try:
        # Extract the top recommended category from live_mcats
        live_mcats = api_response.get("guess", {}).get("live_mcats", [])
        
        if not live_mcats:
            return "No context available"
        
        # Get the first (highest ranked) category
        top_mcat = live_mcats[0]
        
        # Extract hierarchy components
        mcat_name = top_mcat.get("name", "")
        breadcrumb = top_mcat.get("breadcrumb", {})
        
        if not breadcrumb:
            # Fallback to just the mcat name if no breadcrumb
            return f"Context: {mcat_name}" if mcat_name else "No context available"
        
        # Build hierarchy: catname > groupname > pmcatname > name
        hierarchy_parts = []
        
        catname = breadcrumb.get("catname")
        if catname:
            hierarchy_parts.append(catname)
        
        groupname = breadcrumb.get("groupname")
        if groupname:
            hierarchy_parts.append(groupname)
        
        pmcatname = breadcrumb.get("pmcatname")
        if pmcatname:
            hierarchy_parts.append(pmcatname)
        
        if mcat_name:
            hierarchy_parts.append(mcat_name)
        
        if hierarchy_parts:
            hierarchy_string = " > ".join(hierarchy_parts)
            return f"Context: {hierarchy_string}"
        else:
            return "No context available"
            
    except Exception as e:
        print(f"[WARN] Error parsing search context: {e}")
        return "No context available"


# ============================================================================
# LLM Prompt Template
# ============================================================================

AUDIT_PROMPT_TEMPLATE = """You are an expert e-commerce product categorization auditor. Your task is to evaluate whether a user's search term is correctly mapped to a product category.

**LABELING RULES:**

1. **Label: "Relevant"**
   - The search term is a synonym, exact match, or specific brand/model of the category
   - Examples:
     * "iPhone 14" -> "Mobile Phones" (Relevant)
     * "Paracetamol" -> "Acetaminophen" (Relevant - generic vs brand name)
     * "Crocs" -> "Crocs Slippers" (Relevant)

2. **Label: "Related"**
   - The search term is a necessary accessory or complementary product
   - Examples:
     * "Phone Case" -> "Mobile Phones" (Related - accessory)
     * "Laptop Charger" -> "Laptops" (Related - accessory)

3. **Label: "Remove"**
   - The items are completely unrelated
   - Examples:
     * "Crocs Making Machine" -> "Crocs Slippers" (Remove - machine vs product)
     * "Cup making machine" -> "Paper Cup" (Remove - machine vs product)
     * "Cotton" -> "T-Shirt" (Remove - raw material vs finished good)
     * "Dog Food" -> "Mobile Phones" (Remove - completely unrelated)

**ADDITIONAL CONTEXT FROM SEARCH ENGINE:**
{search_engine_context}

Use this context to understand what the search term actually refers to in our catalog.
The search engine has analyzed this term and recommended the above category hierarchy.
However, prioritize your logical reasoning rules for the final decision.

**YOUR TASK:**
Analyze the following mapping and provide your assessment:

Search Term: "{search_term}"
Mapped Category: "{mapped_category}"

Respond ONLY with valid JSON in this exact format (no markdown, no code blocks):
{{
    "label": "Relevant",
    "reasoning": "Detailed explanation for your decision",
    "confidence": 0.95
}}

Be thorough in your reasoning and consider edge cases like:
- Pharmaceutical drugs (generic vs brand names)
- Manufacturing equipment vs finished products
- Raw materials vs finished goods
- Accessories vs main products
"""


# ============================================================================
# Core Auditor Class
# ============================================================================

class SearchTermAuditor:
    """
    Main class for auditing search term to category mappings using LLM.
    """
    
    def __init__(self, api_key: str, model: str = Config.OPENAI_MODEL, base_url: str = Config.BASE_URL):
        """
        Initialize the auditor with OpenAI client.
        
        Args:
            api_key: OpenAI/OpenRouter API key
            model: Model to use (default: openai/o4-mini)
            base_url: API base URL (default: OpenRouter)
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model
        self.audit_count = 0
        self.error_count = 0
    
    def audit_mapping(self, search_term: str, mapped_category: str, custom_prompt: Optional[str] = None) -> Optional[AuditResult]:
        """
        Audit a single search term to category mapping using LLM.
        
        Args:
            search_term: The user's search query
            mapped_category: The category it's mapped to
            custom_prompt: Optional custom prompt template to override default
            
        Returns:
            AuditResult object or None if error occurred
        """
        try:
            # Call Search API to get contextual information
            print(f"   [API] Calling Search API...")
            api_response = call_search_api(search_term)
            search_context = parse_search_context(api_response)
            print(f"   [API] {search_context}")
            
            # Use custom prompt if provided, otherwise use default
            prompt_template = custom_prompt if custom_prompt else AUDIT_PROMPT_TEMPLATE
            
            # Log which prompt is being used
            if custom_prompt:
                print(f"   [PROMPT] Using custom system prompt")
            
            # Construct the prompt with search context
            prompt = prompt_template.format(
                search_term=search_term,
                mapped_category=mapped_category,
                search_engine_context=search_context
            )
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an expert e-commerce product categorization auditor. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                # temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            response_text = response.choices[0].message.content
            response_data = json.loads(response_text)
            
            # Validate using Pydantic
            audit_result = AuditResult(**response_data)
            
            self.audit_count += 1
            return audit_result
            
        except ValidationError as e:
            print(f"[WARN] Validation error for '{search_term}': {e}")
            self.error_count += 1
            return None
            
        except json.JSONDecodeError as e:
            print(f"[WARN] JSON parsing error for '{search_term}': {e}")
            self.error_count += 1
            return None
            
        except Exception as e:
            print(f"[WARN] Unexpected error for '{search_term}': {e}")
            self.error_count += 1
            return None
    
    def process_csv(self, input_path: str, output_path: str) -> None:
        """
        Process an entire CSV file of mappings.
        
        Args:
            input_path: Path to input CSV file
            output_path: Path to output CSV file
        """
        print(f"[*] Loading input CSV: {input_path}")
        
        try:
            # Load the CSV with automatic encoding detection
            # Try UTF-8 first, then fall back to other common encodings
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
            required_cols = [Config.COL_SEARCH_TERM, Config.COL_MAPPED_CATEGORY]
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
            
            print(f"[OK] Loaded {len(df)} rows")
            print(f"[AI] Starting AI audit using model: {self.model_name}\n")
            
            # Initialize result columns
            df[Config.COL_AI_LABEL] = None
            df[Config.COL_AI_CONFIDENCE] = None
            df[Config.COL_AI_REASONING] = None
            
            # Process each row
            for idx, row in df.iterrows():
                search_term = str(row[Config.COL_SEARCH_TERM])
                mapped_category = str(row[Config.COL_MAPPED_CATEGORY])
                
                print(f"[{idx + 1}/{len(df)}] Auditing: '{search_term}' -> '{mapped_category}'")
                
                # Audit the mapping
                result = self.audit_mapping(search_term, mapped_category)
                
                if result:
                    df.at[idx, Config.COL_AI_LABEL] = result.label
                    df.at[idx, Config.COL_AI_CONFIDENCE] = result.confidence
                    df.at[idx, Config.COL_AI_REASONING] = result.reasoning
                    print(f"   [+] Label: {result.label} (Confidence: {result.confidence:.2f})")
                else:
                    df.at[idx, Config.COL_AI_LABEL] = "ERROR"
                    df.at[idx, Config.COL_AI_CONFIDENCE] = 0.0
                    df.at[idx, Config.COL_AI_REASONING] = "Failed to process"
                    print(f"   [X] Error occurred")
                
                print()  # Blank line for readability
            
            # Save the results
            df.to_csv(output_path, index=False)
            print(f"[SAVE] Results saved to: {output_path}")
            print(f"\n[SUMMARY]")
            print(f"   Total rows: {len(df)}")
            print(f"   Successfully audited: {self.audit_count}")
            print(f"   Errors: {self.error_count}")
            
            # Print label distribution
            if self.audit_count > 0:
                print(f"\n[STATS] Label Distribution:")
                label_counts = df[Config.COL_AI_LABEL].value_counts()
                for label, count in label_counts.items():
                    percentage = (count / len(df)) * 100
                    print(f"   {label}: {count} ({percentage:.1f}%)")
            
        except FileNotFoundError:
            print(f"[ERROR] Input file '{input_path}' not found")
            sys.exit(1)
            
        except ValueError as e:
            print(f"[ERROR] {e}")
            sys.exit(1)
            
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            sys.exit(1)


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Main entry point for the script."""
    
    print("=" * 70)
    print("AI Search Term Auditor (OpenAI o4-mini)".center(70))
    print("=" * 70)
    print()
    
    # Check for API key
    if Config.OPENAI_API_KEY == "your-api-key-here":
        print("[WARNING] Using placeholder API key!")
        print("          Please set the OPENAI_API_KEY environment variable or")
        print("          update the Config.OPENAI_API_KEY in the script.\n")
    
    # Initialize the auditor
    auditor = SearchTermAuditor(
        api_key=Config.OPENAI_API_KEY,
        model=Config.OPENAI_MODEL,
        base_url=Config.BASE_URL
    )
    
    # Process the CSV
    auditor.process_csv(
        input_path=Config.INPUT_CSV,
        output_path=Config.OUTPUT_CSV
    )
    
    print("\n" + "=" * 70)
    print("Audit Complete!".center(70))
    print("=" * 70)


if __name__ == "__main__":
    main()
