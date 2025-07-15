import hl7
import json
from datetime import datetime
import logging

logging.basicConfig(filename='logs/core.log', level=logging.INFO, format='%(asctime)s %(message)s')

def flatten_obx_result(obx):
    # Helper to flatten test_id and flags
    def flatten_field(field):
        if isinstance(field, list):
            # If it's a list of lists (like test_id), join first elements with ^
            if all(isinstance(x, list) for x in field):
                return "^".join(x[0] if x else "" for x in field)
            # If it's a list of strings, join non-empty with ~
            return "~".join(x for x in field if x)
        return field if field else ""
    return {
        "sequence": obx.get("sequence", [""])[0] if isinstance(obx.get("sequence", ""), list) else obx.get("sequence", ""),
        "value_type": obx.get("value_type", [""])[0] if isinstance(obx.get("value_type", ""), list) else obx.get("value_type", ""),
        "test_id": flatten_field(obx.get("test_id", "")),
        "test_name": obx.get("test_name", ""),
        "value": obx.get("value", [""])[0] if isinstance(obx.get("value", ""), list) else obx.get("value", ""),
        "units": obx.get("units", [""])[0] if isinstance(obx.get("units", ""), list) else obx.get("units", ""),
        "reference_range": obx.get("reference_range", [""])[0] if isinstance(obx.get("reference_range", ""), list) else obx.get("reference_range", ""),
        "flags": flatten_field(obx.get("flags", "")),
    }

def parse_obx_segments(segments):
    results = []
    for seg in segments:
        # Strip whitespace from segment type
        seg_type = str(seg[0]).strip() if seg[0] else ""
        if seg_type != 'OBX':
            continue
        # Handle test_id and test_name safely
        test_id = seg[3][0] if len(seg[3]) > 0 else ""
        test_name = seg[3][1] if len(seg[3]) > 1 else ""
        obx = {
            "sequence": seg[1],
            "value_type": seg[2],
            "test_id": test_id,
            "test_name": test_name,
            "value": seg[5],
            "units": seg[6],
            "reference_range": seg[7],
            "flags": seg[8],
        }
        results.append(obx)
    return results

def parse_hl7_message(message: str):
    print("Debug: Starting to parse HL7 message")
    # Replace [CR] with actual carriage return
    message = message.replace("[CR]", "\r")
    parsed = hl7.parse(message)
    print(f"Debug: Number of segments parsed: {len(parsed)}")
    message_dict = {
        "msh": {},
        "pid": {},
        "pv1": {},
        "obr": {},
        "obx_results": []
    }
    for seg in parsed:
        # Strip whitespace from segment type - this is the key fix
        seg_type = str(seg[0]).strip() if seg[0] else ""
        print(f"Debug: Segment type: '{seg_type}' (original: '{seg[0]}'), Length: {len(seg)}, First few fields: {seg[:5]}")
        if seg_type == 'MSH':
            message_dict["msh"] = {
                "sending_app": seg[2] if len(seg) > 2 else "",
                "sending_facility": seg[3] if len(seg) > 3 else "",
                "datetime": seg[6] if len(seg) > 6 else "",
                "message_type": seg[8] if len(seg) > 8 else "",
                "message_id": seg[9] if len(seg) > 9 else "",
                "hl7_version": seg[11] if len(seg) > 11 else "",
            }
        elif seg_type == 'PID':
            message_dict["pid"] = {
                "patient_id": seg[1] if len(seg) > 1 else "",
            }
        elif seg_type == 'PV1':
            message_dict["pv1"] = {
                "visit_number": seg[1] if len(seg) > 1 else "",
            }
        elif seg_type == 'OBR':
            # Handle OBR test_id and test_name safely
            test_id = seg[4][0] if len(seg) > 4 and len(seg[4]) > 0 else ""
            test_name = seg[4][1] if len(seg) > 4 and len(seg[4]) > 1 else ""
            message_dict["obr"] = {
                "order_id": seg[3] if len(seg) > 3 else "",
                "test_id": test_id,
                "test_name": test_name,
                "ordered_at": seg[6] if len(seg) > 6 else "",
                "collected_at": seg[7] if len(seg) > 7 else "",
            }
    message_dict["obx_results"] = parse_obx_segments(parsed)
    return message_dict

if __name__ == "__main__":
    # This is the point where the info will be fetched
    raw_message = r"MSH|^~\&|ELite 580|Erba|||20250628173333||ORU^R01|031416ea601f4d8fa02c823f6fa42b8e|P|2.3.1||||||UNICODE[CR]PID|1[CR]PV1|1[CR]OBR|1||25059651|01001^Automated Count^99MRC||20250628173219|20250628173219|||||||20250628173219||||||||||HM||||||||admin[CR]OBX|1|IS|02001^Take Mode^99MRC||A||||||F[CR]OBX|2|IS|02002^Blood Mode^99MRC||W||||||F[CR]OBX|3|IS|02003^Test Mode^99MRC||CBC+DIFF||||||F[CR]OBX|4|NM|30525-0^Age^LN||||||||F[CR]OBX|5|IS|09001^Remark^99MRC||||||||F[CR]OBX|6|IS|03001^Ref Group^99MRC||General||||||F[CR]OBX|7|NM|6690-2^WBC^LN||7.13|10*3/uL|4.00-10.00|~N|||F[CR]OBX|8|NM|770-8^NEU%^LN||43.2|%|50.0-70.0|L~A|||F[CR]OBX|9|NM|736-9^LYM%^LN||35.1|%|20.0-40.0|~A|||F[CR]OBX|10|NM|5905-5^MON%^LN||19.1|%|3.0-12.0|H~A|||F[CR]OBX|11|NM|713-8^EOS%^LN||1.7|%|0.5-5.0|~N|||F[CR]OBX|12|NM|706-2^BAS%^LN||0.9|%|0.0-1.0|~N|||F[CR]OBX|13|NM|751-8^NEU#^LN||3.09|10*3/uL|2.00-7.00|~N|||F[CR]OBX|14|NM|731-0^LYM#^LN||2.50|10*3/uL|0.80-4.00|~A|||F[CR]OBX|15|NM|742-7^MON#^LN||1.36|10*3/uL|0.12-1.20|H~A|||F[CR]OBX|16|NM|711-2^EOS#^LN||0.12|10*3/uL|0.02-0.50|~N|||F[CR]OBX|17|NM|704-7^BAS#^LNOBX|37|IS|15192-8^Atypical Lymphs?^LN||T||||||F[CR]OBX|38|IS|13502^Thrombocytopenia^99MRC||T||||||F[CR][FS][CR]||0.06|10*3/uL|0.00-0.10|~N|||F[CR]OBX|18|NM|26477-0^*ALY#^LN||0.01|10*3/uL|0.00-0.20|~A|||F[CR]OBX|19|NM|13046-8^*ALY%^LN||0.2|%|0.0-2.0|~A|||F[CR]OBX|20|NM|11001^*LIC#^99MRC||0.00|10*3/uL|0.00-0.20|~N|||F[CR]OBX|21|NM|11002^*LIC%^99MRC||0.1|%|0.0-2.5|~N|||F[CR]OBX|22|NM|789-8^RBC^LN||6.32|10*6/uL|3.50-5.50|H~A|||F[CR]OBX|23|NM|718-7^HGB^LN||19.0|g/dL|11.0-16.0|H~A|||F[CR]OBX|24|NM|4544-3^HCT^LN||56.9|%|37.0-54.0|H~A|||F[CR]OBX|25|NM|787-2^MCV^LN||90.1|fL|80.0-100.0|~N|||F[CR]OBX|26|NM|785-6^MCH^LN||30.0|pg|27.0-34.0|~N|||F[CR]OBX|27|NM|786-4^MCHC^LN||33.3|g/dL|32.0-36.0|~N|||F[CR]OBX|28|NM|788-0^RDW-CV^LN||13.8|%|11.0-16.0|~N|||F[CR]OBX|29|NM|21000-5^RDW-SD^LN||43.8|fL|35.0-56.0|~N|||F[CR]OBX|30|NM|777-3^PLT^LN||58|10*3/uL|100-300|L~A|||F[CR]OBX|31|NM|32623-1^MPV^LN||9.9|fL|6.5-12.0|~N|||F[CR]OBX|32|NM|32207-3^PDW-SD^LN||10.9|fL|9.0-17.0|~N|||F[CR]OBX|33|NM|11090^PDW-CV^LN||15.8|%|10.0-17.9|~N|||F[CR]OBX|34|NM|11003^PCT^99MRC||0.057|%|0.108-0.282|L~A|||F[CR]OBX|35|NM|48386-7^P-LCR^LN||26.9|%|11.0-45.0|~N|||F[CR]OBX|36|NM|34167-7^P-LCC^LN||16|10*9/L|30-90|L~A|||F"
    structured_result = parse_hl7_message(raw_message)
    with open("parsed_result.json", "w") as out:
        json.dump(structured_result, out, indent=2)
    print("HL7 parsed successfully to parsed_result.json")
    print("\nSample parsed data:")
    print(f"Message Type: {structured_result['msh'].get('message_type', 'N/A')}")
    print(f"Sending Application: {structured_result['msh'].get('sending_app', 'N/A')}")
    print(f"Number of OBX results: {len(structured_result['obx_results'])}")
    if structured_result['obx_results']:
        print(f"First test result: {structured_result['obx_results'][0]['test_name']} = {structured_result['obx_results'][0]['value']}")
    # Now read, flatten, and log the OBX results
    with open("parsed_result.json", "r") as infile:
        parsed = json.load(infile)
    cleaned_obx_results = [flatten_obx_result(obx) for obx in parsed.get("obx_results", [])]
    for obx in cleaned_obx_results:
        logging.info(f"Cleaned OBX result: {obx}")