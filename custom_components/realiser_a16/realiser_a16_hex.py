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

    # All key - toggles SOLO/MUTE mode (Table 1: #38) → ALL=SOLO or ALL=MUTE
    CMD_ALL_TOGGLE = 0x1A

    # User A info (Table 2: #57) - VA, AUR, IN, ASPKR, ...
    CMD_USER_A_INFO = 0x80
    # User A volume only (Table 2: #60) - VA=27-99
    CMD_VOL_A_GET = 0x83

    # User B info (Table 2: #89) - VB, BUR, ...
    CMD_USER_B_INFO = 0xA0
    # User B volume only (Table 2: #92) - VB=27-99
    CMD_VOL_B_GET = 0xA3

    # Speaker visibility (Table 2: #103) → V00,V01,...Vnn
    CMD_SPEAKER_VISIBILITY = 0xAE
    # Active speaker status (Table 2: #104) → A00,A01,...Ann
    CMD_SPEAKER_STATUS = 0xAF

    # Speaker select base (Table 2: #106-155)
    # Speaker ID n (1-50) → command = 0xB0 + n
    # In SOLO mode: solos speaker; in MUTE mode: toggles between active and muted
    CMD_SPEAKER_BASE = 0xB0

    # Speaker name lookup table (from PDF Table 3)
    SPEAKER_NAMES: dict = {
        1: "L",
        2: "R",
        3: "C",
        4: "SW",
        5: "Ls",
        6: "Rs",
        7: "Lb",
        8: "Rb",
        9: "Lss",
        10: "Rss",
        11: "Ltr",
        12: "Rtr",
        13: "Lw",
        14: "Rw",
        15: "Lbs",
        16: "Rbs",
        17: "Lc",
        18: "Rc",
        19: "Lu",
        20: "Ru",
        21: "Cu",
        22: "Ch",
        23: "Chr",
        24: "T",
        25: "Lh",
        26: "Rh",
        27: "Lhs",
        28: "Rhs",
        29: "Lhr",
        30: "Rhr",
        31: "Ltf",
        32: "Rtf",
        33: "Ltm",
        34: "Rtm",
        35: "Ltr",
        36: "Rtr",
        37: "Lsc",
        38: "Rsc",
        39: "Ls1",
        40: "Rs1",
        41: "Lrs1",
        42: "Rrs1",
        43: "Lrs2",
        44: "Rrs2",
        45: "Lhw",
        46: "Rhw",
        47: "Lhs1",
        48: "Rhs1",
        49: "Lbu",
        50: "Rbu",
    }

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

    # Convenience methods
    def get_assignments(self) -> str:
        return self.send(self.CMD_GET_ASSIGNMENTS)

    def get_version(self) -> str:
        return self.send(self.CMD_GET_VERSION)

    def get_user_a_info(self) -> str:
        return self.send(self.CMD_USER_A_INFO)

    def get_user_b_info(self) -> str:
        return self.send(self.CMD_USER_B_INFO)

    def get_speaker_visibility(self) -> str:
        return self.send(self.CMD_SPEAKER_VISIBILITY)

    def get_speaker_status(self) -> str:
        return self.send(self.CMD_SPEAKER_STATUS)

    def select_speaker(self, speaker_id: int) -> str:
        """Select/toggle speaker by ID (1-50)."""
        if not 1 <= speaker_id <= 50:
            raise ValueError("Speaker ID must be 1-50")
        return self.send(self.CMD_SPEAKER_BASE + speaker_id)

    def load_preset_a(self, preset_num: int) -> str:
        """Load User A preset 1-16."""
        if not 1 <= preset_num <= 16:
            raise ValueError("Preset must be 1-16")
        return self.send(0x70 + preset_num - 1)

    def load_preset_b(self, preset_num: int) -> str:
        """Load User B preset 1-16."""
        if not 1 <= preset_num <= 16:
            raise ValueError("Preset must be 1-16")
        return self.send(0x90 + preset_num - 1)
