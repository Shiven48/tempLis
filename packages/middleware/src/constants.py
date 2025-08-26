ENQ = b'\x05'
ACK = b'\x06'
NAK = b'\x15'
EOT = b'\x04'
STX = b'\x02'
ETX = b'\x03'
CR  = b'\r'
LF  = b'\n'

control_map = {
    0x05: 'ENQ',
    0x06: 'ACK',
    0x15: 'NAK',
    0x04: 'EOT',
    0x02: 'STX',
    0x03: 'ETX',
    0x0D: 'CR',
    0x0A: 'LF',
}

CONTROL_CHAR_TO_BYTE = {
    'ENQ': ENQ,
    'ACK': ACK,
    'NAK': NAK,
    'EOT': EOT,
    'STX': STX,
    'ETX': ETX,
    'CR' : CR,
    'LF' : LF
}

START_BLOCK = b'\x0b'
END_BLOCK = b'\x1c'
CARRIAGE_RETURN = b'\x0d'