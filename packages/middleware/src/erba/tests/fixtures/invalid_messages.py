"""
Invalid HL7 messages for negative testing
"""

# Missing required MSH segment
MISSING_MSH = """PID|1
PV1|1
OBR|1||TEST001|01001^Automated Count^99MRC||20250828010809|20250828010809|||||||20250828010809||||||||||HM||||||||admin
OBX|7|NM|6690-2^WBC^LN||6.50|10*3/uL|4.00-10.00|~N|||F"""

# Missing required OBR segment
MISSING_OBR = """MSH|^~\\&|ELite 580|Erba|||20250828152838||ORU^R01|test123|P|2.3.1||||||UNICODE
PID|1
PV1|1
OBX|7|NM|6690-2^WBC^LN||6.50|10*3/uL|4.00-10.00|~N|||F"""

# Invalid datetime format in MSH
INVALID_MSH_DATETIME = """MSH|^~\\&|ELite 580|Erba|||INVALID_DATE||ORU^R01|test123|P|2.3.1||||||UNICODE
PID|1
PV1|1
OBR|1||TEST001|01001^Automated Count^99MRC||20250828010809|20250828010809|||||||20250828010809||||||||||HM||||||||admin
OBX|7|NM|6690-2^WBC^LN||6.50|10*3/uL|4.00-10.00|~N|||F"""

# Invalid datetime format in OBR
INVALID_OBR_DATETIME = """MSH|^~\\&|ELite 580|Erba|||20250828152838||ORU^R01|test123|P|2.3.1||||||UNICODE
PID|1
PV1|1
OBR|1||TEST001|01001^Automated Count^99MRC||INVALID_DATE|20250828010809|||||||20250828010809||||||||||HM||||||||admin
OBX|7|NM|6690-2^WBC^LN||6.50|10*3/uL|4.00-10.00|~N|||F"""

# Missing required OBX sequences (only has 7-16, missing 17-36)
MISSING_REQUIRED_OBX = """MSH|^~\\&|ELite 580|Erba|||20250828152838||ORU^R01|test123|P|2.3.1||||||UNICODE
PID|1
PV1|1
OBR|1||TEST001|01001^Automated Count^99MRC||20250828010809|20250828010809|||||||20250828010809||||||||||HM||||||||admin
OBX|7|NM|6690-2^WBC^LN||6.50|10*3/uL|4.00-10.00|~N|||F
OBX|8|NM|770-8^NEU%^LN||83.4|%|50.0-70.0|H~A|||F
OBX|9|NM|736-9^LYM%^LN||13.6|%|20.0-40.0|L~A|||F
OBX|10|NM|5905-5^MON%^LN||2.7|%|3.0-12.0|L~A|||F
OBX|11|NM|713-8^EOS%^LN||0.1|%|0.5-5.0|L~A|||F
OBX|12|NM|706-2^BAS%^LN||0.2|%|0.0-1.0|~N|||F
OBX|13|NM|751-8^NEU#^LN||5.43|10*3/uL|2.00-7.00|~N|||F
OBX|14|NM|731-0^LYM#^LN||0.88|10*3/uL|0.80-4.00|~N|||F
OBX|15|NM|742-7^MON#^LN||0.17|10*3/uL|0.12-1.20|~N|||F
OBX|16|NM|711-2^EOS#^LN||0.01|10*3/uL|0.02-0.50|L~A|||F"""

# Duplicate sequence numbers
DUPLICATE_SEQUENCES = """MSH|^~\\&|ELite 580|Erba|||20250828152838||ORU^R01|test123|P|2.3.1||||||UNICODE
PID|1
PV1|1
OBR|1||TEST001|01001^Automated Count^99MRC||20250828010809|20250828010809|||||||20250828010809||||||||||HM||||||||admin
OBX|7|NM|6690-2^WBC^LN||6.50|10*3/uL|4.00-10.00|~N|||F
OBX|7|NM|770-8^NEU%^LN||83.4|%|50.0-70.0|H~A|||F
OBX|9|NM|736-9^LYM%^LN||13.6|%|20.0-40.0|L~A|||F"""

# Invalid sequence numbers (out of range)
INVALID_SEQUENCE_NUMBERS = """MSH|^~\\&|ELite 580|Erba|||20250828152838||ORU^R01|test123|P|2.3.1||||||UNICODE
PID|1
PV1|1
OBR|1||TEST001|01001^Automated Count^99MRC||20250828010809|20250828010809|||||||20250828010809||||||||||HM||||||||admin
OBX|0|NM|6690-2^WBC^LN||6.50|10*3/uL|4.00-10.00|~N|||F
OBX|100|NM|770-8^NEU%^LN||83.4|%|50.0-70.0|H~A|||F"""

# Wrong value type in required range (IS instead of NM)
WRONG_VALUE_TYPE_REQUIRED = """MSH|^~\\&|ELite 580|Erba|||20250828152838||ORU^R01|test123|P|2.3.1||||||UNICODE
PID|1
PV1|1
OBR|1||TEST001|01001^Automated Count^99MRC||20250828010809|20250828010809|||||||20250828010809||||||||||HM||||||||admin
OBX|7|IS|6690-2^WBC^LN||6.50|10*3/uL|4.00-10.00|~N|||F
OBX|8|NM|770-8^NEU%^LN||83.4|%|50.0-70.0|H~A|||F"""

# Insufficient field count in OBX
INSUFFICIENT_OBX_FIELDS = """MSH|^~\\&|ELite 580|Erba|||20250828152838||ORU^R01|test123|P|2.3.1||||||UNICODE
PID|1
PV1|1
OBR|1||TEST001|01001^Automated Count^99MRC||20250828010809|20250828010809|||||||20250828010809||||||||||HM||||||||admin
OBX|7|NM|6690-2^WBC^LN||6.50"""

# Empty message
EMPTY_MESSAGE = ""

# Malformed HL7 structure
MALFORMED_STRUCTURE = """This is not a valid HL7 message at all
It has no proper segments or structure
Just random text that should fail parsing"""

# Invalid model field (empty)
INVALID_MODEL_FIELD = """MSH|^~\\&||Erba|||20250828152838||ORU^R01|test123|P|2.3.1||||||UNICODE
PID|1
PV1|1
OBR|1||TEST001|01001^Automated Count^99MRC||20250828010809|20250828010809|||||||20250828010809||||||||||HM||||||||admin
OBX|7|NM|6690-2^WBC^LN||6.50|10*3/uL|4.00-10.00|~N|||F"""

# Invalid facility field (too short)
INVALID_FACILITY_FIELD = """MSH|^~\\&|ELite 580|E|||20250828152838||ORU^R01|test123|P|2.3.1||||||UNICODE
PID|1
PV1|1
OBR|1||TEST001|01001^Automated Count^99MRC||20250828010809|20250828010809|||||||20250828010809||||||||||HM||||||||admin
OBX|7|NM|6690-2^WBC^LN||6.50|10*3/uL|4.00-10.00|~N|||F"""