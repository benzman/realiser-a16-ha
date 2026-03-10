#!/usr/bin/env python3
"""
Realiser A16 TCP Remote using the official IP Command Protocol
Based on: A16-IP-command-server-May-2020-1.pdf

Protokoll:
- Send: 2-digit hex code + "\r\n"
- Receive: one or more null-terminated ASCII tokens per response burst
- The A16 always prepends async User A status tokens before the actual
  command response.  All tokens are categorised into an A16Response object
  so nothing is discarded - every piece of information ends up where it
  belongs.
"""

import logging
import re
import socket
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Union

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response container
# ---------------------------------------------------------------------------


@dataclass
class A16Response:
    """Categorised response from a single A16 command.

    All null-terminated tokens returned by the device are sorted into typed
    fields so callers never have to re-parse raw strings.
    """

    # User A fields (arrive async with every command response)
    user_a: Dict[str, str] = field(default_factory=dict)
    # AUR=, PA=, VA=, AROOM=, ANAME=, ASPKR=, AQFILE=, AQNAME=,
    # AQDATE=, AQTYPE=, AQMOD=, ATACT=, IN=, DEC=, LM=,
    # UMIX=, HTMODE=, LEG=, USER=

    # User B fields (arrive with 0xA0 response)
    user_b: Dict[str, str] = field(default_factory=dict)
    # BUR=, PB=, VB=, BROOM=, BNAME=, BSPKR=, BQFILE=, BQNAME=,
    # BQDATE=, BQTYPE=, BQMOD=, BTACT=

    # Speaker visibility indices (0-based), from V00 V01 … tokens
    visible_speakers: Set[int] = field(default_factory=set)

    # Active speaker indices (0-based), from A00 A01 … tokens
    active_speakers: Set[int] = field(default_factory=set)

    # Speaker mode: "SOLO" or "MUTE" from ALL=SOLO / ALL=MUTE
    speaker_mode: Optional[str] = None

    # Power status from PWR=ON / PWR=STANDBY / PWR=BOOT
    power: Optional[str] = None

    # DSP channel assignments: {"ach": {1: "L", …}, "bch": {1: "L", …}}
    assignments: Dict[str, Dict[int, str]] = field(
        default_factory=lambda: {"ach": {}, "bch": {}}
    )

    # Firmware / version tokens (A16FW=, APMFW=, …)
    firmware: Dict[str, str] = field(default_factory=dict)

    # Level meter values (L1=…, L2=…, AHL=…, BTR=…) from 0x38 / 0x6A
    levels: Dict[str, str] = field(default_factory=dict)

    # Any token that did not fit a known category
    other: Dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Known token prefixes - used by the parser to route each token
# ---------------------------------------------------------------------------

# User A tokens that come asynchronously with every command response
_USER_A_KEYS: Set[str] = {
    "AUR",
    "PA",
    "VA",
    "AROOM",
    "ANAME",
    "ASPKR",
    "AQFILE",
    "AQNAME",
    "AQDATE",
    "AQTYPE",
    "AQMOD",
    "ATACT",
    "IN",
    "DEC",
    "LM",
    "UMIX",
    "HTMODE",
    "LEG",
    "USER",
}

# User B tokens from 0xA0
_USER_B_KEYS: Set[str] = {
    "BUR",
    "PB",
    "VB",
    "BROOM",
    "BNAME",
    "BSPKR",
    "BQFILE",
    "BQNAME",
    "BQDATE",
    "BQTYPE",
    "BQMOD",
    "BTACT",
}

# Firmware version keys from 0x64
_FIRMWARE_KEYS: Set[str] = {"A16FW", "APMFW", "HSRFW", "HTFW", "A16SN"}

# Level-meter keys from 0x38 / 0x6A  (L1…L24, AHL, BTR, etc.)
_LEVEL_KEY_RE = re.compile(r"^(L\d+|AHL|BTR|ATR)$")

# Assignment channel prefixes (ACH1…ACH24, BCH1…BCH16)
_ACH_RE = re.compile(r"^ACH(\d+)$")
_BCH_RE = re.compile(r"^BCH(\d+)$")


def _parse_token(token: str, resp: A16Response) -> None:
    """Route a single KEY=VALUE or bare token into the correct field."""
    token = token.strip()
    if not token:
        return

    if "=" in token:
        key, value = token.split("=", 1)
        key = key.strip()
        value = value.strip()

        if key in _USER_A_KEYS:
            resp.user_a[key] = value
        elif key in _USER_B_KEYS:
            resp.user_b[key] = value
        elif key == "PWR":
            resp.power = value
        elif key == "ALL":
            resp.speaker_mode = value
        elif key in _FIRMWARE_KEYS:
            resp.firmware[key] = value
        elif _ACH_RE.match(key):
            idx = int(_ACH_RE.match(key).group(1))  # type: ignore[union-attr]
            resp.assignments["ach"][idx] = value
        elif _BCH_RE.match(key):
            idx = int(_BCH_RE.match(key).group(1))  # type: ignore[union-attr]
            resp.assignments["bch"][idx] = value
        elif _LEVEL_KEY_RE.match(key):
            resp.levels[key] = value
        else:
            resp.other[key] = value
    else:
        # Bare tokens: V00…V49 (visible) and A00…A49 (active)
        if len(token) >= 2:
            if token[0] == "V" and token[1:].isdigit():
                resp.visible_speakers.add(int(token[1:]))
            elif token[0] == "A" and token[1:].isdigit():
                resp.active_speakers.add(int(token[1:]))
            elif token[0] == "M" and token[1:].isdigit():
                pass  # muted speaker tokens - currently not needed
            else:
                resp.other[token] = ""


# ---------------------------------------------------------------------------
# Main client class
# ---------------------------------------------------------------------------


class RealiserA16Hex:
    """TCP client for the official A16 IP command protocol."""

    # Command codes (Table 2 of A16-IP-command-server-May-2020-1.pdf)
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

    CMD_POWER_ON = 0x2C
    CMD_POWER_OFF = 0x2D
    CMD_POWER_STATUS = 0x2E

    CMD_ZONE_A = 0x06
    CMD_ZONE_B = 0x07

    CMD_VOL_A_UP = 0x30
    CMD_VOL_A_DN = 0x31
    CMD_MUTE_A = 0x32
    CMD_VOL_B_UP = 0x33
    CMD_VOL_B_DN = 0x34
    CMD_MUTE_B = 0x35

    CMD_GET_ASSIGNMENTS = 0x37
    CMD_RESET_LEVELS = 0x38
    CMD_GET_ALL_LEVELS = 0x6A
    CMD_GET_VERSION = 0x64

    CMD_ALL_TOGGLE = 0x1A  # Toggle SOLO/MUTE

    CMD_USER_A_INFO = 0x80
    CMD_VOL_A_GET = 0x83

    CMD_USER_B_INFO = 0xA0
    CMD_VOL_B_GET = 0xA3

    CMD_SPEAKER_VISIBILITY = 0xAE
    CMD_SPEAKER_STATUS = 0xAF
    CMD_SPEAKER_BASE = 0xB0  # + speaker_id (1-50)

    # Preset load: 0x70-0x7F (User A #1-16), 0x90-0x9F (User B #1-16)
    CMD_LOAD_PRESET_A1 = 0x70
    CMD_LOAD_PRESET_B1 = 0x90

    # Speaker name lookup table (Table 3)
    SPEAKER_NAMES: Dict[int, str] = {
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

    VOLUME_MIN = 27
    VOLUME_MAX = 99

    def __init__(self, host: str, port: int = 4101, timeout: float = 30.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Open TCP connection to A16."""
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

    def __enter__(self) -> "RealiserA16Hex":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Core send / receive
    # ------------------------------------------------------------------

    def send(self, code: Union[int, str]) -> A16Response:
        """Send a command and return a fully categorised A16Response.

        All tokens in the burst response are classified and stored in the
        appropriate field of A16Response - nothing is discarded.

        Args:
            code: Command code as int (0x37) or 2-char hex string ("37").

        Returns:
            A16Response with every token routed to the right field.
        """
        if not self._sock:
            raise RuntimeError("Not connected. Call connect() first.")

        if isinstance(code, int):
            cmd = f"{code:02x}\r\n"
        else:
            if len(code) != 2:
                raise ValueError("Hex code must be exactly 2 digits")
            cmd = f"{code}\r\n"

        _LOGGER.debug("Sending: %s", repr(cmd))
        self._sock.sendall(cmd.encode("ascii"))

        raw = self._recv_all()
        return self._categorise(raw)

    def _recv_all(self) -> str:
        """Collect the full response burst across multiple TCP packets.

        The A16 always sends at least two bursts:
          1. Async User A status (~50 ms after command)
          2. The actual command response (~150 ms later)

        We keep reading until a 500 ms silence, bounded by a 4 s wall-clock
        limit.  Each recv is followed by a 150 ms pause so the OS can fill
        the next burst before we attempt another read.
        """
        buf = b""
        deadline = time.monotonic() + 4.0

        while time.monotonic() < deadline:
            try:
                self._sock.settimeout(0.5)
                chunk = self._sock.recv(4096)
            except socket.timeout:
                break  # 500 ms of silence → done

            if not chunk:
                break  # connection closed

            buf += chunk
            # Give the device time to send the next burst
            time.sleep(0.15)

        # Trim trailing null / CR
        if b"\x00" in buf:
            buf = buf[: buf.rfind(b"\x00")]

        return buf.decode("ascii", errors="ignore")

    def _categorise(self, raw: str) -> A16Response:
        """Parse every null-separated token and route it into A16Response."""
        resp = A16Response()
        for token in raw.split("\x00"):
            _parse_token(token, resp)
        _LOGGER.debug(
            "A16Response: user_a_keys=%s power=%s mode=%s visible=%s active=%s fw=%s ach=%s bch=%s",
            list(resp.user_a.keys()),
            resp.power,
            resp.speaker_mode,
            resp.visible_speakers,
            resp.active_speakers,
            resp.firmware,
            len(resp.assignments["ach"]),
            len(resp.assignments["bch"]),
        )
        return resp

    # ------------------------------------------------------------------
    # Convenience methods (return A16Response)
    # ------------------------------------------------------------------

    def power_on(self) -> A16Response:
        return self.send(self.CMD_POWER_ON)

    def power_off(self) -> A16Response:
        return self.send(self.CMD_POWER_OFF)

    def get_power_status(self) -> A16Response:
        return self.send(self.CMD_POWER_STATUS)

    def select_zone_a(self) -> A16Response:
        return self.send(self.CMD_ZONE_A)

    def select_zone_b(self) -> A16Response:
        return self.send(self.CMD_ZONE_B)

    def get_assignments(self) -> A16Response:
        return self.send(self.CMD_GET_ASSIGNMENTS)

    def get_version(self) -> A16Response:
        return self.send(self.CMD_GET_VERSION)

    def get_user_a_info(self) -> A16Response:
        return self.send(self.CMD_USER_A_INFO)

    def get_user_b_info(self) -> A16Response:
        return self.send(self.CMD_USER_B_INFO)

    def get_speaker_visibility(self) -> A16Response:
        return self.send(self.CMD_SPEAKER_VISIBILITY)

    def get_speaker_status(self) -> A16Response:
        return self.send(self.CMD_SPEAKER_STATUS)

    def select_speaker(self, speaker_id: int) -> A16Response:
        """Select/toggle speaker by ID (1-50)."""
        if not 1 <= speaker_id <= 50:
            raise ValueError("Speaker ID must be 1-50")
        return self.send(self.CMD_SPEAKER_BASE + speaker_id)

    def load_preset_a(self, preset_num: int) -> A16Response:
        """Load User A preset 1-16."""
        if not 1 <= preset_num <= 16:
            raise ValueError("Preset must be 1-16")
        return self.send(self.CMD_LOAD_PRESET_A1 + preset_num - 1)

    def load_preset_b(self, preset_num: int) -> A16Response:
        """Load User B preset 1-16."""
        if not 1 <= preset_num <= 16:
            raise ValueError("Preset must be 1-16")
        return self.send(self.CMD_LOAD_PRESET_B1 + preset_num - 1)
