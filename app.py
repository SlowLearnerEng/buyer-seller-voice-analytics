# -*- coding: utf-8 -*-
"""
Streamlit UI for Buyer-Seller Voice Analytics
Audio Transcription Interface
"""

import streamlit as st
import json
import logging
import os
import csv
import pandas as pd
from datetime import datetime
from bulk import transcribe_audio

# Configure logging for Streamlit app
os.makedirs("logs", exist_ok=True)
log_filename = os.path.join("logs", f"streamlit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Streamlit app started. Log file: {log_filename}")

# Page configuration
st.set_page_config(
    page_title="Audio Transcription Tool",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border-left: 4px solid #17a2b8;
        margin: 1rem 0;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        margin: 1rem 0;
    }
    .stTextArea textarea {
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🎙️ Audio Transcription Tool</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Transcribe buyer-seller call recordings with AI-powered speech recognition</div>', unsafe_allow_html=True)

# Create tabs for single and batch processing
tab1, tab2 = st.tabs(["📎 Single URL", "📊 Batch Processing (CSV)"])

# Sidebar for additional options
with st.sidebar:
    st.header("⚙️ Configuration")
    
    st.markdown("### Optional Fields")
    caller_id = st.text_input(
        "Caller ID",
        value="unknown",
        help="Identifier for the caller (optional)"
    )
    
    receiver_id = st.text_input(
        "Receiver ID",
        value="unknown",
        help="Identifier for the receiver (optional)"
    )
    
    st.markdown("---")
    st.markdown("### About")
    st.info(
        "This tool transcribes audio recordings from URLs using the "
        "Intermesh transcription API. Supports direct audio URLs and "
        "Knowlarity player pages."
    )
    
    st.markdown("### Supported URL Formats")
    st.markdown("""
    - Direct audio file URLs (`.mp3`, `.wav`, etc.)
    - Knowlarity player pages (`playsound.html?soundurl=...`)
    """)

# ============================================================================
# TAB 1: Single URL Transcription
# ============================================================================
with tab1:
    st.markdown("### 📎 Audio Recording URL")

    # URL input
    audio_url = st.text_input(
        "Paste the URL to your audio recording",
        placeholder="https://example.com/recording.mp3",
        help="Enter the full URL to the audio file you want to transcribe",
        label_visibility="collapsed",
        key="single_url"
    )

    # Transcribe button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        transcribe_button = st.button(
            "🚀 Transcribe Audio",
            type="primary",
            use_container_width=True,
            key="single_transcribe"
        )

    # Handle transcription
    if transcribe_button:
        logger.info(f"Transcribe button clicked. URL: {audio_url}")
        if not audio_url or not audio_url.strip():
            logger.warning("Empty URL submitted")
            st.markdown('<div class="error-box">❌ <strong>Error:</strong> Please enter a valid URL</div>', unsafe_allow_html=True)
        else:
            # Remove all whitespace from URL
            clean_url = ''.join(audio_url.split())
            logger.info(f"URL after sanitization: {clean_url}")
            
            # Show loading spinner
            logger.info(f"Starting transcription for caller_id={caller_id}, receiver_id={receiver_id}")
            with st.spinner("🔄 Transcribing audio... This may take a moment."):
                # Call the transcription function
                result = transcribe_audio(
                    url=clean_url,
                    caller_id=caller_id,
                    receiver_id=receiver_id
                )
            
            logger.info(f"Transcription result: success={result['success']}")
            
            # Display results
            if result["success"]:
                st.markdown('<div class="success-box">✅ <strong>Transcription completed successfully!</strong></div>', unsafe_allow_html=True)
                
                # Extract data
                data = result["data"]
                
                # Display transcript in a nice format
                st.markdown("### 📝 Transcript")
                st.text_area(
                    "Transcription Text",
                    value=data["transcription"],
                    height=300,
                    label_visibility="collapsed",
                    key="single_transcript"
                )
                
                # Metadata
                st.markdown("### 📊 Metadata")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Media ID:** `{data['media_id']}`")
                    st.markdown(f"**Caller ID:** `{data['caller_id']}`")
                    st.markdown(f"**Receiver ID:** `{data['receiver_id']}`")
                
                with col2:
                    st.markdown(f"**Original URL:** [{data['raw_url'][:50]}...]({data['raw_url']})")
                    if data['normalized_url'] != data['raw_url']:
                        st.markdown(f"**Normalized URL:** [{data['normalized_url'][:50]}...]({data['normalized_url']})")
                    st.markdown(f"**Transcription URL:** [{data['transcription_url'][:50]}...]({data['transcription_url']})")
                
                # Raw JSON response (collapsible)
                with st.expander("🔍 View Raw API Response (JSON)"):
                    st.json(data)
                
                # Download button for transcript
                st.download_button(
                    label="💾 Download Transcript",
                    data=data["transcription"],
                    file_name=f"transcript_{data['media_id']}.txt",
                    mime="text/plain",
                    key="single_download"
                )
            
            else:
                # Error occurred
                st.markdown(f'<div class="error-box">❌ <strong>Transcription Failed</strong><br>{result["error"]}</div>', unsafe_allow_html=True)
                
                # Show troubleshooting tips
                with st.expander("💡 Troubleshooting Tips"):
                    st.markdown("""
                    **Common issues:**
                    - **Invalid URL**: Make sure the URL is accessible and points to an audio file
                    - **Network Error**: Check your internet connection
                    - **API Error**: The transcription service may be temporarily unavailable
                    - **File Format**: Ensure the audio file is in a supported format (MP3, WAV, etc.)
                    
                    **What to try:**
                    1. Verify the URL is correct and accessible
                    2. Try a different audio file
                    3. Check if the file format is supported
                    4. Wait a moment and try again
                    """)

# ============================================================================
# TAB 2: CSV Batch Processing
# ============================================================================
with tab2:
    st.markdown("### 📊 Batch Transcription from CSV")
    
    st.markdown('<div class="info-box">📋 <strong>CSV Format Required:</strong><br>• <strong>Required columns:</strong> <code>caller_id</code>, <code>receiver_id</code><br>• <strong>URL column:</strong> <code>pns_call_recording_url</code> OR <code>Signed_URL</code><br>• <strong>ID column (optional):</strong> <code>pns_call_record_id</code> (will generate from caller-receiver if missing)</div>', unsafe_allow_html=True)
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Upload CSV file",
        type=['csv'],
        help="Upload a CSV file with call recording information",
        key="csv_upload"
    )
    
    if uploaded_file is not None:
        try:
            # Read CSV
            df = pd.read_csv(uploaded_file)
            logger.info(f"CSV uploaded: {len(df)} rows")
            
            # Flexible column validation
            # Required: caller_id, receiver_id
            # URL column can be: pns_call_recording_url OR Signed_URL
            # ID column can be: pns_call_record_id (optional, will generate if missing)
            
            required_columns = ['caller_id', 'receiver_id']
            missing_required = [col for col in required_columns if col not in df.columns]
            
            if missing_required:
                st.markdown(f'<div class="error-box">❌ <strong>Missing Required Columns:</strong> {", ".join(missing_required)}</div>', unsafe_allow_html=True)
            else:
                # Detect URL column
                url_column = None
                if 'pns_call_recording_url' in df.columns:
                    url_column = 'pns_call_recording_url'
                elif 'Signed_URL' in df.columns:
                    url_column = 'Signed_URL'
                else:
                    st.markdown('<div class="error-box">❌ <strong>Missing URL Column:</strong> CSV must have either <code>pns_call_recording_url</code> or <code>Signed_URL</code> column</div>', unsafe_allow_html=True)
                    url_column = None
                
                if url_column:
                    # Check if pns_call_record_id exists, if not we'll generate it
                    has_record_id = 'pns_call_record_id' in df.columns
                    
                    if not has_record_id:
                        st.markdown('<div class="info-box">ℹ️ <strong>Note:</strong> No <code>pns_call_record_id</code> column found. Will use <code>caller_id-receiver_id</code> combination as ID.</div>', unsafe_allow_html=True)
                    
                    # Show preview
                    st.markdown("#### 📋 CSV Preview")
                    st.dataframe(df.head(10), use_container_width=True)
                    
                    st.markdown(f"**Total Records:** {len(df)}")
                    st.markdown(f"**URL Column:** `{url_column}`")
                    st.markdown(f"**ID Strategy:** {'Using pns_call_record_id' if has_record_id else 'Generating from caller_id-receiver_id'}")
                    
                    # Process button
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        process_button = st.button(
                            f"🚀 Process {len(df)} Recordings",
                            type="primary",
                            use_container_width=True,
                            key="batch_process"
                        )
                    
                    if process_button:
                        logger.info(f"Starting batch processing of {len(df)} recordings")
                        
                        # Initialize results dictionary
                        results = {}
                        
                        # Progress tracking
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        success_count = 0
                        error_count = 0
                        
                        # Process each row
                        for idx, row in df.iterrows():
                            # Get caller and receiver IDs
                            caller = str(row['caller_id']).strip()
                            receiver = str(row['receiver_id']).strip()
                            
                            # Generate or get record ID
                            if has_record_id:
                                pns_id = str(row['pns_call_record_id']).strip()
                            else:
                                # Generate ID from caller-receiver combination
                                pns_id = f"{caller}-{receiver}"
                            
                            # Get URL
                            url = str(row[url_column])
                            
                            # Remove all whitespace from URL (spaces, tabs, newlines)
                            url = ''.join(url.split())
                            
                            status_text.text(f"Processing {idx + 1}/{len(df)}: ID {pns_id}")
                            logger.info(f"Processing record {pns_id}, URL: {url}")
                            
                            # Transcribe (MOVED INSIDE THE LOOP)
                            result = transcribe_audio(
                                url=url,
                                caller_id=caller,
                                receiver_id=receiver
                            )
                            
                            # Build result entry
                            if result["success"]:
                                results[pns_id] = {
                                    "caller_id": caller,
                                    "receiver_id": receiver,
                                    "transcription": result["data"]["transcription"],
                                    "media_id": result["data"]["media_id"],
                                    "transcription_url": result["data"]["transcription_url"],
                                    "status": "success"
                                }
                                success_count += 1
                            else:
                                results[pns_id] = {
                                    "caller_id": caller,
                                    "receiver_id": receiver,
                                    "error": result["error"],
                                    "status": "failed"
                                }
                                error_count += 1
                            
                            # Update progress
                            progress_bar.progress((idx + 1) / len(df))
                            
                            # Add 3-second delay between calls to avoid rate limiting
                            if idx < len(df) - 1:  # Don't delay after the last one
                                import time
                                time.sleep(3)
                        
                        # Clear status (AFTER THE LOOP)
                        status_text.empty()
                        progress_bar.empty()
                        
                        # Show summary
                        st.markdown(f'<div class="success-box">✅ <strong>Batch Processing Complete!</strong><br>Success: {success_count} | Failed: {error_count}</div>', unsafe_allow_html=True)
                        
                        # Display results
                        st.markdown("### 📄 Results")
                        
                        # Convert to JSON string
                        json_output = json.dumps(results, indent=2, ensure_ascii=False)
                        
                        # Show JSON preview
                        with st.expander("🔍 View JSON Output", expanded=True):
                            st.json(results)
                        
                        # Download buttons
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.download_button(
                                label="💾 Download JSON",
                                data=json_output,
                                file_name=f"transcriptions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                mime="application/json",
                                key="download_json"
                            )
                        
                        with col2:
                            # Create CSV output
                            output_rows = []
                            for pns_id, data in results.items():
                                output_rows.append({
                                    'pns_call_record_id': pns_id,
                                    'caller_id': data.get('caller_id'),
                                    'receiver_id': data.get('receiver_id'),
                                    'transcription': data.get('transcription', ''),
                                    'media_id': data.get('media_id', ''),
                                    'status': data.get('status'),
                                    'error': data.get('error', '')
                                })
                            
                            output_df = pd.DataFrame(output_rows)
                            csv_output = output_df.to_csv(index=False)
                            
                            st.download_button(
                                label="📊 Download CSV",
                                data=csv_output,
                                file_name=f"transcriptions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                                key="download_csv"
                            )
                        
                        logger.info(f"Batch processing complete: {success_count} success, {error_count} failed")
        
        except Exception as e:
            logger.error(f"Error processing CSV: {e}", exc_info=True)
            st.markdown(f'<div class="error-box">❌ <strong>Error:</strong> {str(e)}</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #666; font-size: 0.9rem;">'
    'Powered by Intermesh Transcription API | Built with Streamlit'
    '</div>',
    unsafe_allow_html=True
)
