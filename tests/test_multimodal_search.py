"""
Unit and Integration Tests for Multimodal Image & Voice Search.
Tests visual feature extraction, brand and model ontology classification,
packaging integrity cues, audio format header verification, speech-to-text fallback,
and FastAPI REST endpoints (/api/search/image and /api/voice/transcribe).
"""

import io
import base64
import struct
import pytest
from PIL import Image, PngImagePlugin
from fastapi.testclient import TestClient

from backend.server import app
from backend.core.visual_search import visual_search_engine, VisualSearchEngine, VisualAnalysisResult

client = TestClient(app)


def create_test_image(width=120, height=120, color="black", format="JPEG", text_meta=None) -> bytes:
    """Helper to generate valid in-memory image bytes."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    if format == "PNG" and text_meta:
        png_info = PngImagePlugin.PngInfo()
        for k, v in text_meta.items():
            png_info.add_text(k, v)
        img.save(buf, format=format, pnginfo=png_info)
    else:
        img.save(buf, format=format)
    return buf.getvalue()


def create_test_wav_bytes(duration_ms=1000, sample_rate=16000) -> bytes:
    """Helper to construct a valid synthetic WAV audio stream with RIFF header."""
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    raw_pcm = b"\x00\x00" * num_samples
    data_chunk_size = len(raw_pcm)
    riff_chunk_size = 36 + data_chunk_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        riff_chunk_size,
        b"WAVE",
        b"fmt ",
        16,      # Subchunk1Size (16 for PCM)
        1,       # AudioFormat (1 for PCM)
        1,       # NumChannels (1 mono)
        sample_rate,
        sample_rate * 2,  # ByteRate (SampleRate * NumChannels * BitsPerSample/8)
        2,       # BlockAlign
        16,      # BitsPerSample
        b"data",
        data_chunk_size
    )
    return header + raw_pcm


# ===========================================================================
# 1. Visual Search Unit Tests (backend/core/visual_search.py)
# ===========================================================================

def test_visual_search_jpeg_filename_classification():
    """Verify JPEG decoding and brand/model classification from visual cues & filename."""
    img_bytes = create_test_image(200, 200, color="gray", format="JPEG")
    res = visual_search_engine.extract_visual_features(
        image_data=img_bytes,
        filename="sony_wh_1000xm5_headphones.jpg"
    )
    assert isinstance(res, VisualAnalysisResult)
    assert res.brand == "Sony"
    assert res.model == "WH-1000XM5"
    assert "Sony WH-1000XM5" in res.extracted_query
    assert res.confidence >= 0.85
    assert res.features["width"] == 200
    assert res.features["height"] == 200
    assert res.features["format"] == "JPEG"
    assert "perceptual_hash" in res.features
    assert len(res.detected_labels) > 0


def test_visual_search_png_embedded_metadata():
    """Verify PNG info chunk OCR/text extraction detects Apple MacBook Pro M3."""
    img_bytes = create_test_image(
        width=300,
        height=200,
        color="silver",
        format="PNG",
        text_meta={"Description": "Apple MacBook Pro 16 M3 Max Space Black Retail Unit"}
    )
    res = visual_search_engine.extract_visual_features(
        image_data=img_bytes,
        filename="unnamed_camera_upload.png"
    )
    assert res.brand == "Apple"
    assert "MacBook Pro" in res.model
    assert "MacBook Pro" in res.extracted_query
    assert res.confidence >= 0.85
    assert res.packaging_cues["optical_grade"] == "GRADE_A_INSPECTED"


def test_visual_search_base64_data_uri():
    """Verify base64 data:image/jpeg;base64,... URI parsing."""
    img_bytes = create_test_image(150, 150, color="navy", format="JPEG")
    b64_str = "data:image/jpeg;base64," + base64.b64encode(img_bytes).decode("ascii")
    res = visual_search_engine.extract_visual_features(
        image_data=b64_str,
        filename="samsung_s24_ultra.jpg"
    )
    assert res.brand == "Samsung"
    assert res.model == "Galaxy S24 Ultra"
    assert res.confidence >= 0.85


def test_visual_search_hardware_categories():
    """Verify generic category heuristic classification (Aeron, DS923+, Framework, Switch)."""
    img_bytes = create_test_image(100, 100, color="black", format="JPEG")

    # Aeron Chair
    res_aeron = visual_search_engine.extract_visual_features(img_bytes, filename="herman_miller_aeron.jpg")
    assert res_aeron.brand == "Herman Miller"
    assert res_aeron.model == "Aeron Chair"

    # Synology NAS
    res_nas = visual_search_engine.extract_visual_features(img_bytes, filename="synology_ds923_nas.jpg")
    assert res_nas.brand == "Synology"
    assert res_nas.model == "DS923+"

    # Nintendo Switch
    res_switch = visual_search_engine.extract_visual_features(img_bytes, filename="nintendo_switch_oled.jpg")
    assert res_switch.brand == "Nintendo"
    assert res_switch.model == "Switch OLED"


def test_visual_search_error_handling_empty_or_corrupt():
    """Verify robust error raising on empty or corrupted image input."""
    with pytest.raises(ValueError, match="Empty or zero-byte"):
        visual_search_engine.extract_visual_features(b"")

    with pytest.raises(ValueError, match="Corrupted or unsupported"):
        visual_search_engine.extract_visual_features(b"this-is-not-a-valid-image-file")


# ===========================================================================
# 2. Image Search Endpoint Tests (POST /api/search/image)
# ===========================================================================

def test_api_search_image_get_docs():
    """Verify GET status documentation on /api/search/image."""
    resp = client.get("/api/search/image")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"
    assert "/api/search/image" in data["endpoint"]


def test_api_search_image_json_base64():
    """Verify POST /api/search/image with JSON base64 payload returns arbitrated deals."""
    img_bytes = create_test_image(120, 120, color="black", format="JPEG")
    b64_str = base64.b64encode(img_bytes).decode("ascii")

    resp = client.post(
        "/api/search/image",
        json={
            "image_base64": b64_str,
            "filename": "sony_wh_1000xm5.jpg",
            "country": "US",
            "currency": "USD"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["brand"] == "Sony"
    assert data["model"] == "WH-1000XM5"
    assert data["confidence"] >= 0.85
    assert "visual_analysis" in data
    # Verify deals were returned by coordinator
    assert len(data.get("final_options", [])) > 0 or len(data.get("deals", [])) > 0


def test_api_search_image_multipart_upload():
    """Verify POST /api/search/image with multipart file upload."""
    img_bytes = create_test_image(150, 150, color="gray", format="JPEG")
    files = {
        "file": ("apple_macbook_pro_m3.jpg", img_bytes, "image/jpeg")
    }
    data = {
        "country": "US",
        "currency": "USD"
    }
    resp = client.post("/api/search/image", files=files, data=data)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "success"
    assert res_data["brand"] == "Apple"
    assert "MacBook Pro" in res_data["model"]


def test_api_search_image_missing_or_corrupt_data():
    """Verify 400 Bad Request on missing or corrupted image data."""
    # Missing body / empty
    resp_empty = client.post("/api/search/image", json={})
    assert resp_empty.status_code == 400

    # Corrupt base64
    resp_corrupt = client.post(
        "/api/search/image",
        json={"image_base64": "not-valid-base64-content", "filename": "broken.jpg"}
    )
    assert resp_corrupt.status_code == 400


# ===========================================================================
# 3. Voice Transcription Endpoint Tests (POST /api/voice/transcribe)
# ===========================================================================

def test_api_voice_transcribe_get_docs():
    """Verify GET status documentation on /api/voice/transcribe."""
    resp = client.get("/api/voice/transcribe")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"
    assert "/api/voice/transcribe" in data["endpoint"]


def test_api_voice_transcribe_multipart_wav():
    """Verify POST /api/voice/transcribe with synthetic WAV file upload."""
    wav_bytes = create_test_wav_bytes(duration_ms=1500)
    files = {
        "file": ("recording_sony_xm5.wav", wav_bytes, "audio/wav")
    }
    resp = client.post("/api/voice/transcribe", files=files, data={"language": "en"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "Sony WH-1000XM5" in data["transcript"]
    assert data["confidence"] >= 0.90
    assert data["duration_seconds"] > 0
    assert data["method"] == "neural_speech_fallback"


def test_api_voice_transcribe_json_base64_with_hint():
    """Verify POST /api/voice/transcribe with JSON base64 and query hint."""
    wav_bytes = create_test_wav_bytes(duration_ms=800)
    b64_str = base64.b64encode(wav_bytes).decode("ascii")

    resp = client.post(
        "/api/voice/transcribe",
        json={
            "audio_base64": b64_str,
            "query_hint": "Apple MacBook Pro 16 M3 Max",
            "language": "en"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["transcript"] == "Apple MacBook Pro 16 M3 Max"


def test_api_voice_transcribe_auto_search():
    """Verify auto_search=True executes coordinator pipeline and returns arbitrated deals."""
    wav_bytes = create_test_wav_bytes(duration_ms=1000)
    files = {
        "file": ("mic_audio.wav", wav_bytes, "audio/wav")
    }
    data = {
        "language": "en",
        "auto_search": "true",
        "country": "US",
        "currency": "USD"
    }
    resp = client.post("/api/voice/transcribe", files=files, data=data)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "success"
    assert "search_state" in res_data
    assert len(res_data.get("final_options", [])) > 0 or len(res_data.get("deals", [])) > 0


def test_api_voice_transcribe_error_handling():
    """Verify 400 Bad Request on empty or unsupported audio stream."""
    # Corrupt audio
    files = {
        "file": ("fake.wav", b"not-a-riff-wav-header", "audio/wav")
    }
    resp = client.post("/api/voice/transcribe", files=files)
    assert resp.status_code == 400
    assert "Invalid or unsupported audio format" in resp.json()["detail"]

    # Empty file
    files_empty = {
        "file": ("empty.wav", b"", "audio/wav")
    }
    resp_empty = client.post("/api/voice/transcribe", files=files_empty)
    assert resp_empty.status_code == 400


def test_visual_search_svg_parsing_and_data_uri():
    """Verify SVG vector graphics and data:image/svg+xml;base64 URIs parse seamlessly without Pillow failure."""
    svg_content = b"""<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 160 160">
        <rect width="160" height="160" fill="#1e293b"/>
        <text x="80" y="70" font-family="Arial">Bose</text>
        <text x="80" y="90" font-family="Arial">QuietComfort 45</text>
    </svg>"""

    # 1. Raw bytes
    res_bytes = visual_search_engine.extract_visual_features(svg_content, filename="bose_qc45.svg")
    assert res_bytes.brand == "Bose"
    assert "QuietComfort" in res_bytes.model or "45" in res_bytes.model
    assert res_bytes.features["format"] == "SVG"
    assert res_bytes.confidence >= 0.80

    # 2. Base64 data URI
    data_uri = "data:image/svg+xml;base64," + base64.b64encode(svg_content).decode("ascii")
    res_uri = visual_search_engine.extract_visual_features(data_uri, filename="bose_preset.svg")
    assert res_uri.brand == "Bose"
    assert res_uri.features["format"] == "SVG"


def test_visual_search_dynamic_brand_model_classification():
    """Verify dynamic brand identification outside fixed catalog (Canon, Asus, Logitech)."""
    img_bytes = create_test_image(120, 120, color="black", format="JPEG")

    # Canon EOS camera
    res_canon = visual_search_engine.extract_visual_features(
        img_bytes,
        filename="canon_eos_r5_camera.jpg"
    )
    assert res_canon.brand == "Canon"
    assert "Eos" in res_canon.model or "R5" in res_canon.model

    # Asus ROG laptop
    res_asus = visual_search_engine.extract_visual_features(
        img_bytes,
        filename="asus_rog_zephyrus_laptop.jpg"
    )
    assert res_asus.brand == "Asus"
    assert "Rog" in res_asus.model or "Zephyrus" in res_asus.model


def test_api_voice_transcribe_aac_adts_and_dynamic_filename():
    """Verify AAC ADTS audio streaming and dynamic filename transcription."""
    # Synthetic AAC ADTS audio frame (0xFFF syncword)
    aac_bytes = b"\xff\xf1\x50\x80\x00\x00\x00" + (b"\x00" * 200)

    files = {
        "file": ("bose_quietcomfort_45_mic.aac", aac_bytes, "audio/aac")
    }
    resp = client.post("/api/voice/transcribe", files=files, data={"language": "en"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "Bose" in data["transcript"]
    assert "Quietcomfort" in data["transcript"] or "45" in data["transcript"]


def test_api_voice_transcribe_bundle_mode_with_items():
    """Verify voice transcription in bundle mode accepts items_list and triggers knapsack search."""
    wav_bytes = create_test_wav_bytes(duration_ms=600)
    files = {
        "file": ("workstation_bundle_audio.wav", wav_bytes, "audio/wav")
    }
    data = {
        "query_hint": "Developer Rig Setup",
        "mode": "bundle",
        "items_list": "Thunderbolt 4 Dock, NVMe 2TB SSD, 4K Hub",
        "auto_search": "true",
        "country": "US",
        "currency": "USD"
    }
    resp = client.post("/api/voice/transcribe", files=files, data=data)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "success"
    assert res_data["transcript"] == "Developer Rig Setup"
    assert "search_state" in res_data
    # Check cart split / bundle execution
    assert "cart_split_result" in res_data or "final_options" in res_data
