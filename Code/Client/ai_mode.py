"""AI Mode - Unified voice control for tank robot.

Architecture:
- AIModeSession: Push-to-talk voice control
  - STT: Gemini 2.5 Flash (audio understanding)
  - Agent: ADK with Gemini 3 Flash (reasoning + tools)
  - TTS: Gemini 2.5 Flash TTS (native voice output)
- Hard-coded safety layer - Distance checks OUTSIDE LLM control

Audio Specs:
- Input: 16-bit PCM, 16kHz, mono
- Output: 16-bit PCM, 24kHz, mono
"""
import os
import io
import time
import wave
import asyncio
import base64
import threading
import functools
from pathlib import Path
from typing import Optional
import cv2
from dotenv import load_dotenv, find_dotenv

from PyQt5.QtCore import QObject, pyqtSignal  # [FIX #3] Qt signals

from google import genai
from google.genai import types
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService

# Load .env from repo root (find_dotenv walks up directory tree)
load_dotenv(find_dotenv())

# Audio constants
AUDIO_INPUT_RATE = 16000   # Live API input: 16kHz
AUDIO_OUTPUT_RATE = 24000  # Live API output: 24kHz
AUDIO_CHANNELS = 1
AUDIO_SAMPLE_WIDTH = 2     # 16-bit = 2 bytes

# Aliases for backward compatibility
AUDIO_SAMPLE_RATE = AUDIO_INPUT_RATE

def _pcm_to_wav(pcm_data: bytes) -> bytes:
    """Convert raw PCM audio to WAV format for Gemini API.

    Gemini's generate_content API expects audio in container formats (WAV, MP3, etc.)
    not raw PCM. This wraps the PCM data with a proper WAV header.
    """
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(AUDIO_CHANNELS)
        wav_file.setsampwidth(AUDIO_SAMPLE_WIDTH)
        wav_file.setframerate(AUDIO_SAMPLE_RATE)
        wav_file.writeframes(pcm_data)
    return wav_buffer.getvalue()

# TTS voice configuration
TTS_VOICE = "Puck"  # Options: Puck, Charon, Kore, Fenrir, Aoede
TTS_MODEL = "gemini-2.0-flash-exp"  # Supports audio output

# Global genai client - initialized in AIModeSession.initialize()
_genai_client = None

# ============================================================
# Configuration
# ============================================================

ULTRASONIC_STALE_THRESHOLD = 2.0  # seconds before reading is stale
SAFETY_DISTANCE_BLOCK = 15  # cm - hard block forward movement

# ============================================================
# Sensor Cache - Simple globals + lock
# ============================================================

_sensors = {}
_sensor_lock = threading.Lock()

def update_sensor(key: str, value):
    with _sensor_lock:
        _sensors[key] = (value, time.time())

def get_sensor(key: str) -> tuple:
    """Returns (value, age_seconds) or (None, 0) if not found."""
    with _sensor_lock:
        if key not in _sensors:
            return None, 0
        value, ts = _sensors[key]
        return value, time.time() - ts

def parse_robot_message(message: str):
    """Parse incoming robot messages and update sensor cache."""
    parts = message.strip().split("#")
    if len(parts) < 2:
        return
    cmd = parts[0]
    if cmd == "CMD_SONIC":
        try:
            update_sensor("ultrasonic", float(parts[1]))
        except ValueError:
            pass
    elif cmd == "CMD_ACTION":
        status_map = {"0": "stopped", "10": "up_complete", "20": "down_complete"}
        update_sensor("clamp", status_map.get(parts[1], "unknown"))

# ============================================================
# Video Frame + TCP - Thread-safe
# ============================================================

_video_frame = None
_frame_lock = threading.Lock()
_tcp_client = None
_tcp_lock = threading.Lock()

def set_tcp_client(client):
    global _tcp_client
    _tcp_client = client

def set_video_frame(frame):
    global _video_frame
    with _frame_lock:
        _video_frame = frame.copy() if frame is not None else None

def _encode_frame_small() -> Optional[str]:
    """Encode frame as small JPEG (320x240, quality 50)."""
    with _frame_lock:
        if _video_frame is None:
            return None
        frame = _video_frame.copy()
    try:
        small = cv2.resize(frame, (320, 240))
        _, buf = cv2.imencode('.jpg', small, [cv2.IMWRITE_JPEG_QUALITY, 50])
        return base64.b64encode(buf).decode()
    except Exception:
        return None

def is_connected() -> bool:
    return _tcp_client is not None and getattr(_tcp_client, 'connect_Flag', False)

# ============================================================
# Robot Actions - DRY with decorator [SIMPLIFIED]
# ============================================================

def _requires_connection(func):
    """Decorator: Return error if robot not connected."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not is_connected():
            return "ERROR: Robot not connected"
        return func(*args, **kwargs)
    return wrapper

def _send_command(cmd: str):
    """Thread-safe command send."""
    if _tcp_client and is_connected():
        with _tcp_lock:
            _tcp_client.sendData(cmd)

@_requires_connection
def move_forward(speed: int = 2000) -> str:
    """Move forward. HARD-CODED SAFETY: blocks if distance < 15cm or stale."""
    distance, age = get_sensor("ultrasonic")
    if distance is None or age > ULTRASONIC_STALE_THRESHOLD:
        return "BLOCKED: No reliable distance reading"
    if distance < SAFETY_DISTANCE_BLOCK:
        return f"BLOCKED: Obstacle at {distance:.1f}cm"
    speed = max(0, min(2500, abs(speed)))
    _send_command(f"CMD_MOTOR#{speed}#{speed}\n")
    _send_command("CMD_SONIC#\n")  # [SIMPLIFIED] Inline sense request
    return f"Moving forward at speed {speed}"

@_requires_connection
def move_backward(speed: int = 2000) -> str:
    speed = max(0, min(2500, abs(speed)))
    _send_command(f"CMD_MOTOR#{-speed}#{-speed}\n")
    return f"Moving backward at speed {speed}"

@_requires_connection
def turn_left(speed: int = 1500) -> str:
    speed = max(0, min(2500, abs(speed)))
    _send_command(f"CMD_MOTOR#{-speed}#{speed}\n")
    return f"Turning left at speed {speed}"

@_requires_connection
def turn_right(speed: int = 1500) -> str:
    speed = max(0, min(2500, abs(speed)))
    _send_command(f"CMD_MOTOR#{speed}#{-speed}\n")
    return f"Turning right at speed {speed}"

def stop() -> str:
    """EMERGENCY STOP - [FIX #2] Bypasses connection check (best-effort)."""
    if _tcp_client:
        try:
            with _tcp_lock:
                _tcp_client.sendData("CMD_MOTOR#0#0\n")
        except Exception:
            pass  # Best-effort emergency stop
    return "STOPPED"

@_requires_connection
def set_servo(channel: int, angle: int) -> str:
    channel, angle = max(0, min(1, channel)), max(90, min(150, angle))
    _send_command(f"CMD_SERVO#{channel}#{angle}\n")
    return f"Servo {'pan' if channel == 0 else 'tilt'} set to {angle} degrees"

@_requires_connection
def set_leds(r: int, g: int, b: int) -> str:
    r, g, b = [max(0, min(255, c)) for c in (r, g, b)]
    _send_command(f"CMD_LED#1#{r}#{g}#{b}#15\n")
    return f"LEDs set to RGB({r},{g},{b})"

@_requires_connection
def clamp_up() -> str:
    _send_command("CMD_ACTION#1\n")
    return "Clamp moving up"

@_requires_connection
def clamp_down() -> str:
    _send_command("CMD_ACTION#2\n")
    return "Clamp moving down"

def get_sensor_status() -> str:
    """Get current sensor readings for Live API tool calling."""
    distance, age = get_sensor("ultrasonic")
    clamp, _ = get_sensor("clamp")
    connected = is_connected()

    parts = []
    parts.append(f"Robot: {'Connected' if connected else 'DISCONNECTED'}")
    if distance is not None:
        stale = " (STALE)" if age > ULTRASONIC_STALE_THRESHOLD else ""
        parts.append(f"Distance: {distance:.1f}cm{stale}")
    else:
        parts.append("Distance: No reading (forward movement blocked)")
    if clamp:
        parts.append(f"Clamp: {clamp}")
    return ", ".join(parts)

# All robot tools for ADK agent
ROBOT_TOOLS = [move_forward, move_backward, turn_left, turn_right, stop,
               set_servo, set_leds, clamp_up, clamp_down, get_sensor_status]

# ============================================================
# Robot Brain - Gemini 3 Flash
# ============================================================

ROBOT_BRAIN_INSTRUCTION = """You are the intelligent brain of a tank robot.

ENVIRONMENT (provided every message): Distance (cm), Camera view, Clamp state
TOOLS: move_forward/backward(speed), turn_left/right(speed), stop(), set_servo(ch,angle), set_leds(r,g,b), clamp_up/down()
SAFETY: <15cm blocked, no reading blocked, "stop/halt/emergency" instant stop
STYLE: Be CONCISE. "Moving forward" not "I am now executing..."
"""

_robot_brain: Optional[Agent] = None
_brain_runner: Optional[Runner] = None
_brain_session_service: Optional[InMemorySessionService] = None
_brain_session_id: Optional[str] = None
_brain_lock = asyncio.Lock()

async def _ensure_brain_async():
    """Initialize Robot Brain agent and create session (async for proper session creation)."""
    global _robot_brain, _brain_runner, _brain_session_service, _brain_session_id
    async with _brain_lock:
        if _robot_brain is None:
            _robot_brain = Agent(model="gemini-2.0-flash-exp", name="robot_brain",
                                 instruction=ROBOT_BRAIN_INSTRUCTION, tools=ROBOT_TOOLS)
            _brain_session_service = InMemorySessionService()
            _brain_runner = Runner(agent=_robot_brain, app_name="robot_brain",
                                   session_service=_brain_session_service)
            # Create session explicitly per ADK docs
            session = await _brain_session_service.create_session(
                app_name="robot_brain",
                user_id="user",
                state={}  # Initial state (can be used for context)
            )
            _brain_session_id = session.id

# ============================================================
# robot_command() - Sensor Injection + Emergency Fast-Path
# ============================================================

async def robot_command(user_command: str, emit_callback=None) -> str:
    """Process command with environment context. Uses Gemini 3 Flash for reasoning.

    Args:
        user_command: The user's voice command
        emit_callback: Optional callback(role, text) to emit conversation events
            Roles: "env" (sensors), "prompt" (full prompt), "tool" (tool calls),
                   "tool_result" (tool outputs), "robot" (final response)
    """
    def emit(role, text):
        if emit_callback:
            emit_callback(role, text)

    # Emergency fast-path - bypass LLM entirely
    if any(w in user_command.lower() for w in ("stop", "halt", "freeze", "emergency")):
        result = stop()
        emit("tool", "stop()")
        emit("tool_result", result)
        return f"Emergency stop: {result}"

    await _ensure_brain_async()  # Async initialization with proper session creation

    # Gather environment context
    distance, age = get_sensor("ultrasonic")
    clamp, _ = get_sensor("clamp")
    frame_b64 = _encode_frame_small()

    # Build environment context for Gemini 3 Flash
    status = "DISCONNECTED" if not is_connected() else "Connected"
    dist_str = f"{distance:.1f}cm" if distance else "No reading (forward blocked)"
    if distance and age > ULTRASONIC_STALE_THRESHOLD:
        dist_str += f" (stale {age:.1f}s)"
    env = f"Robot: {status}, Distance: {dist_str}, Camera: {'attached' if frame_b64 else 'none'}"
    if clamp:
        env += f", Clamp: {clamp}"

    # Emit environment context
    emit("env", env)

    prompt = f"[ENV] {env}\n[COMMAND] {user_command}"
    emit("prompt", prompt)

    parts = [types.Part.from_text(prompt)]
    if frame_b64:
        parts.append(types.Part.from_bytes(data=base64.b64decode(frame_b64), mime_type="image/jpeg"))
        emit("camera", "[Camera frame attached]")

    try:
        # ADK run_async returns async generator - iterate to get response
        result_text = ""
        tool_calls_seen = set()

        async def run_with_timeout():
            nonlocal result_text
            async for event in _brain_runner.run_async(
                user_id="user",
                session_id=_brain_session_id,
                new_message=types.Content(role="user", parts=parts)
            ):
                # Capture tool calls
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        # Check for function calls
                        if hasattr(part, 'function_call') and part.function_call:
                            fc = part.function_call
                            call_str = f"{fc.name}({fc.args})" if fc.args else f"{fc.name}()"
                            if call_str not in tool_calls_seen:
                                tool_calls_seen.add(call_str)
                                emit("tool", call_str)
                        # Check for function responses
                        if hasattr(part, 'function_response') and part.function_response:
                            fr = part.function_response
                            emit("tool_result", f"{fr.name}: {fr.response}")
                        # Capture text response
                        if hasattr(part, 'text') and part.text:
                            result_text += part.text

        await asyncio.wait_for(run_with_timeout(), timeout=10.0)
        return result_text if result_text else "Done."
    except asyncio.TimeoutError:
        return "Timeout - please try again."
    except Exception as e:
        return f"Error: {e}"

# ============================================================
# AIModeSession - Unified Push-to-Talk Voice Control
# ============================================================

class AIModeSession(QObject):
    """Unified voice control: ADK agent (Gemini 3) + STT/TTS (Gemini 2.5).

    Pipeline: Mic → STT → ADK Agent → TTS → Speaker
    UI: Push-to-talk (hold to record, release to process)
    """

    # Qt signals for cross-thread UI updates
    state_changed = pyqtSignal(str)  # "ready", "listening", "thinking", "speaking"
    transcript_received = pyqtSignal(str, str)  # role, text
    error_occurred = pyqtSignal(str)  # error message

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = "ready"
        self._audio_buffer = []
        self._recording = False
        self._pyaudio = None
        self._stream = None
        self._stop_event = threading.Event()
        self._record_thread = None

    def initialize(self) -> bool:
        """Initialize API and audio."""
        global _genai_client
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("ERROR: GOOGLE_API_KEY or GEMINI_API_KEY not found in .env")
            return False
        try:
            # Initialize Google Gen AI client
            _genai_client = genai.Client(api_key=api_key)
            import pyaudio
            self._pyaudio = pyaudio.PyAudio()
            return True
        except Exception as e:
            print(f"Failed to initialize AI Mode: {e}")
            return False

    def start_listening(self):
        """[FIX #1] Start recording audio when button pressed."""
        if self.state != "ready":
            return
        self._set_state("listening")
        self._audio_buffer = []
        self._recording = True
        self._stop_event.clear()
        self._record_thread = threading.Thread(target=self._record_audio, daemon=True)
        self._record_thread.start()

    def stop_listening(self):
        """[FIX #1] Stop recording and process when button released."""
        if self.state != "listening":
            return
        self._stop_event.set()
        self._recording = False
        if self._record_thread:
            self._record_thread.join(timeout=1.0)
        self._set_state("thinking")
        threading.Thread(target=self._process_audio, daemon=True).start()

    def _set_state(self, state: str):
        self.state = state
        self.state_changed.emit(state)  # [FIX #3] Qt signal (thread-safe)

    def _record_audio(self):
        """Record audio until stop event is set."""
        stream = None
        try:
            import pyaudio
            stream = self._pyaudio.open(
                format=pyaudio.paInt16,  # 16-bit audio
                channels=AUDIO_CHANNELS,
                rate=AUDIO_SAMPLE_RATE,
                input=True,
                frames_per_buffer=1024
            )
            self._stream = stream
            while not self._stop_event.is_set():
                self._audio_buffer.append(stream.read(1024, exception_on_overflow=False))
        except Exception as e:
            print(f"Audio recording error: {e}")
            self._set_state("ready")
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            self._stream = None

    def _emit_transcript(self, role: str, text: str):
        """Thread-safe emit of transcript messages."""
        self.transcript_received.emit(role, text)

    def _process_audio(self):
        """Sequential API calls: STT → ADK Agent → TTS.

        Pipeline:
        1. Convert PCM to WAV (Gemini needs container format)
        2. STT: Gemini 2.5 Flash transcribes audio
        3. Agent: ADK with Gemini 3 Flash processes command (with full logging)
        4. TTS: Gemini 2.5 Flash TTS speaks response

        All messages are emitted to transcript including:
        - User speech transcription
        - Environment context (sensors, camera)
        - Tool calls and results
        - Final robot response
        """
        try:
            if not self._audio_buffer:
                self._set_state("ready")
                return

            # Convert raw PCM to WAV format for Gemini API
            pcm_bytes = b''.join(self._audio_buffer)
            wav_bytes = _pcm_to_wav(pcm_bytes)

            # Step 1: STT - Transcribe audio with Gemini 2.0 Flash
            stt_response = _genai_client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[
                    "Transcribe this audio exactly. Return only the transcription.",
                    types.Part.from_bytes(data=wav_bytes, mime_type="audio/wav")
                ]
            )
            user_text = stt_response.text.strip()
            if not user_text:
                self._set_state("ready")
                return
            self.transcript_received.emit("user", user_text)

            # Step 2: ADK Agent - Process command (Gemini 3 Flash)
            # Pass callback to emit all conversation events
            response_text = asyncio.run(
                robot_command(user_text, emit_callback=self._emit_transcript)
            )
            self.transcript_received.emit("robot", response_text)

            # Step 3: TTS - Speak response with Gemini 2.5 Flash TTS
            self._set_state("speaking")
            self._speak_with_gemini(response_text)

            self._set_state("ready")
        except Exception as e:
            print(f"Processing error: {e}")
            self.error_occurred.emit(str(e))
            self._set_state("ready")

    def _speak_with_gemini(self, text: str):
        """Convert text to speech using Gemini 2.5 Flash TTS and play it."""
        try:
            import pyaudio

            # Generate audio with Gemini TTS
            tts_response = _genai_client.models.generate_content(
                model=TTS_MODEL,
                contents=text,
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

            # Validate response (may be empty or safety-blocked)
            if not tts_response.candidates:
                print("TTS: No candidates returned")
                return
            if not tts_response.candidates[0].content or not tts_response.candidates[0].content.parts:
                print("TTS: Empty or blocked response")
                return

            # Extract audio data (24kHz PCM)
            audio_data = tts_response.candidates[0].content.parts[0].inline_data.data

            # Play audio
            stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=AUDIO_CHANNELS,
                rate=AUDIO_OUTPUT_RATE,
                output=True
            )
            stream.write(audio_data)
            stream.stop_stream()
            stream.close()

        except Exception as e:
            print(f"TTS error: {e}")
            # Fallback: just print the response
            self.error_occurred.emit(f"TTS failed: {e}")

    def stop(self):
        """Stop AI Mode and cleanup."""
        self._stop_event.set()
        self._recording = False
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self._set_state("ready")
        if self._pyaudio:
            self._pyaudio.terminate()
