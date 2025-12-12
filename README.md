# Buyer-Seller Voice Analytics

Audio transcription tool for analyzing buyer-seller call recordings using AI-powered speech recognition.

## Features

- 🎙️ **Single URL Transcription**: Web UI for transcribing individual audio files
- 📊 **Batch Processing**: Process multiple recordings from CSV files
- 🔄 **URL Normalization**: Automatically handles Knowlarity player pages
- 📝 **Comprehensive Logging**: All operations logged to `logs/` directory
- 💾 **Export Options**: Download transcripts as text files

## Quick Start

### Prerequisites

- Python 3.8+
- Required packages (see `requirements.txt`)

### Installation

```powershell
# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file (optional, for LLM features):

```env
LLM_API_KEY=your-api-key-here
BASE_URL=https://imllm.intermesh.net/v1
OPENAI_MODEL=google/gemini-2.5-flash
```

### Running the Application

**Streamlit Web UI** (Recommended for single transcriptions):
```powershell
streamlit run app.py
```

**Batch Processing** (For CSV files):
```powershell
python bulk.py
```

## Usage

### Web Interface

1. Launch the Streamlit app: `streamlit run app.py`
2. Paste your audio recording URL
3. (Optional) Enter caller and receiver IDs
4. Click "Transcribe Audio"
5. View and download the transcript

### Batch Processing

1. Prepare a CSV file named `calls.csv` with columns:
   - `caller_id`
   - `receiver_id`
   - `pns_call_recording_url`

2. Run: `python bulk.py`

3. Results saved to `transcriptions.jsonl`

## Logging

All operations are logged to the `logs/` directory:

- `streamlit_YYYYMMDD_HHMMSS.log` - Web UI logs
- `transcription_YYYYMMDD_HHMMSS.log` - Batch processing logs

Logs include:
- URL normalization steps
- API requests and responses
- Transcription downloads
- Error details with stack traces

## Troubleshooting

### DNS Resolution Error

If you see `NameResolutionError` for `transcribe.imutils.com`:

1. **Check network connection**: Ensure you can access the internet
2. **Verify DNS**: Try `nslookup transcribe.imutils.com`
3. **Check VPN**: If on corporate network, ensure VPN is connected
4. **Firewall**: Verify firewall isn't blocking the connection

### API Errors

Check the log files in `logs/` directory for detailed error information including:
- Full stack traces
- API request/response details
- Network error details

## Project Structure

```
buyer-seller-voice-analytics/
├── app.py                  # Streamlit web interface
├── bulk.py                 # Batch processing & core logic
├── test_gemini.py         # API connection testing
├── requirements.txt       # Python dependencies
├── .env                   # Environment configuration
├── logs/                  # Log files (auto-created)
└── README.md             # This file
```

## API Configuration

The transcription service uses:
- **Endpoint**: `http://transcribe.imutils.com/transcribe`
- **Authentication**: Bearer token (configured in `bulk.py`)
- **Team**: SELLER-BOT

## Support

For issues or questions, check the log files in `logs/` directory for detailed error information.
