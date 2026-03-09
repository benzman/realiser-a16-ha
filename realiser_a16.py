#!/usr/bin/env python3
"""
Realiser A16 TCP Remote Control Client
Protokoll basierend auf Wireshark-Analyse (dump.pcapng)
"""

import socket
from typing import Dict, List, Optional, Union


class RealiserA16:
    """TCP Client für Realiser A16 Verstärker"""

    # Präambeln (identifiziert aus Wireshark)
    PREAMBLE_PRESET = bytes(
        [
            0xDE,
            0x19,
            0x16,
            0x16,
            0x11,
            0x56,
            0x43,
            0xDE,
            0x19,
            0x16,
            0x16,
            0x19,
            0x41,
            0x01,
        ]
    )
    PREAMBLE_STATUS = bytes(
        [0xDE, 0x19, 0x16, 0x16, 0x11, 0x56, 0x38, 0xDE, 0x19, 0x16, 0x16, 0x19]
    )

    # Standard-Port aus Wireshark: 4101
    DEFAULT_PORT = 4101

    def __init__(self, host: str, port: int = DEFAULT_PORT, timeout: float = 5.0):
        """
        Args:
            host: IP-Adresse des Realiser A16
            port: TCP Port (Default: 4101)
            timeout: Socket-Timeout in Sekunden
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None

    def connect(self) -> None:
        """TCP-Verbindung herstellen"""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self.timeout)
        self._sock.connect((self.host, self.port))

    def close(self) -> None:
        """Verbindung schließen"""
        if self._sock:
            self._sock.close()
            self._sock = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _build_preset_frame(self, params: Dict[str, Union[str, int]]) -> bytes:
        """
        Baue einen Preset/Config-Frame mit Präambel und KEY=VALUE Paaren.

        Args:
            params: Dictionary mit Key-Value Paaren (ohne Null-Terminatoren)

        Returns:
            Rohdaten-Bytes zum Senden
        """
        frame = bytearray(self.PREAMBLE_PRESET)

        for key, value in params.items():
            # KEY=
            frame.extend(key.encode("ascii"))
            frame.extend(b"=")
            # VALUE
            if isinstance(value, int):
                frame.extend(str(value).encode("ascii"))
            else:
                frame.extend(str(value).encode("ascii"))
            # Null-Terminator
            frame.extend(b"\x00")

        return bytes(frame)

    def _parse_response(self, data: bytes) -> Dict[str, List[str]]:
        """
        Parse empfangene Rohdaten in Key-Value Paare.

        Returns:
            Dictionary mit Keys und Liste aller vorkommenden Werte
        """
        result: Dict[str, List[str]] = {}

        # Nach Null-Terminatoren splitten
        i = 0
        while i < len(data):
            # Finde nächsten Null-Byte
            end = data.find(b"\x00", i)
            if end == -1:
                break

            token = data[i:end]
            if b"=" in token:
                try:
                    key, value = token.split(b"=", 1)
                    key_str = key.decode("ascii")
                    val_str = value.decode("ascii", errors="ignore")
                    if key_str not in result:
                        result[key_str] = []
                    result[key_str].append(val_str)
                except (UnicodeDecodeError, ValueError):
                    pass

            i = end + 1

        return result

    def send_preset(
        self,
        aur: Optional[str] = None,
        pa: Optional[str] = None,
        va: Optional[Union[int, str]] = None,
        aroom: Optional[str] = None,
        aname: Optional[str] = None,
        aspkr: Optional[str] = None,
        aqfile: Optional[str] = None,
        aqname: Optional[str] = None,
        aqdate: Optional[str] = None,
        aqtype: Optional[str] = None,
        aqmod: Optional[str] = None,
        atact: Optional[str] = None,
        inp: Optional[str] = None,  # IN=<source>
        dec: Optional[str] = None,
        lm: Optional[str] = None,
        umix: Optional[str] = None,
        htmode: Optional[str] = None,
        leg: Optional[str] = None,
        user: Optional[str] = None,
        pwr: Optional[str] = None,
        all_mode: Optional[str] = None,
        test: Optional[str] = None,
        mode: Optional[str] = None,
        # Lautsprecher-Pegel L1-L24 (dB)
        lvls: Optional[List[int]] = None,
        # Amplifier-Pegel AHL, AHR, ATL, ATR
        ahl: Optional[int] = None,
        ahr: Optional[int] = None,
        atl: Optional[int] = None,
        atr: Optional[int] = None,
        # Zone B (B- Präfix)
        bur: Optional[str] = None,
        pb: Optional[str] = None,
        vb: Optional[Union[int, str]] = None,
        broom: Optional[str] = None,
        bname: Optional[str] = None,
        bspkr: Optional[str] = None,
        bqfile: Optional[str] = None,
        bqname: Optional[str] = None,
        bqdate: Optional[str] = None,
        bqtype: Optional[str] = None,
        bqmod: Optional[str] = None,
        btact: Optional[str] = None,
        bhl: Optional[int] = None,
        bhr: Optional[int] = None,
        btl: Optional[int] = None,
        btr: Optional[int] = None,
    ) -> None:
        """
        Sende Preset/Config-Daten an den Verstärker.

        Die meisten Parameter sind optionale Strings, wie im Wireshark-Dump gesehen.
        Beispiel:
            send_preset(
                aur="Benni",
                pa="01",
                va=62,
                aspkr="5.1.4h",
                aqfile="Benni _NDH 30",
                atact="ON",
                inp="HDMI-1",
                dec="PCM 2ch",
                lm="5.1.4",
                umix="AuroMatic",
                htmode="Optical",
                leg="OFF",
                user="DUAL",
                pwr="ON",
                all_mode="SOLO",
                test="OFF",
                mode="SVS"
            )
        """
        if not self._sock:
            raise RuntimeError("Not connected. Call connect() first.")

        params: Dict[str, Union[str, int]] = {}

        # Zone A
        if aur is not None:
            params["AUR"] = aur
        if pa is not None:
            params["PA"] = pa
        if va is not None:
            params["VA"] = va
        if aroom is not None:
            params["AROOM"] = aroom
        if aname is not None:
            params["ANAME"] = aname
        if aspkr is not None:
            params["ASPKR"] = aspkr
        if aqfile is not None:
            params["AQFILE"] = aqfile
        if aqname is not None:
            params["AQNAME"] = aqname
        if aqdate is not None:
            params["AQDATE"] = aqdate
        if aqtype is not None:
            params["AQTYPE"] = aqtype
        if aqmod is not None:
            params["AQMOD"] = aqmod
        if atact is not None:
            params["ATACT"] = atact
        if inp is not None:
            params["IN"] = inp
        if dec is not None:
            params["DEC"] = dec
        if lm is not None:
            params["LM"] = lm
        if umix is not None:
            params["UMIX"] = umix
        if htmode is not None:
            params["HTMODE"] = htmode
        if leg is not None:
            params["LEG"] = leg
        if user is not None:
            params["USER"] = user

        # Globale Befehle
        if pwr is not None:
            params["PWR"] = pwr
        if all_mode is not None:
            params["ALL"] = all_mode
        if test is not None:
            params["TEST"] = test
        if mode is not None:
            params["MODE"] = mode

        # Lautsprecher-Pegel L1-L24
        if lvls and len(lvls) >= 24:
            for i, lvl in enumerate(lvls[:24], start=1):
                params[f"L{i}"] = lvl

        # Amplifier-Pegel Zone A
        if ahl is not None:
            params["AHL"] = ahl
        if ahr is not None:
            params["AHR"] = ahr
        if atl is not None:
            params["ATL"] = atl
        if atr is not None:
            params["ATR"] = atr

        # Zone B (B- Präfix)
        if bur is not None:
            params["BUR"] = bur
        if pb is not None:
            params["PB"] = pb
        if vb is not None:
            params["VB"] = vb
        if broom is not None:
            params["BROOM"] = broom
        if bname is not None:
            params["BNAME"] = bname
        if bspkr is not None:
            params["BSPKR"] = bspkr
        if bqfile is not None:
            params["BQFILE"] = bqfile
        if bqname is not None:
            params["BQNAME"] = bqname
        if bqdate is not None:
            params["BQDATE"] = bqdate
        if bqtype is not None:
            params["BQTYPE"] = bqtype
        if bqmod is not None:
            params["BQMOD"] = bqmod
        if btact is not None:
            params["BTACT"] = btact
        if bhl is not None:
            params["BHL"] = bhl
        if bhr is not None:
            params["BHR"] = bhr
        if btl is not None:
            params["BTL"] = btl
        if btr is not None:
            params["BTR"] = btr

        frame = self._build_preset_frame(params)
        self._sock.send(frame)

    def query_status(self) -> Dict[str, List[str]]:
        """
        Sende Status-Abfrage und parse Antwort.

        Returns:
            Dictionary mit Keys und allen Werten
        """
        if not self._sock:
            raise RuntimeError("Not connected. Call connect() first.")

        # Sende Status-Anfrage mit 12-Byte-Präambel (wie in Stream 0)
        self._sock.send(self.PREAMBLE_STATUS)

        # Empfange Antwort (größer als preset, weil alle Zustände)
        data = self._sock.recv(8192)
        return self._parse_response(data)

    def set_power(self, state: str) -> None:
        """Ein/Aus: 'ON' oder 'OFF'"""
        self.send_preset(pwr=state)

    def set_volume(self, zone: str, volume: int) -> None:
        """
        Lautstärke setzen.

        Args:
            zone: 'A' oder 'B'
            volume: 0-100 (im Dump: va=62, vb=62)
        """
        if zone.upper() == "A":
            self.send_preset(va=volume)
        else:
            self.send_preset(vb=volume)

    def set_source(self, zone: str, source: str) -> None:
        """
        Eingang wählen.

        Args:
            source: z.B. 'HDMI-1', 'HDMI-2', 'Optical', 'Coaxial', etc.
        """
        if zone.upper() == "A":
            self.send_preset(inp=source)
        else:
            self.send_preset(bur=source)

    def set_mode(self, mode: str) -> None:
        """Betriebsmodus: 'SVS', 'STEREO', 'SURROUND', etc."""
        self.send_preset(mode=mode)

    def set_all_solo(self) -> None:
        """ALL=SOLO (wie im Dump)"""
        self.send_preset(all_mode="SOLO")

    def mute(self, zone: str) -> None:
        """Stummschaltung (über ATACT/BTACT)"""
        if zone.upper() == "A":
            self.send_preset(
                atact="OFF"
            )  # Achtung: im Dump ist ATACT=ON bedeutet aktiv?
        else:
            self.send_preset(btact="OFF")

    def unmute(self, zone: str) -> None:
        """Stummschaltung aufheben"""
        if zone.upper() == "A":
            self.send_preset(atact="ON")
        else:
            self.send_preset(btact="ON")

    # Bequeme Methoden für EQ/Setup
    def load_autoeq(
        self, zone: str, filename: str, eqname: str = "", date: str = ""
    ) -> None:
        """
        AutoEQ Preset laden.

        Args:
            zone: 'A' oder 'B'
            filename: Dateiname wie im Dump (z.B. "Benni _NDH 30")
            eqname: EQ Name (z.B. "Benni")
            date: Datum/Zeit (z.B. "14:37 13/02/2024")
        """
        if zone.upper() == "A":
            self.send_preset(
                aqfile=filename, aqname=eqname, aqdate=date, aqtype="autoEQ", atact="ON"
            )
        else:
            self.send_preset(
                bqfile=filename, bqname=eqname, bqdate=date, bqtype="autoEQ", btact="ON"
            )


# Beispiel-Nutzung:
if __name__ == "__main__":
    # Einfaches Beispiel:
    with RealiserA16("192.168.160.19") as amp:
        # Power ON
        amp.set_power("ON")

        # Lautstärke Zone A auf 50
        amp.set_volume("A", 50)

        # Eingang HDMI-1 für Zone A
        amp.set_source("A", "HDMI-1")

        # Preset laden
        amp.load_autoeq("A", "Benni _NDH 30", "Benni", "14:37 13/02/2024")

        # Status abfragen
        status = amp.query_status()
        print("Status:", status)

        # Alles auf Solo
        amp.set_all_solo()
