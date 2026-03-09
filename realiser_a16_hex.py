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

    # Command codes from PDF (partial list)
    CMD_POWER_OFF = 0x00
    CMD_POWER_ON = 0x01
    CMD_MUTE = 0x02
    CMD_VOL_UP = 0x03
    CMD_VOL_DN = 0x04
    CMD_ASSIGNMENTS = 0x37  # Get speaker assignments
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
            # Ensure it's exactly 2 hex digits
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

    # Convenience methods for common commands
    def power_on(self) -> str:
        """Turn A16 ON"""
        return self.send(self.CMD_POWER_ON)

    def power_off(self) -> str:
        """Turn A16 OFF"""
        return self.send(self.CMD_POWER_OFF)

    def mute(self) -> str:
        """Mute toggle (IR remote MUTE key)"""
        return self.send(self.CMD_MUTE)

    def volume_up(self) -> str:
        """Volume up (IR remote VOL UP key)"""
        return self.send(self.CMD_VOL_UP)

    def volume_down(self) -> str:
        """Volume down (IR remote VOL DN key)"""
        return self.send(self.CMD_VOL_DN)

    def menu(self) -> str:
        """Press MENU key"""
        return self.send(self.CMD_MENU)

    def select_zone_a(self) -> str:
        """Select Zone A (IR remote)"""
        return self.send(self.CMD_ZONE_A)

    def select_zone_b(self) -> str:
        """Select Zone B (IR remote)"""
        return self.send(self.CMD_ZONE_B)

    def all_solo(self) -> str:
        """ALL = SOLO mode"""
        return self.send(self.CMD_ALL_SOLO)

    def all_mute(self) -> str:
        """ALL = MUTE mode"""
        return self.send(self.CMD_ALL_MUTE)

    def get_version(self) -> str:
        """Request firmware version"""
        return self.send(self.CMD_GET_VERSION)

    def get_model(self) -> str:
        """Request model identifier"""
        return self.send(self.CMD_GET_MODEL)

    def get_ip(self) -> str:
        """Request current IP address"""
        return self.send(self.CMD_GET_IP)

    def get_mac(self) -> str:
        """Request MAC address"""
        return self.send(self.CMD_GET_MAC)

    def get_port(self) -> str:
        """Request TCP port number"""
        return self.send(self.CMD_GET_PORT)

    def get_status(self) -> str:
        """Request full status"""
        return self.send(self.CMD_GET_STATUS)

    def get_assignments(self) -> str:
        """Request speaker assignments for current presets"""
        return self.send(self.CMD_ASSIGNMENTS)

    def get_preset_a(self) -> str:
        """Request Preset A data"""
        return self.send(self.CMD_GET_PRESET_A)

    def get_preset_b(self) -> str:
        """Request Preset B data"""
        return self.send(self.CMD_GET_PRESET_B)

    def load_preset_a(self) -> str:
        """Load Preset A"""
        return self.send(self.CMD_LOAD_PRESET_A)

    def load_preset_b(self) -> str:
        """Load Preset B"""
        return self.send(self.CMD_LOAD_PRESET_B)

    def store_preset_a(self) -> str:
        """Store current settings to Preset A"""
        return self.send(self.CMD_STORE_PRESET_A)

    def store_preset_b(self) -> str:
        """Store current settings to Preset B"""
        return self.send(self.CMD_STORE_PRESET_B)

    def set_volume_a(self, volume: int) -> str:
        """Set Zone A volume (0-?)"""
        # Note: PDF doesn't specify volume range. Sending 0-100 as decimal string?
        # Actually command 0x50 likely expects additional data. This needs testing.
        # For now, send only command (may not work without extra bytes)
        return self.send(self.CMD_SETVOL_A)

    def set_volume_b(self, volume: int) -> str:
        """Set Zone B volume (0-?)"""
        return self.send(self.CMD_SETVOL_B)

    def mute_zone_a(self) -> str:
        """Mute Zone A"""
        return self.send(self.CMD_MUTE_A)

    def mute_zone_b(self) -> str:
        """Mute Zone B"""
        return self.send(self.CMD_MUTE_B)

    def solo_zone_a(self) -> str:
        """Solo Zone A"""
        return self.send(self.CMD_SOLO_A)

    def solo_zone_b(self) -> str:
        """Solo Zone B"""
        return self.send(self.CMD_SOLO_B)


# Example usage
if __name__ == "__main__":
    # Connect to A16
    with RealiserA16Hex("192.168.160.19") as amp:
        # Power ON
        resp = amp.power_on()
        print("Power ON response:", resp)

        # Get version
        version = amp.get_version()
        print("Version:", version)

        # Get status
        status = amp.get_status()
        print("Status:", status)

        # Volume up
        amp.volume_up()

        # Get assignments
        assignments = amp.get_assignments()
        print("Assignments:", assignments)
