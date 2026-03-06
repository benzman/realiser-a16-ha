#!/usr/bin/env python3
"""
Realiser A16 TCP Remote using the official IP Command Protocol
Based on: A16-IP-command-server-May-2020-1.pdf

Protokoll:
- Send: 2-digit hex code + "\r\n"
- Receive: ASCII string + "\x00"
"""

import logging
import socket
from typing import Union, Optional

_LOGGER = logging.getLogger(__name__)


class RealiserA16Hex:
    """Simple TCP client for official A16 IP command protocol"""

    # Command codes from commands.md and legacy
    # Input selection
    CMD_SOURCE_EARC = 0x20
    CMD_SOURCE_HDMI1 = 0x21
    CMD_SOURCE_HDMI2 = 0x22
    CMD_SOURCE_HDMI3 = 0x23
    CMD_SOURCE_HDMI4 = 0x24
    CMD_SOURCE_USB = 0x25
    CMD_SOURCE_LINE = 0x26
    CMD_SOURCE_STEREO = 0x27
    CMD_SOURCE_COAXIAL = 0x28
    CMD_SOURCE_OPTICAL = 0x29

    # Power
    CMD_POWER_ON = 0x2C
    CMD_POWER_OFF = 0x2D
    CMD_POWER_STATUS = 0x2E

    # Zone selection
    CMD_ZONE_A = 0x06
    CMD_ZONE_B = 0x07

    # Volume User A (Table 1: #41-42)
    CMD_VOL_A_UP = 0x30  # A vol+  → VA=27-99
    CMD_VOL_A_DN = 0x31  # A vol-  → VA=27-99
    CMD_MUTE_A = 0x32  # Mute A  → MUTEA=MUTE or MUTEA=OFF
    # Volume User B (Table 1: #43-46)
    CMD_VOL_B_UP = 0x33  # B vol+  → VB=27-99
    CMD_VOL_B_DN = 0x34  # B vol-  → VB=27-99
    CMD_MUTE_B = 0x35  # Mute B  → MUTEB=MUTE or MUTEB=OFF

    # Status queries
    CMD_GET_ASSIGNMENTS = 0x37
    CMD_RESET_LEVELS = 0x38
    CMD_GET_VERSION = 0x64

    # User A info (Table 2: #57) - VA, AUR, IN, ASPKR, ...
    CMD_USER_A_INFO = 0x80
    # User A volume only (Table 2: #60) - VA=27-99
    CMD_VOL_A_GET = 0x83

    # User B info (Table 2: #89) - VB, BUR, ...
    CMD_USER_B_INFO = 0xA0
    # User B volume only (Table 2: #92) - VB=27-99
    CMD_VOL_B_GET = 0xA3

    # Presets User A (0x70-0x7f = Preset 1-16)
    CMD_LOAD_PRESET_A1 = 0x70
    CMD_LOAD_PRESET_A2 = 0x71
    CMD_LOAD_PRESET_A3 = 0x72
    CMD_LOAD_PRESET_A4 = 0x73
    CMD_LOAD_PRESET_A5 = 0x74
    CMD_LOAD_PRESET_A6 = 0x75
    CMD_LOAD_PRESET_A7 = 0x76
    CMD_LOAD_PRESET_A8 = 0x77
    CMD_LOAD_PRESET_A9 = 0x78
    CMD_LOAD_PRESET_A10 = 0x79
    CMD_LOAD_PRESET_A11 = 0x7A
    CMD_LOAD_PRESET_A12 = 0x7B
    CMD_LOAD_PRESET_A13 = 0x7C
    CMD_LOAD_PRESET_A14 = 0x7D
    CMD_LOAD_PRESET_A15 = 0x7E
    CMD_LOAD_PRESET_A16 = 0x7F

    # Presets User B (0x90-0x9f = Preset 1-16)
    CMD_LOAD_PRESET_B1 = 0x90
    CMD_LOAD_PRESET_B2 = 0x91
    CMD_LOAD_PRESET_B3 = 0x92
    CMD_LOAD_PRESET_B4 = 0x93
    CMD_LOAD_PRESET_B5 = 0x94
    CMD_LOAD_PRESET_B6 = 0x95
    CMD_LOAD_PRESET_B7 = 0x96
    CMD_LOAD_PRESET_B8 = 0x97
    CMD_LOAD_PRESET_B9 = 0x98
    CMD_LOAD_PRESET_B10 = 0x99
    CMD_LOAD_PRESET_B11 = 0x9A
    CMD_LOAD_PRESET_B12 = 0x9B
    CMD_LOAD_PRESET_B13 = 0x9C
    CMD_LOAD_PRESET_B14 = 0x9D
    CMD_LOAD_PRESET_B15 = 0x9E
    CMD_LOAD_PRESET_B16 = 0x9F

    # Volume range per PDF
    VOLUME_MIN = 27
    VOLUME_MAX = 99

    def __init__(self, host: str, port: int = 4101, timeout: float = 30.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None

    def connect(self) -> None:
        """Open TCP connection to A16"""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self.timeout)
        self._sock.connect((self.host, self.port))

    def close(self) -> None:
        """Close TCP connection properly."""
        if self._sock:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def send(self, code: Union[int, str]) -> str:
        """
        Send a command and return response.

        Args:
            code: Hex command code (e.g. 0x37 or "37")

        Returns:
            Response string without null terminator
        """
        if not self._sock:
            raise RuntimeError("Not connected. Call connect() first.")

        if isinstance(code, int):
            cmd = f"{code:02x}\r\n"
        else:
            cmd = f"{code}\r\n"
            if len(code) != 2:
                raise ValueError("Hex code must be 2 digits")

        _LOGGER.debug("Sending: %s", repr(cmd))
        self._sock.sendall(cmd.encode("ascii"))

        resp = b""
        try:
            while True:
                chunk = self._sock.recv(4096)
                if not chunk:
                    break
                resp += chunk
                if b"\x00" in chunk:
                    break
        except socket.timeout:
            _LOGGER.debug("Receive timeout after %d bytes", len(resp))

        if resp.endswith(b"\x00"):
            resp = resp[:-1]

        return resp.decode("ascii", errors="ignore")

    # Convenience methods - Power
    def power_on(self) -> str:
        return self.send(self.CMD_POWER_ON)

    def power_off(self) -> str:
        return self.send(self.CMD_POWER_OFF)

    def get_power_status(self) -> str:
        return self.send(self.CMD_POWER_STATUS)

    # Convenience methods - Zone selection
    def select_zone_a(self) -> str:
        return self.send(self.CMD_ZONE_A)

    def select_zone_b(self) -> str:
        return self.send(self.CMD_ZONE_B)

    # Convenience methods - Status queries
    def get_status(self) -> str:
        """Get status (returns preset data when powered on)."""
        return self.send(self.CMD_GET_STATUS)

    def get_assignments(self) -> str:
        return self.send(self.CMD_GET_ASSIGNMENTS)

    def reset_levels(self) -> str:
        return self.send(self.CMD_RESET_LEVELS)

    def get_version(self) -> str:
        return self.send(self.CMD_GET_VERSION)

    # Convenience methods - Input selection
    def select_source(self, source: str) -> str:
        """Select input source: earc, hdmi1-hdmi4, usb, line, stereo, coaxial, optical"""
        sources = {
            "earc": self.CMD_SOURCE_EARC,
            "hdmi1": self.CMD_SOURCE_HDMI1,
            "hdmi2": self.CMD_SOURCE_HDMI2,
            "hdmi3": self.CMD_SOURCE_HDMI3,
            "hdmi4": self.CMD_SOURCE_HDMI4,
            "usb": self.CMD_SOURCE_USB,
            "line": self.CMD_SOURCE_LINE,
            "stereo": self.CMD_SOURCE_STEREO,
            "coaxial": self.CMD_SOURCE_COAXIAL,
            "optical": self.CMD_SOURCE_OPTICAL,
        }
        if source.lower() not in sources:
            raise ValueError(f"Unknown source: {source}")
        return self.send(sources[source.lower()])

    # Convenience methods - Presets
    def get_preset_a(self) -> str:
        return self.send(self.CMD_GET_PRESET_A)

    def get_preset_b(self) -> str:
        return self.send(self.CMD_GET_PRESET_B)

    def get_user_b_info(self) -> str:
        return self.send(self.CMD_GET_USER_B_INFO)

    def load_preset_a(self, preset_num: int) -> str:
        """Load User A preset 1-8."""
        if not 1 <= preset_num <= 8:
            raise ValueError("Preset must be 1-8")
        return self.send(0x70 + preset_num - 1)

    def load_preset_b(self, preset_num: int) -> str:
        """Load User B preset 8-16."""
        if not 8 <= preset_num <= 16:
            raise ValueError("Preset must be 8-16")
        return self.send(0x97 + preset_num - 8)
