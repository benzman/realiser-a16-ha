#!/usr/bin/env python3
"""Test speaker visibility and status commands (0xAE and 0xAF)."""

import time
import sys
import os

# Determine the path to custom_components
script_dir = os.path.dirname(os.path.abspath(__file__))
custom_components_path = os.path.join(script_dir, "custom_components")
sys.path.insert(0, custom_components_path)

from realiser_a16.realiser_a16_hex import RealiserA16Hex

SPEAKER_NAMES = RealiserA16Hex.SPEAKER_NAMES


def test_speaker_commands(host, port):
    """Test 0xAE (visibility) and 0xAF (status) commands."""
    print(f"=== Realiser A16 Speaker Command Test ===")
    print(f"Connecting to {host}:{port}...")

    try:
        with RealiserA16Hex(host, port, timeout=10.0) as client:
            print("✓ Connected!\n")

            # Test 0xAE - Speaker Visibility
            print("--- Testing 0xAE (Speaker Visibility) ---")
            try:
                vis_response = client.send(0xAE)
                print(f"Raw response: {repr(vis_response[:200])}")
                print(f"Length: {len(vis_response)} bytes\n")

                tokens = vis_response.replace("\r", "").replace("\n", "").split(",")
                visible_count = sum(1 for t in tokens if t and t[-1] == "1")
                print(f"Visible speakers: {visible_count}\n")

            except Exception as e:
                print(f"✗ 0xAE failed: {e}\n")
                return

            time.sleep(0.5)

            # Test 0xAF - Speaker Status
            print("--- Testing 0xAF (Speaker Status) ---")
            try:
                status_response = client.send(0xAF)
                print(f"Raw response: {repr(status_response[:200])}")
                print(f"Length: {len(status_response)} bytes\n")

                tokens = status_response.replace("\r", "").replace("\n", "").split(",")
                active_count = sum(1 for t in tokens if t and t[-1] == "1")
                print(f"Active (soloed) speakers: {active_count}\n")

            except Exception as e:
                print(f"✗ 0xAF failed: {e}\n")
                return

            # Show detailed mapping for first 20 speakers
            print("--- Speaker Mapping (IDs 1-20) ---")
            vis_tokens = vis_response.replace("\r", "").replace("\n", "").split(",")
            status_tokens = (
                status_response.replace("\r", "").replace("\n", "").split(",")
            )

            for i in range(1, 21):
                idx = i - 1
                vis = vis_tokens[idx] if idx < len(vis_tokens) else ""
                st = status_tokens[idx] if idx < len(status_tokens) else ""
                name = SPEAKER_NAMES.get(i, f"Spk{i}")
                vis_flag = vis[-1:] if vis else "?"
                st_flag = st[-1:] if st else "?"
                print(f"ID {i:2d} ({name:4s}): Vis={vis_flag}  Stat={st_flag}")

            print("\n✓ Test completed successfully!")

    except Exception as e:
        print(f"✗ Connection failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # CHANGE THESE to your A16 IP and port
    HOST = "192.168.160.19"  # Your A16 IP address
    PORT = 4101  # Your A16 port (default 4101)

    print("NOTE: Make sure your Realiser A16 has TCP Command Server ENABLED!")
    print(f"Using HOST={HOST}, PORT={PORT}\n")

    test_speaker_commands(HOST, PORT)
