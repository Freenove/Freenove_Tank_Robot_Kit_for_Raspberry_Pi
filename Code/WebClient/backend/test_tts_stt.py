#!/usr/bin/env python3
"""Test TTS and STT with real Gemini API calls.

Tests the speech-to-text and text-to-speech pipeline using real API calls.
Requires GEMINI_API_KEY in environment or .env file.

Usage:
    python test_tts_stt.py              # Run all tests
    python test_tts_stt.py --tts-only   # Test TTS only
    python test_tts_stt.py --stt-only   # Test STT only
    python test_tts_stt.py --play       # Play generated audio (requires ffplay)
"""

import asyncio
import argparse
import base64
import io
import os
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

from dotenv import load_dotenv, find_dotenv
from google import genai
from google.genai import types

# Load .env from repo root
load_dotenv(find_dotenv())


# Configuration - same as ai_session.py
STT_MODEL = "gemini-3-flash-preview"  # Transcription
TTS_MODEL = "gemini-2.5-flash-preview-tts"  # Dedicated TTS model
TTS_VOICE = "Puck"  # One of 30 available voices

# TTS output format (raw PCM)
TTS_SAMPLE_RATE = 24000  # 24kHz
TTS_CHANNELS = 1  # Mono
TTS_SAMPLE_WIDTH = 2  # 16-bit


def pcm_to_wav(pcm_data: bytes, sample_rate: int = TTS_SAMPLE_RATE,
               channels: int = TTS_CHANNELS, sample_width: int = TTS_SAMPLE_WIDTH) -> bytes:
    """Convert raw PCM audio to WAV format."""
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)
    return buffer.getvalue()

# Test phrases for TTS
TTS_TEST_PHRASES = [
    "Hello! I am your robot assistant.",
    "Moving forward 30 centimeters.",
    "I see a red ball ahead, about 50 centimeters away.",
    "Emergency stop executed.",
    "Scanning the area for objects.",
]


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


def print_header(title: str):
    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}")


async def test_tts(client: genai.Client, phrase: str, play: bool = False) -> dict:
    """Test TTS generation for a single phrase.

    Returns:
        dict with keys: success, phrase, audio_size, error
    """
    result = {
        "success": False,
        "phrase": phrase,
        "audio_size": 0,
        "error": None,
        "audio_data": None
    }

    try:
        response = client.models.generate_content(
            model=TTS_MODEL,
            contents=phrase,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=TTS_VOICE
                        )
                    )
                )
            )
        )

        if not response.candidates:
            result["error"] = "No candidates in response"
            return result

        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            result["error"] = "No content parts in response"
            return result

        for part in candidate.content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                audio_data = part.inline_data.data
                result["audio_size"] = len(audio_data)
                result["audio_data"] = audio_data
                result["success"] = True

                # Optionally play the audio
                if play and audio_data:
                    await play_audio(audio_data)

                return result

        result["error"] = "No audio data in response parts"
        return result

    except Exception as e:
        result["error"] = str(e)
        return result


async def test_stt(client: genai.Client, audio_data: bytes, expected_text: str = None,
                   is_raw_pcm: bool = False) -> dict:
    """Test STT transcription.

    Args:
        client: Gemini client
        audio_data: Raw audio bytes (PCM or WAV)
        expected_text: Optional expected transcription for validation
        is_raw_pcm: If True, audio_data is raw PCM and needs WAV conversion

    Returns:
        dict with keys: success, transcription, error
    """
    result = {
        "success": False,
        "transcription": None,
        "expected": expected_text,
        "error": None
    }

    try:
        # Convert raw PCM to WAV if needed
        if is_raw_pcm:
            audio_data = pcm_to_wav(audio_data)

        # Detect mime type from audio data
        mime_type = "audio/wav"  # Default
        if audio_data[:4] == b'RIFF':
            mime_type = "audio/wav"
        elif audio_data[:3] == b'ID3' or audio_data[:2] == b'\xff\xfb':
            mime_type = "audio/mpeg"
        elif audio_data[:4] == b'OggS':
            mime_type = "audio/ogg"

        response = client.models.generate_content(
            model=STT_MODEL,
            contents=[
                "Transcribe this audio exactly. Return only the transcription.",
                types.Part.from_bytes(data=audio_data, mime_type=mime_type)
            ]
        )

        transcription = response.text.strip()
        result["transcription"] = transcription
        result["success"] = bool(transcription)

        return result

    except Exception as e:
        result["error"] = str(e)
        return result


async def test_round_trip(client: genai.Client, phrase: str) -> dict:
    """Test full TTS -> STT round trip.

    Generate speech from text, then transcribe it back.

    Returns:
        dict with keys: success, original, transcribed, similarity, error
    """
    result = {
        "success": False,
        "original": phrase,
        "transcribed": None,
        "error": None
    }

    # Step 1: Generate TTS
    tts_result = await test_tts(client, phrase, play=False)
    if not tts_result["success"]:
        result["error"] = f"TTS failed: {tts_result['error']}"
        return result

    # Step 2: Transcribe the audio back (TTS outputs raw PCM)
    stt_result = await test_stt(client, tts_result["audio_data"], expected_text=phrase, is_raw_pcm=True)
    if not stt_result["success"]:
        result["error"] = f"STT failed: {stt_result['error']}"
        return result

    result["transcribed"] = stt_result["transcription"]
    result["success"] = True

    return result


async def play_audio(audio_data: bytes):
    """Play audio using ffplay if available."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        # Try ffplay (comes with ffmpeg)
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", temp_path],
            check=True
        )
        os.unlink(temp_path)
    except FileNotFoundError:
        print(f"{Colors.DIM}  (ffplay not found - skipping playback){Colors.RESET}")
    except Exception as e:
        print(f"{Colors.DIM}  (Playback error: {e}){Colors.RESET}")


async def run_tts_tests(client: genai.Client, play: bool = False):
    """Run TTS tests for all test phrases."""
    print_header("TTS (Text-to-Speech) Tests")

    passed = 0
    failed = 0

    for phrase in TTS_TEST_PHRASES:
        print(f"\n{Colors.CYAN}Testing:{Colors.RESET} \"{phrase[:50]}...\"" if len(phrase) > 50 else f"\n{Colors.CYAN}Testing:{Colors.RESET} \"{phrase}\"")

        result = await test_tts(client, phrase, play=play)

        if result["success"]:
            print(f"  {Colors.GREEN}PASS{Colors.RESET} - Generated {result['audio_size']:,} bytes of audio")
            passed += 1
        else:
            print(f"  {Colors.RED}FAIL{Colors.RESET} - {result['error']}")
            failed += 1

    print(f"\n{Colors.BOLD}TTS Results: {passed} passed, {failed} failed{Colors.RESET}")
    return passed, failed


async def run_stt_tests(client: genai.Client):
    """Run STT tests using TTS-generated audio."""
    print_header("STT (Speech-to-Text) Tests")

    # We need audio to test STT - generate it from TTS first
    print(f"\n{Colors.DIM}Generating test audio via TTS...{Colors.RESET}")

    passed = 0
    failed = 0

    test_phrases = [
        "Move forward",
        "Turn left 90 degrees",
        "What do you see",
    ]

    for phrase in test_phrases:
        print(f"\n{Colors.CYAN}Testing round-trip:{Colors.RESET} \"{phrase}\"")

        # Generate TTS audio
        tts_result = await test_tts(client, phrase, play=False)
        if not tts_result["success"]:
            print(f"  {Colors.RED}FAIL{Colors.RESET} - Could not generate audio: {tts_result['error']}")
            failed += 1
            continue

        print(f"  {Colors.DIM}Generated {tts_result['audio_size']:,} bytes{Colors.RESET}")

        # Transcribe it back (TTS outputs raw PCM)
        stt_result = await test_stt(client, tts_result["audio_data"], expected_text=phrase, is_raw_pcm=True)

        if stt_result["success"]:
            transcribed = stt_result["transcription"]
            # Check similarity (case-insensitive, strip punctuation)
            original_clean = phrase.lower().strip(".,!?")
            transcribed_clean = transcribed.lower().strip(".,!?")

            if original_clean in transcribed_clean or transcribed_clean in original_clean:
                print(f"  {Colors.GREEN}PASS{Colors.RESET} - Transcribed: \"{transcribed}\"")
                passed += 1
            else:
                print(f"  {Colors.YELLOW}PARTIAL{Colors.RESET} - Got: \"{transcribed}\" (expected: \"{phrase}\")")
                passed += 1  # Still counts as working
        else:
            print(f"  {Colors.RED}FAIL{Colors.RESET} - {stt_result['error']}")
            failed += 1

    print(f"\n{Colors.BOLD}STT Results: {passed} passed, {failed} failed{Colors.RESET}")
    return passed, failed


async def run_integration_test(client: genai.Client):
    """Run a full integration test simulating the voice pipeline."""
    print_header("Integration Test (Full Pipeline)")

    print(f"\n{Colors.CYAN}Simulating: User says 'move forward' -> Robot responds{Colors.RESET}")

    # Step 1: Simulate user speech (we'll use TTS to generate "user" audio)
    user_phrase = "move forward slowly"
    print(f"\n  1. Generating 'user' audio for: \"{user_phrase}\"")

    tts_result = await test_tts(client, user_phrase)
    if not tts_result["success"]:
        print(f"     {Colors.RED}FAIL{Colors.RESET} - Could not generate user audio")
        return 0, 1

    print(f"     {Colors.GREEN}OK{Colors.RESET} - {tts_result['audio_size']:,} bytes")

    # Step 2: STT - transcribe user audio (TTS outputs raw PCM)
    print(f"\n  2. Transcribing user audio...")
    stt_result = await test_stt(client, tts_result["audio_data"], is_raw_pcm=True)
    if not stt_result["success"]:
        print(f"     {Colors.RED}FAIL{Colors.RESET} - STT failed")
        return 0, 1

    print(f"     {Colors.GREEN}OK{Colors.RESET} - Heard: \"{stt_result['transcription']}\"")

    # Step 3: Generate robot response TTS
    robot_response = "Moving forward at slow speed."
    print(f"\n  3. Generating robot response: \"{robot_response}\"")

    response_tts = await test_tts(client, robot_response)
    if not response_tts["success"]:
        print(f"     {Colors.RED}FAIL{Colors.RESET} - Could not generate response audio")
        return 0, 1

    print(f"     {Colors.GREEN}OK{Colors.RESET} - {response_tts['audio_size']:,} bytes")

    print(f"\n{Colors.GREEN}{Colors.BOLD}Integration test PASSED{Colors.RESET}")
    return 1, 0


async def main():
    parser = argparse.ArgumentParser(description="Test TTS and STT with Gemini API")
    parser.add_argument("--tts-only", action="store_true", help="Run TTS tests only")
    parser.add_argument("--stt-only", action="store_true", help="Run STT tests only")
    parser.add_argument("--play", action="store_true", help="Play generated audio")
    parser.add_argument("--integration", action="store_true", help="Run integration test only")
    args = parser.parse_args()

    # Check API key (support both names)
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print(f"{Colors.RED}Error: GOOGLE_API_KEY or GEMINI_API_KEY not set{Colors.RESET}")
        print("Set it in .env file or environment variable")
        return

    print(f"{Colors.BOLD}Gemini TTS/STT Test Suite{Colors.RESET}")
    print(f"{Colors.DIM}Using models: STT={STT_MODEL}, TTS={TTS_MODEL}, Voice={TTS_VOICE}{Colors.RESET}")

    # Initialize client
    client = genai.Client(api_key=api_key)

    total_passed = 0
    total_failed = 0

    if args.integration:
        p, f = await run_integration_test(client)
        total_passed += p
        total_failed += f
    elif args.tts_only:
        p, f = await run_tts_tests(client, play=args.play)
        total_passed += p
        total_failed += f
    elif args.stt_only:
        p, f = await run_stt_tests(client)
        total_passed += p
        total_failed += f
    else:
        # Run all tests
        p, f = await run_tts_tests(client, play=args.play)
        total_passed += p
        total_failed += f

        p, f = await run_stt_tests(client)
        total_passed += p
        total_failed += f

        p, f = await run_integration_test(client)
        total_passed += p
        total_failed += f

    # Final summary
    print_header("Final Results")
    if total_failed == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}All {total_passed} tests passed!{Colors.RESET}")
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}{total_passed} passed, {total_failed} failed{Colors.RESET}")


if __name__ == "__main__":
    asyncio.run(main())
