# -*- coding: utf-8 -*-

import csv
import json
import time
import logging
import os
from datetime import datetime
import requests
from urllib.parse import urlparse, parse_qs

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure logging
log_filename = os.path.join("logs", f"transcription_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info(f"Logging initialized. Log file: {log_filename}")

API_URL = "http://transcribe.imutils.com/transcribe"
BEARER_TOKEN = "242c349fbd0481bb6d76a037f72ee4c8884dc8ac4199733b83d292d8258b87a0"   # change to your real token
TEAM_NAME = "SELLER-BOT"

INPUT_CSV = "calls.csv"
OUTPUT_JSONL = "transcriptions.jsonl"   # appended after each row

# column name of URL in your CSV
URL_COLUMN = "pns_call_recording_url"

headers = {
    "BearerToken": BEARER_TOKEN,
    "TeamName": TEAM_NAME,
}


def append_jsonl(path, obj):
    """Append one JSON object as a single line to JSONL file."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def normalize_recording_url(raw_url: str) -> str:
    """
    Normalize recording URLs:
    - If it is a Knowlarity player page (...playsound.html?soundurl=...), extract the soundurl.
    - Otherwise, return as-is.
    """
    logger.debug(f"Normalizing URL: {raw_url}")
    raw_url = raw_url.strip()
    if not raw_url:
        return raw_url

    if "playsound.html" in raw_url:
        parsed = urlparse(raw_url)
        qs = parse_qs(parsed.query)
        soundurls = qs.get("soundurl") or qs.get("soundUrl")
        if soundurls:
            normalized = soundurls[0].strip()
            logger.info(f"Extracted soundurl from Knowlarity player: {normalized}")
            return normalized

    logger.debug(f"URL unchanged: {raw_url}")
    return raw_url


def request_transcription(caller_id, receiver_id, recording_url, call_type="PNS"):
    logger.info(f"Requesting transcription for URL: {recording_url}")
    logger.debug(f"Caller: {caller_id}, Receiver: {receiver_id}, Type: {call_type}")
    
    files = {
        "caller_id": (None, str(caller_id)),
        "receiver_id": (None, str(receiver_id)),
        "callRecordingLink": (None, recording_url),
        "callType": (None, call_type),
    }

    try:
        resp = requests.post(API_URL, headers=headers, files=files, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        logger.debug(f"API Response: {json.dumps(data, indent=2)}")

        if data.get("Code") != 200 or data.get("Status") != "Success":
            logger.error(f"API returned error: {data}")
            raise RuntimeError("API error: %s" % data)

        media_id = data["Data"]["MediaId"]
        trans_url = data["Data"]["TranscriptionURL"]
        logger.info(f"Transcription requested successfully. MediaID: {media_id}")
        return media_id, trans_url
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during transcription request: {e}")
        raise


def download_transcription_text(url, max_retries=2):
    """
    Download the transcription text from the URL.
    Make the request look like a plain curl call.
    """
    logger.info(f"Downloading transcription from: {url}")
    dl_headers = {
        "User-Agent": "curl/7.88.1",
        "Accept": "*/*",
        # no Referer, no extra headers
    }

    last_status = None
    last_body_snippet = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.debug(f"Download attempt {attempt}/{max_retries}")
            resp = requests.get(url, headers=dl_headers, timeout=60)
            last_status = resp.status_code
            try:
                last_body_snippet = resp.text[:200]
            except Exception:
                last_body_snippet = None

            if resp.status_code == 403:
                logger.warning(f"Got 403 (attempt {attempt}/{max_retries}), backing off...")
                print("       got 403 (attempt %d/%d), backing off..." % (attempt, max_retries))
                time.sleep(5 * attempt)
                continue

            resp.raise_for_status()
            logger.info(f"Transcription downloaded successfully ({len(resp.text)} chars)")
            return resp.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during download (attempt {attempt}/{max_retries}): {e}")
            if attempt == max_retries:
                raise
            time.sleep(2 * attempt)

    error_msg = f"Failed to download transcription: status={last_status}, body_snippet={last_body_snippet!r}"
    logger.error(error_msg)
    raise RuntimeError(error_msg)


def transcribe_audio(url, caller_id="unknown", receiver_id="unknown"):
    """
    Transcribe a single audio file from URL.
    
    This is a wrapper function designed for single-URL transcription (e.g., from Streamlit UI).
    
    Args:
        url (str): Raw URL to the audio recording
        caller_id (str): Caller ID (optional, defaults to "unknown")
        receiver_id (str): Receiver ID (optional, defaults to "unknown")
    
    Returns:
        dict: Response with structure:
            {
                "success": bool,
                "data": {
                    "media_id": str,
                    "transcription_url": str,
                    "transcription": str,
                    "normalized_url": str,
                    "raw_url": str,
                    "caller_id": str,
                    "receiver_id": str
                },
                "error": str or None
            }
    """
    logger.info(f"=== Starting transcription for URL: {url} ===")
    result = {
        "success": False,
        "data": None,
        "error": None
    }
    
    try:
        # Validate URL
        if not url or not url.strip():
            logger.warning("Empty URL provided")
            result["error"] = "URL cannot be empty"
            return result
        
        # Normalize the URL
        normalized_url = normalize_recording_url(url)
        
        # Request transcription
        media_id, trans_url = request_transcription(
            caller_id=caller_id,
            receiver_id=receiver_id,
            recording_url=normalized_url,
            call_type="PNS"
        )
        
        # Download the transcription text
        transcription_text = download_transcription_text(trans_url)
        
        # Build successful response
        result["success"] = True
        result["data"] = {
            "media_id": media_id,
            "transcription_url": trans_url,
            "transcription": transcription_text,
            "normalized_url": normalized_url,
            "raw_url": url,
            "caller_id": caller_id,
            "receiver_id": receiver_id
        }
        logger.info(f"=== Transcription completed successfully. MediaID: {media_id} ===")
        
    except Exception as e:
        logger.error(f"=== Transcription failed: {e} ===", exc_info=True)
        result["error"] = str(e)
    
    return result



def main():
    # Clear the output file at start
    open(OUTPUT_JSONL, "w").close()

    with open(INPUT_CSV, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for idx, row in enumerate(reader, start=1):
            caller_id = row.get("caller_id", "").strip()
            receiver_id = row.get("receiver_id", "").strip()
            raw_url = row.get(URL_COLUMN, "").strip()

            if not raw_url:
                print("[%-4d] SKIP: empty URL" % idx)
                append_jsonl(OUTPUT_JSONL, {
                    "index": idx,
                    "caller_id": caller_id,
                    "receiver_id": receiver_id,
                    URL_COLUMN: raw_url,
                    "error": "Empty URL",
                })
                continue

            recording_url = normalize_recording_url(raw_url)

            print("[%-4d] caller_id=%s receiver_id=%s" % (idx, caller_id, receiver_id))
            print("       raw_url  = %s" % raw_url)
            print("       norm_url = %s" % recording_url)

            try:
                media_id, trans_url = request_transcription(
                    caller_id=caller_id,
                    receiver_id=receiver_id,
                    recording_url=recording_url,
                    call_type="PNS",
                )
                print("       media_id  = %s" % media_id)
                print("       trans_url = %s" % trans_url)

                text = download_transcription_text(trans_url)

                result = {
                    "index": idx,
                    "caller_id": caller_id,
                    "receiver_id": receiver_id,
                    URL_COLUMN: raw_url,
                    "normalized_url": recording_url,
                    "media_id": media_id,
                    "transcription_url": trans_url,
                    "transcription": text,
                }

                append_jsonl(OUTPUT_JSONL, result)
                print("       ✔ appended to JSONL")

            except Exception as e:
                print("       ERROR: %s" % e)
                append_jsonl(OUTPUT_JSONL, {
                    "index": idx,
                    "caller_id": caller_id,
                    "receiver_id": receiver_id,
                    URL_COLUMN: raw_url,
                    "normalized_url": recording_url,
                    "error": str(e),
                })

            # Delay to avoid rate limiting
            time.sleep(2.5)


if __name__ == "__main__":
    main()
