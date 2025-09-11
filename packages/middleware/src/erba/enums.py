from enum import Enum

class TransportMode(str, Enum):
    TCP = "tcp"
    SERIAL = "serial"
    UDP = "udp"

class Protocol(str, Enum):
    HL7 = "HL7"
    ASTM = "ASTM"
    HL7_MLLP = "HL7-MLLP"

class Encoding(str, Enum):
    UTF8 = "utf-8"
    ASCII = "ascii"
    LATIN1 = "latin-1"
    CP1252 = "cp1252"