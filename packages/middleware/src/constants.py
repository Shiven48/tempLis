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

host = "127.0.0.1"
port = 15200
BUFFER_SIZE = 4096

ERBA_YAML_PATH = 'packages/middleware/src/configuration/erba.yaml'
# ERBA_YAML_PATH = 'configuration/erba.yaml'


cbc_parameters = {
    "WBC": "White Blood Cell Count",
    "NEU%": "Neutrophil Percentage",
    "LYM%": "Lymphocyte Percentage",
    "MON%": "Monocyte Percentage",
    "EOS%": "Eosinophil Percentage",
    "BAS%": "Basophil Percentage",
    "NEU#": "Absolute Neutrophil Count",
    "LYM#": "Absolute Lymphocyte Count",
    "MON#": "Absolute Monocyte Count",
    "EOS#": "Absolute Eosinophil Count",
    "BAS#": "Absolute Basophil Count",
    "*ALY#": "Atypical Lymphocyte Count",
    "*ALY%": "Atypical Lymphocyte Percentage",
    "*LIC#": "Large Immature Cell Count",
    "*LIC%": "Large Immature Cell Percentage",
    "RBC": "Red Blood Cell Count",
    "HGB": "Hemoglobin",
    "HCT": "Hematocrit",
    "MCV": "Mean Corpuscular Volume",
    "MCH": "Mean Corpuscular Hemoglobin",
    "MCHC": "Mean Corpuscular Hemoglobin Concentration",
    "RDW-CV": "Red Cell Distribution Width (CV)",
    "RDW-SD": "Red Cell Distribution Width (SD)",
    "PLT": "Platelet Count",
    "MPV": "Mean Platelet Volume",
    "PDW-SD": "Platelet Distribution Width (SD)",
    "PDW-CV": "Platelet Distribution Width (CV)",
    "PCT": "Plateletcrit",
    "P-LCR": "Platelet Large Cell Ratio",
    "P-LCC": "Platelet Large Cell Count"
}