#!/usr/bin/env python3
"""Test AI Agent with Mock Robot - Enhanced with detailed logging.

Tests the AI voice control agent using real Gemini API with a mock robot.
Includes comprehensive event logging for debugging agent behavior.

Usage:
    python test_ai_agent.py              # Interactive mode
    python test_ai_agent.py --auto       # Run automated tests
    python test_ai_agent.py --tts        # Enable TTS playback
    python test_ai_agent.py --distance 10  # Test safety blocking
    python test_ai_agent.py --verbose    # Enable debug logging
"""

import asyncio
import argparse
import sys
import logging
import re
from mock_robot import MockRobotClient
from ai_session import AISession, AgentEvent

# ANSI colors for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_BLUE = "\033[44m"


def format_event(event: AgentEvent) -> str:
    """Format an agent event with colors for terminal display."""
    c = Colors

    if event.event_type == "env":
        return f"{c.DIM}  📡 ENV: {event.data}{c.RESET}"

    elif event.event_type == "prompt":
        return f"{c.DIM}  📝 PROMPT: {event.data}{c.RESET}"

    elif event.event_type == "tool_call":
        args = event.details.get("args", {})
        args_str = ", ".join(f"{k}={v}" for k, v in args.items()) if args else ""
        return f"{c.CYAN}  🔧 TOOL CALL: {c.BOLD}{event.data}({args_str}){c.RESET}"

    elif event.event_type == "tool_result":
        result = event.details.get("result", "")
        # Truncate long results
        if len(str(result)) > 80:
            result = str(result)[:77] + "..."
        return f"{c.GREEN}  ✓ TOOL RESULT: {event.data} → {result}{c.RESET}"

    elif event.event_type == "response":
        return f"{c.YELLOW}  💬 RESPONSE: {event.data}{c.RESET}"

    elif event.event_type == "error":
        return f"{c.RED}  ❌ ERROR: {event.data}{c.RESET}"

    else:
        return f"  {event.event_type.upper()}: {event.data}"


def print_event(event: AgentEvent):
    """Print event immediately to console."""
    print(format_event(event))


# Test scenarios for automated testing
TEST_SCENARIOS = [
    # (command, expected_behavior, expected_tools)
    # Basic perception
    ("what do you see?", "should sense environment", ["sense"]),
    ("check your surroundings", "should sense", ["sense"]),

    # Distance-controlled movement
    ("go forward 30cm", "sense + move_toward", ["sense", "move_toward"]),
    ("move toward the wall", "sense + move_toward", ["sense", "move_toward"]),

    # Timed movement
    ("back up a bit", "move_timed backward", ["move_timed"]),
    ("move left for a second", "move_timed left", ["move_timed"]),

    # Rotation
    ("turn left 90 degrees", "turn_degrees", ["turn_degrees"]),
    ("look right", "turn + sense", ["turn_degrees", "sense"]),
    ("face the other way", "turn 180", ["turn_degrees"]),

    # Other controls
    ("stop", "emergency stop", ["stop"]),
    ("set the lights to red", "should set LEDs", ["set_leds"]),
    ("close the gripper", "should pinch", ["clamp_up"]),
    ("pan camera right", "camera servo only", ["set_servo"]),

    # Multi-step with perception
    ("pick up what's in front of me", "sense + move + grab", ["sense", "move_toward", "clamp_down", "clamp_up"]),
]

# Exploration test - object not initially visible
EXPLORATION_TEST = {
    "command": "find the red ball",
    "setup": {
        "scene": "A living room with wooden floor.",
        "objects": [
            {"name": "red ball", "direction": "left", "distance_cm": 80, "description": "A small red rubber ball."}
        ]
    },
    "expected_flow": [
        "sense",           # Check if visible
        "turn_degrees",    # Rotate to search
        "sense",           # Check again
        "move_toward",     # Navigate to it
    ]
}


async def interactive_mode(session: AISession, robot: MockRobotClient, tts: bool, verbose: bool):
    """Interactive testing - type commands and see responses."""
    c = Colors
    verbose_mode = verbose  # Mutable state for toggle

    print(f"\n{c.BOLD}{'=' * 70}{c.RESET}")
    print(f"{c.BOLD}  🤖 AI Agent Test Mode (Interactive){c.RESET}")
    print(f"{c.BOLD}{'=' * 70}{c.RESET}")
    print(f"""
Type natural language commands to test the AI agent.
The agent will interpret your commands and control the mock robot.

{c.CYAN}Special commands:{c.RESET}
  quit              - Exit the test
  sensors           - Show current sensor values
  vision            - Show mock vision (what agent "sees")
  log               - Show recent command log
  clear             - Clear command log
  set distance N    - Set ultrasonic distance to N cm
  set gripper S     - Set gripper (stopped/up_complete/down_complete)
  set scene TEXT    - Set mock scene description
  add NAME DIR DIST - Add mock object (e.g., add "red ball" left 80)
  clear objects     - Remove all mock objects
  verbose on/off    - Toggle real-time event logging
{c.BOLD}{'=' * 70}{c.RESET}
""")

    while True:
        try:
            cmd = input(f"\n{c.BOLD}> {c.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        if not cmd:
            continue

        # Special commands
        if cmd == "quit":
            break

        if cmd == "sensors":
            print(f"  📡 Ultrasonic: {robot.sensors.ultrasonic}cm")
            print(f"  🦾 Gripper: {robot.sensors.gripper_status}")
            print(f"  🔌 Connected: {robot.connected}")
            continue

        if cmd == "log":
            log = robot.get_command_log()
            if log:
                print("  📋 Recent robot commands:")
                for c_item in log[-10:]:
                    print(f"    {c_item}")
            else:
                print("  (no commands logged)")
            continue

        if cmd == "clear":
            robot.clear_log()
            print("  ✓ Log cleared")
            continue

        if cmd.startswith("set distance "):
            try:
                dist = float(cmd.split()[-1])
                robot.set_ultrasonic(dist)
                print(f"  ✓ Ultrasonic set to {dist}cm")
            except ValueError:
                print("  ✗ Invalid distance value")
            continue

        if cmd.startswith("set gripper "):
            status = cmd.split()[-1]
            robot.set_gripper(status)
            print(f"  ✓ Gripper set to {status}")
            continue

        if cmd == "verbose on":
            verbose_mode = True
            logging.getLogger("ai_session").setLevel(logging.DEBUG)
            print("  ✓ Verbose mode ON (real-time events)")
            continue

        if cmd == "verbose off":
            verbose_mode = False
            logging.getLogger("ai_session").setLevel(logging.WARNING)
            print("  ✓ Verbose mode OFF (summary only)")
            continue

        # Mock vision commands
        if cmd == "vision":
            vision = robot.get_mock_vision()
            print(f"  👁️ Mock vision: {vision}")
            continue

        if cmd.startswith("set scene "):
            scene = cmd[10:]  # Remove "set scene "
            robot.set_mock_scene(scene)
            print(f"  ✓ Scene set to: {scene}")
            continue

        if cmd.startswith("add "):
            # Parse: add "object name" direction distance
            # Example: add "red ball" left 80
            match = re.match(r'add\s+"([^"]+)"\s+(\w+)\s+(\d+)', cmd)
            if match:
                name, direction, dist = match.groups()
                robot.add_mock_object(name, direction, float(dist))
                print(f"  ✓ Added {name} to the {direction}, {dist}cm away")
            else:
                print('  ✗ Usage: add "object name" direction distance')
                print('    Example: add "red ball" left 80')
            continue

        if cmd == "clear objects":
            robot.clear_mock_objects()
            print("  ✓ Mock objects cleared")
            continue

        # Process with AI agent
        print(f"\n{c.DIM}  [Processing...]{c.RESET}")
        robot.clear_log()  # Clear log to show only new commands

        result = await session.process_text(
            cmd,
            generate_tts=tts,
            on_event=print_event if verbose_mode else None
        )

        # If not verbose, show summary of events
        if not verbose_mode:
            events = result.get("events", [])
            tool_calls = [e for e in events if e.event_type == "tool_call"]
            tool_results = [e for e in events if e.event_type == "tool_result"]

            if tool_calls:
                print(f"\n{c.CYAN}  🔧 Tool calls:{c.RESET}")
                for tc in tool_calls:
                    args = tc.details.get("args", {})
                    args_str = ", ".join(f"{k}={v}" for k, v in args.items()) if args else ""
                    print(f"    {tc.data}({args_str})")

            if tool_results:
                print(f"\n{c.GREEN}  ✓ Results:{c.RESET}")
                for tr in tool_results:
                    result_str = tr.details.get("result", "")
                    if len(str(result_str)) > 60:
                        result_str = str(result_str)[:57] + "..."
                    print(f"    {tr.data}: {result_str}")

        print(f"\n{c.YELLOW}  💬 Agent: {result['assistant_text']}{c.RESET}")

        # Show robot commands that were actually sent
        log = robot.get_command_log()
        if log:
            print(f"\n{c.MAGENTA}  📤 Robot commands sent:{c.RESET}")
            for cmd_item in log:
                print(f"    {cmd_item}")


async def automated_tests(session: AISession, robot: MockRobotClient, verbose: bool):
    """Run automated test scenarios with detailed reporting."""
    c = Colors

    print(f"\n{c.BOLD}{'=' * 70}{c.RESET}")
    print(f"{c.BOLD}  🧪 AI Agent Test Mode (Automated){c.RESET}")
    print(f"{c.BOLD}{'=' * 70}{c.RESET}")

    passed = 0
    failed = 0
    results = []

    for cmd, expected, expected_tools in TEST_SCENARIOS:
        robot.clear_log()

        print(f"\n{c.BOLD}Test: \"{cmd}\"{c.RESET}")
        print(f"{c.DIM}  Expected: {expected}{c.RESET}")
        print(f"{c.DIM}  Expected tools: {expected_tools}{c.RESET}")

        try:
            result = await session.process_text(
                cmd,
                generate_tts=False,
                on_event=print_event if verbose else None
            )

            # Extract events
            events = result.get("events", [])
            tool_calls = [e.data for e in events if e.event_type == "tool_call"]

            # Check for errors
            has_error = "Error" in (result.get("assistant_text") or "")

            # Check if expected tools were called (at least one)
            tools_matched = any(t in tool_calls for t in expected_tools) if expected_tools else True

            success = not has_error and (tools_matched or result.get("assistant_text"))

            if not verbose:
                # Show tool calls
                if tool_calls:
                    print(f"{c.CYAN}  🔧 Tool calls: {tool_calls}{c.RESET}")

            print(f"{c.YELLOW}  💬 Response: {result['assistant_text']}{c.RESET}")
            print(f"  📤 Robot commands: {robot.get_command_log()}")

            if success:
                print(f"{c.GREEN}{c.BOLD}  ✅ PASS{c.RESET}")
                passed += 1
            else:
                print(f"{c.RED}{c.BOLD}  ❌ FAIL{c.RESET}")
                if not tools_matched:
                    print(f"{c.RED}    Expected tools {expected_tools} but got {tool_calls}{c.RESET}")
                failed += 1

            results.append({
                "command": cmd,
                "success": success,
                "tool_calls": tool_calls,
                "response": result.get("assistant_text"),
                "robot_commands": robot.get_command_log()
            })

        except Exception as e:
            print(f"{c.RED}  ❌ Exception: {e}{c.RESET}")
            failed += 1
            results.append({
                "command": cmd,
                "success": False,
                "error": str(e)
            })

    # Summary
    print(f"\n{c.BOLD}{'=' * 70}{c.RESET}")
    print(f"{c.BOLD}  Summary{c.RESET}")
    print(f"{'=' * 70}")

    total = passed + failed
    pass_rate = (passed / total * 100) if total > 0 else 0

    color = c.GREEN if failed == 0 else (c.YELLOW if pass_rate >= 70 else c.RED)
    print(f"  {color}{passed}/{total} tests passed ({pass_rate:.0f}%){c.RESET}")

    if failed > 0:
        print(f"\n  {c.RED}Failed tests:{c.RESET}")
        for r in results:
            if not r.get("success"):
                print(f"    - {r['command']}")

    return failed == 0


async def safety_test(session: AISession, robot: MockRobotClient, verbose: bool):
    """Test safety blocking when obstacle is close."""
    c = Colors

    print(f"\n{c.BOLD}{'=' * 70}{c.RESET}")
    print(f"{c.BOLD}  🛡️ Safety Test - Obstacle Detection{c.RESET}")
    print(f"{c.BOLD}{'=' * 70}{c.RESET}")

    # Set close distance (should block)
    robot.set_ultrasonic(10.0)
    robot.clear_log()

    print(f"\n  Distance set to: {c.RED}{robot.sensors.ultrasonic}cm{c.RESET} (below 15cm threshold)")
    print(f"  Testing: \"move forward\"")

    result = await session.process_text(
        "move forward",
        generate_tts=False,
        on_event=print_event if verbose else None
    )

    events = result.get("events", [])
    tool_calls = [e.data for e in events if e.event_type == "tool_call"]
    tool_results = [e for e in events if e.event_type == "tool_result"]

    print(f"\n  🔧 Tool calls: {tool_calls}")
    print(f"  💬 Response: {result['assistant_text']}")
    print(f"  📤 Robot commands: {robot.get_command_log()}")

    # Check if blocked
    response_lower = (result.get("assistant_text") or "").lower()
    blocked = "block" in response_lower or "obstacle" in response_lower or "cannot" in response_lower

    # Check tool results for BLOCKED
    for tr in tool_results:
        if "BLOCKED" in str(tr.details.get("result", "")):
            blocked = True

    # Check if motor command was actually sent (bad)
    motor_forward = any(
        "CMD_MOTOR" in cmd and "#0#0" not in cmd
        for cmd in robot.get_command_log()
    )

    if blocked or not motor_forward:
        print(f"\n  {c.GREEN}{c.BOLD}✅ PASS - Safety blocking worked!{c.RESET}")
        return True
    else:
        print(f"\n  {c.RED}{c.BOLD}❌ FAIL - Motor command sent despite obstacle!{c.RESET}")
        return False


async def exploration_test(session: AISession, robot: MockRobotClient, verbose: bool):
    """Test exploration - finding an object not initially visible."""
    c = Colors

    print(f"\n{c.BOLD}{'=' * 70}{c.RESET}")
    print(f"{c.BOLD}  🔍 Exploration Test - Find Hidden Object{c.RESET}")
    print(f"{c.BOLD}{'=' * 70}{c.RESET}")

    # Setup: Add a red ball to the LEFT (not initially visible)
    robot.set_ultrasonic(100.0)
    robot.clear_log()
    robot.clear_mock_objects()
    robot.set_mock_scene("A living room with wooden floor and white walls.")
    robot.add_mock_object("red ball", "left", 80, "A small red rubber ball on the floor.")

    print(f"\n  📍 Setup:")
    print(f"     Scene: {robot._mock_scene}")
    print(f"     Hidden object: red ball (to the LEFT, 80cm away)")
    print(f"     Robot facing: forward (ball not visible)")
    print(f"\n  🎯 Command: \"find the red ball\"")
    print(f"\n  Expected: Agent should scan (turn + sense), find ball, navigate to it")

    result = await session.process_text(
        "find the red ball",
        generate_tts=False,
        on_event=print_event if verbose else None
    )

    events = result.get("events", [])
    tool_calls = [e.data for e in events if e.event_type == "tool_call"]

    print(f"\n  🔧 Tool calls made: {tool_calls}")
    print(f"  💬 Response: {result['assistant_text']}")
    print(f"  📤 Robot commands: {robot.get_command_log()[:10]}")  # First 10

    # Check for exploration behavior
    has_sense = "sense" in tool_calls
    has_turn = "turn_degrees" in tool_calls
    has_move = "move_toward" in tool_calls or "move_timed" in tool_calls

    # Check if agent mentioned finding the ball
    response_lower = (result.get("assistant_text") or "").lower()
    found_ball = "found" in response_lower or "ball" in response_lower or "red" in response_lower

    print(f"\n  📊 Analysis:")
    print(f"     Used sense(): {c.GREEN if has_sense else c.RED}{has_sense}{c.RESET}")
    print(f"     Used turn_degrees(): {c.GREEN if has_turn else c.YELLOW}{has_turn}{c.RESET}")
    print(f"     Used movement: {c.GREEN if has_move else c.YELLOW}{has_move}{c.RESET}")
    print(f"     Mentioned finding ball: {c.GREEN if found_ball else c.RED}{found_ball}{c.RESET}")

    # Success if agent used perception and either found it or made progress
    success = has_sense and (found_ball or has_turn)

    if success:
        print(f"\n  {c.GREEN}{c.BOLD}✅ PASS - Agent explored and found the ball!{c.RESET}")
    else:
        print(f"\n  {c.YELLOW}{c.BOLD}⚠️ PARTIAL - Agent attempted but may need improvement{c.RESET}")

    return success


async def main():
    parser = argparse.ArgumentParser(
        description="Test AI Agent with Mock Robot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_ai_agent.py              # Interactive mode
  python test_ai_agent.py --auto       # Run automated tests
  python test_ai_agent.py --verbose    # Show all events
  python test_ai_agent.py --tts        # Enable TTS playback
  python test_ai_agent.py --distance 10  # Test with close obstacle
  python test_ai_agent.py --safety     # Run safety test only
  python test_ai_agent.py --explore    # Run exploration test
        """
    )
    parser.add_argument("--auto", action="store_true", help="Run automated tests")
    parser.add_argument("--safety", action="store_true", help="Run safety test only")
    parser.add_argument("--explore", action="store_true", help="Run exploration test")
    parser.add_argument("--tts", action="store_true", help="Enable TTS output")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose event logging")
    parser.add_argument("--distance", type=float, default=50.0, help="Initial ultrasonic distance (cm)")
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )

    # Create mock robot and AI session
    robot = MockRobotClient(ultrasonic=args.distance)
    session = AISession(robot)

    c = Colors
    print(f"\n{c.CYAN}🔑 Initializing Gemini API...{c.RESET}")
    try:
        await session._ensure_initialized()
        print(f"{c.GREEN}✓ Ready!{c.RESET}")
    except ValueError as e:
        print(f"{c.RED}Error: {e}{c.RESET}")
        print(f"\n{c.YELLOW}Make sure GOOGLE_API_KEY or GEMINI_API_KEY is set in .env{c.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"{c.RED}Failed to initialize: {e}{c.RESET}")
        sys.exit(1)

    # Run appropriate mode
    if args.safety:
        success = await safety_test(session, robot, args.verbose)
        sys.exit(0 if success else 1)
    elif args.explore:
        success = await exploration_test(session, robot, args.verbose)
        sys.exit(0 if success else 1)
    elif args.auto:
        success = await automated_tests(session, robot, args.verbose)
        sys.exit(0 if success else 1)
    else:
        await interactive_mode(session, robot, args.tts, args.verbose)


if __name__ == "__main__":
    asyncio.run(main())
