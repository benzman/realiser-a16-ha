#!/usr/bin/env python3
"""
Realiser A16 TCP Remote using the official IP Command Protocol
Based on: A16-IP-command-server-May-2020-1.pdf

Protokoll:
- Send: 2-digit hex code + "\r\n"
- Receive: ASCII string + "\x00"
"""

import socket
from typing import Union, Optional


class RealiserA16Hex:
    """Simple TCP client for official A16 IP command protocol"""

    # Command codes from PDF
    CMD_POWER_OFF = 0x00
    CMD_POWER_ON = 0x01
    CMD_MUTE = 0x02
    CMD_VOL_UP = 0x03
    CMD_VOL_DN = 0x04
    CMD_ASSIGNMENTS = 0x37
    CMD_MENU = 0x43
    CMD_ALL_SOLO = 0x56
    CMD_ALL_MUTE = 0x57
    CMD_GET_VERSION = 0x40
    CMD_GET_MODEL = 0x41
    CMD_GET_IP = 0x42
    CMD_GET_MAC = 0x43
    CMD_GET_PORT = 0x44
    CMD_GET_STATUS = 0x45
    CMD_GET_PRESET_A = 0x46
    CMD_GET_PRESET_B = 0x47
    CMD_STORE_PRESET_A = 0x48
    CMD_STORE_PRESET_B = 0x49
    CMD_LOAD_PRESET_A = 0x4A
    CMD_LOAD_PRESET_B = 0x4B
    CMD_SETVOL_A = 0x50
    CMD_SETVOL_B = 0x51
    CMD_MUTE_A = 0x52
    CMD_MUTE_B = 0x53
    CMD_SOLO_A = 0x54
    CMD_SOLO_B = 0x55

    # Zone selection IR commands
    CMD_ZONE_A = 0x06
    CMD_ZONE_B = 0x07

    def __init__(self, host: str, port: int = 4101, timeout: float = 5.0):
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
        """Close TCP connection"""
        if self._sock:
            self._sock.close()
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

        # Format: 2-digit hex + \r\n
        if isinstance(code, int):
            cmd = f"{code:02x}\r\n"
        else:
            cmd = f"{code}\r\n"
            if len(code) != 2:
                raise ValueError("Hex code must be 2 digits")

        self._sock.send(cmd.encode("ascii"))

        # Receive response (null-terminated)
        resp = b""
        while True:
            chunk = self._sock.recv(1024)
            if not chunk:
                break
            resp += chunk
            if resp.endswith(b"\x00"):
                break

        # Strip null terminator
        if resp.endswith(b"\x00"):
            resp = resp[:-1]

        return resp.decode("ascii", errors="ignore")

    # Convenience methods
    def power_on(self) -> str:
        return self.send(self.CMD_POWER_ON)

    def power_off(self) -> str:
        return self.send(self.CMD_POWER_OFF)

    def mute(self) -> str:
        return self.send(self.CMD_MUTE)

    def volume_up(self) -> str:
        return self.send(self.CMD_VOL_UP)

    def volume_down(self) -> str:
        return self.send(self.CMD_VOL_DN)

    def menu(self) -> str:
        return self.send(self.CMD_MENU)

    def select_zone_a(self) -> str:
        return self.send(self.CMD_ZONE_A)

    def select_zone_b(self) -> str:
        return self.send(self.CMD_ZONE_B)

    def all_solo(self) -> str:
        return self.send(self.CMD_ALL_SOLO)

    def all_mute(self) -> str:
        return self.send(self.CMD_ALL_MUTE)

    def get_version(self) -> str:
        return self.send(self.CMD_GET_VERSION)

    def get_model(self) -> str:
        return self.send(self.CMD_GET_MODEL)

    def get_ip(self) -> str:
        return self.send(self.CMD_GET_IP)

    def get_mac(self) -> str:
        return self.send(self.CMD_GET_MAC)

    def get_port(self) -> str:
        return self.send(self.CMD_GET_PORT)

    def get_status(self) -> str:
        return self.send(self.CMD_GET_STATUS)

    def get_assignments(self) -> str:
        return self.send(self.CMD_ASSIGNMENTS)

    def get_preset_a(self) -> str:
        return self.send(self.CMD_GET_PRESET_A)

    def get_preset_b(self) -> str:
        return self.send(self.CMD_GET_PRESET_B)

    def load_preset_a(self) -> str:
        return self.send(self.CMD_LOAD_PRESET_A)

    def load_preset_b(self) -> str:
        return self.send(self.CMD_LOAD_PRESET_B)

    def store_preset_a(self) -> str:
        return self.send(self.CMD_STORE_PRESET_A)

    def store_preset_b(self) -> str:
        return self.send(self.CMD_STORE_PRESET_B)

    def set_volume_a(self, volume: int) -> str:
        return self.send(self.CMD_SETVOL_A)

    def set_volume_b(self, volume: int) -> str:
        return self.send(self.CMD_SETVOL_B)

    def mute_zone_a(self) -> str:
        return self.send(self.CMD_MUTE_A)

    def mute_zone_b(self) -> str:
        return self.send(self.CMD_MUTE_B)

    def solo_zone_a(self) -> str:
        return self.send(self.CMD_SOLO_A)

    def solo_zone_b(self) -> str:
        return self.send(self.CMD_SOLO_B)
