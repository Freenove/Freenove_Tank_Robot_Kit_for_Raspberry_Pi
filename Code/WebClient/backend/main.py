"""
FastAPI Backend for Tank Robot Web Client

REST endpoints for robot control + WebSocket for video/sensors/AI
"""

import asyncio
import json
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from robot_client import robot


# === Pydantic Models ===

class ConnectRequest(BaseModel):
    ip: str


class MotorRequest(BaseModel):
    left: int
    right: int


class ServoRequest(BaseModel):
    channel: int
    angle: int


class LEDRequest(BaseModel):
    mode: int = 1
    r: int = 255
    g: int = 255
    b: int = 255
    mask: int = 15


class ModeRequest(BaseModel):
    mode: int


class GripperRequest(BaseModel):
    action: int


# === WebSocket Connection Manager ===

class ConnectionManager:
    def __init__(self):
        self.sensor_connections: list[WebSocket] = []
        self.video_connections: list[WebSocket] = []

    async def connect_sensors(self, websocket: WebSocket):
        await websocket.accept()
        self.sensor_connections.append(websocket)

    async def connect_video(self, websocket: WebSocket):
        await websocket.accept()
        self.video_connections.append(websocket)

    def disconnect_sensors(self, websocket: WebSocket):
        if websocket in self.sensor_connections:
            self.sensor_connections.remove(websocket)

    def disconnect_video(self, websocket: WebSocket):
        if websocket in self.video_connections:
            self.video_connections.remove(websocket)

    async def broadcast_sensor(self, data: dict):
        """Broadcast sensor data to all connected clients."""
        message = json.dumps(data)
        for connection in self.sensor_connections[:]:
            try:
                await connection.send_text(message)
            except:
                self.sensor_connections.remove(connection)


manager = ConnectionManager()


# === Sensor Callback ===

# Global reference to the event loop for cross-thread communication
_main_loop: Optional[asyncio.AbstractEventLoop] = None


def on_sensor_update(sensor_type: str, value):
    """Called when robot sends sensor data (from recv_loop thread)."""
    if _main_loop is None:
        return

    # Schedule the coroutine on the main event loop from this thread
    asyncio.run_coroutine_threadsafe(
        manager.broadcast_sensor({
            "type": sensor_type,
            "value": value
        }),
        _main_loop
    )


# === App Lifecycle ===

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _main_loop
    # Startup: Capture event loop and register sensor callback
    _main_loop = asyncio.get_running_loop()
    robot.add_sensor_callback(on_sensor_update)
    yield
    # Shutdown: Disconnect from robot
    _main_loop = None
    robot.disconnect()


# === FastAPI App ===

app = FastAPI(
    title="Tank Robot API",
    description="Control the Freenove Tank Robot via REST and WebSocket",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === REST Endpoints ===

@app.get("/api/status")
async def get_status():
    """Get connection status."""
    return {
        "connected": robot.connected,
        "ip": robot.ip,
        "sensors": {
            "ultrasonic": robot.sensors.ultrasonic,
            "gripper": robot.sensors.gripper_status
        }
    }


@app.post("/api/connect")
async def connect(request: ConnectRequest):
    """Connect to robot."""
    success = robot.connect(request.ip)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to connect to robot")
    return {"connected": True, "ip": request.ip}


@app.post("/api/disconnect")
async def disconnect():
    """Disconnect from robot."""
    robot.disconnect()
    return {"connected": False}


@app.post("/api/motor")
async def set_motor(request: MotorRequest):
    """Set motor speeds."""
    if not robot.connected:
        raise HTTPException(status_code=400, detail="Not connected to robot")
    robot.motor(request.left, request.right)
    return {"left": request.left, "right": request.right}


@app.post("/api/stop")
async def stop_motors():
    """Stop all motors."""
    if not robot.connected:
        raise HTTPException(status_code=400, detail="Not connected to robot")
    robot.stop()
    return {"stopped": True}


@app.post("/api/servo")
async def set_servo(request: ServoRequest):
    """Set servo angle."""
    if not robot.connected:
        raise HTTPException(status_code=400, detail="Not connected to robot")
    robot.servo(request.channel, request.angle)
    return {"channel": request.channel, "angle": request.angle}


@app.post("/api/servo/home")
async def servo_home():
    """Reset servos to home position."""
    if not robot.connected:
        raise HTTPException(status_code=400, detail="Not connected to robot")
    robot.servo(0, 90)  # Pan center
    robot.servo(1, 140)  # Tilt up
    return {"pan": 90, "tilt": 140}


@app.post("/api/led")
async def set_led(request: LEDRequest):
    """Set LED color."""
    if not robot.connected:
        raise HTTPException(status_code=400, detail="Not connected to robot")
    robot.led(request.mode, request.r, request.g, request.b, request.mask)
    return request.model_dump()


@app.post("/api/led/mode")
async def set_led_mode(request: ModeRequest):
    """Set LED animation mode."""
    if not robot.connected:
        raise HTTPException(status_code=400, detail="Not connected to robot")
    robot.led_mode(request.mode)
    return {"mode": request.mode}


@app.post("/api/mode")
async def set_robot_mode(request: ModeRequest):
    """Set robot mode (0=free, 1=sonic, 2=line)."""
    if not robot.connected:
        raise HTTPException(status_code=400, detail="Not connected to robot")
    robot.set_mode(request.mode)
    return {"mode": request.mode}


@app.post("/api/gripper")
async def control_gripper(request: GripperRequest):
    """Control gripper (0=stop, 1=up, 2=down)."""
    if not robot.connected:
        raise HTTPException(status_code=400, detail="Not connected to robot")
    robot.gripper(request.action)
    return {"action": request.action}


@app.get("/api/ultrasonic")
async def get_ultrasonic():
    """Get ultrasonic distance (also triggers request)."""
    if not robot.connected:
        raise HTTPException(status_code=400, detail="Not connected to robot")
    robot.request_ultrasonic()
    return {"distance": robot.sensors.ultrasonic}


# === WebSocket Endpoints ===

@app.websocket("/ws/video")
async def video_websocket(websocket: WebSocket):
    """Stream video frames as binary WebSocket messages."""
    await manager.connect_video(websocket)

    if not robot.connected:
        await websocket.close(code=1008, reason="Not connected to robot")
        return

    # Start video if not already running
    if not robot.start_video():
        await websocket.close(code=1011, reason="Failed to start video stream")
        return

    try:
        async for frame in robot.video_frames():
            await websocket.send_bytes(frame)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Video WebSocket error: {e}")
    finally:
        manager.disconnect_video(websocket)
        # Only stop video if no other clients
        if not manager.video_connections:
            robot.stop_video()


@app.websocket("/ws/sensors")
async def sensors_websocket(websocket: WebSocket):
    """Stream sensor updates as JSON."""
    await manager.connect_sensors(websocket)

    try:
        # Send initial sensor state
        await websocket.send_json({
            "type": "initial",
            "ultrasonic": robot.sensors.ultrasonic,
            "gripper": robot.sensors.gripper_status,
            "connected": robot.connected
        })

        # Keep connection alive, receive any client messages
        while True:
            try:
                # Wait for messages (like ultrasonic request)
                # Use longer timeout (60s) to reduce unnecessary pings
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                msg = json.loads(data)

                if msg.get("type") == "request_ultrasonic":
                    robot.request_ultrasonic()

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    # Connection lost, exit loop
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Sensor WebSocket error: {e}")
    finally:
        manager.disconnect_sensors(websocket)


# === AI Mode WebSocket ===

@app.websocket("/ws/ai")
async def ai_websocket(websocket: WebSocket):
    """AI voice control WebSocket."""
    await websocket.accept()

    try:
        # Import AI session lazily
        try:
            from ai_session import AISession
            session = AISession(robot)
        except ImportError as e:
            await websocket.send_json({
                "type": "error",
                "message": f"AI mode not available: {e}"
            })
            await websocket.close()
            return

        await websocket.send_json({"type": "state", "state": "idle"})

        while True:
            data = await websocket.receive_json()

            if data.get("type") == "start_listening":
                await websocket.send_json({"type": "state", "state": "listening"})

            elif data.get("type") == "audio":
                await websocket.send_json({"type": "state", "state": "thinking"})

                # Process audio with AI
                try:
                    result = await session.process_audio(data["data"])

                    # Send transcript
                    if result.get("user_text"):
                        await websocket.send_json({
                            "type": "transcript",
                            "role": "user",
                            "text": result["user_text"]
                        })

                    if result.get("assistant_text"):
                        await websocket.send_json({
                            "type": "transcript",
                            "role": "assistant",
                            "text": result["assistant_text"]
                        })

                    # Send TTS audio if available
                    if result.get("audio"):
                        await websocket.send_json({"type": "state", "state": "speaking"})
                        await websocket.send_json({
                            "type": "audio",
                            "data": result["audio"]
                        })

                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })

                await websocket.send_json({"type": "state", "state": "idle"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"AI WebSocket error: {e}")


# === Run Server ===

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
