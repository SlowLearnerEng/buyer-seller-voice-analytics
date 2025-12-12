# -*- coding: utf-8 -*-
"""
Streamlit UI for Buyer-Seller Voice Analytics
Audio Transcription Interface
"""

import streamlit as st
import json
import logging
import os
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
    .stTextArea textarea {
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🎙️ Audio Transcription Tool</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Transcribe buyer-seller call recordings with AI-powered speech recognition</div>', unsafe_allow_html=True)

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

# Main content area
st.markdown("### 📎 Audio Recording URL")

# URL input
audio_url = st.text_input(
    "Paste the URL to your audio recording",
    placeholder="https://example.com/recording.mp3",
    help="Enter the full URL to the audio file you want to transcribe",
    label_visibility="collapsed"
)

# Transcribe button
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    transcribe_button = st.button(
        "🚀 Transcribe Audio",
        type="primary",
        use_container_width=True
    )

# Handle transcription
if transcribe_button:
    logger.info(f"Transcribe button clicked. URL: {audio_url}")
    if not audio_url or not audio_url.strip():
        logger.warning("Empty URL submitted")
        st.markdown('<div class="error-box">❌ <strong>Error:</strong> Please enter a valid URL</div>', unsafe_allow_html=True)
    else:
        # Show loading spinner
        logger.info(f"Starting transcription for caller_id={caller_id}, receiver_id={receiver_id}")
        with st.spinner("🔄 Transcribing audio... This may take a moment."):
            # Call the transcription function
            result = transcribe_audio(
                url=audio_url,
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
                label_visibility="collapsed"
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
                mime="text/plain"
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

# Footer
st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #666; font-size: 0.9rem;">'
    'Powered by Intermesh Transcription API | Built with Streamlit'
    '</div>',
    unsafe_allow_html=True
)
