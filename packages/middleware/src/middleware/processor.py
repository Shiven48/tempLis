import hl7
import re
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
import json


@dataclass
class CBCResult:
    """Enhanced data class to store structured CBC results"""
    specimen_id: str = "Unknown"
    message_control_id: str = "Unknown"
    test_datetime: str = "Unknown"
    analyzer_info: str = "Unknown"
    
    # Complete Blood Count - Main Parameters
    wbc: Optional[float] = None          # White Blood Cell Count
    rbc: Optional[float] = None          # Red Blood Cell Count  
    hgb: Optional[float] = None          # Hemoglobin
    hct: Optional[float] = None          # Hematocrit
    plt: Optional[float] = None          # Platelet Count
    
    # Red Cell Indices
    mcv: Optional[float] = None          # Mean Corpuscular Volume
    mch: Optional[float] = None          # Mean Corpuscular Hemoglobin
    mchc: Optional[float] = None         # Mean Corpuscular Hemoglobin Concentration
    rdw_cv: Optional[float] = None       # Red Cell Distribution Width (CV)
    rdw_sd: Optional[float] = None       # Red Cell Distribution Width (SD)
    
    # Differential Count (Percentages)
    neu_pct: Optional[float] = None      # Neutrophils %
    lym_pct: Optional[float] = None      # Lymphocytes %
    mon_pct: Optional[float] = None      # Monocytes %
    eos_pct: Optional[float] = None      # Eosinophils %
    bas_pct: Optional[float] = None      # Basophils %
    
    # Differential Count (Absolute numbers)
    neu_abs: Optional[float] = None      # Neutrophils Absolute
    lym_abs: Optional[float] = None      # Lymphocytes Absolute
    mon_abs: Optional[float] = None      # Monocytes Absolute
    eos_abs: Optional[float] = None      # Eosinophils Absolute
    bas_abs: Optional[float] = None      # Basophils Absolute
    
    # Atypical cells
    aly_pct: Optional[float] = None      # Atypical Lymphocytes %
    aly_abs: Optional[float] = None      # Atypical Lymphocytes Absolute
    lic_pct: Optional[float] = None      # Large Immature Cells %
    lic_abs: Optional[float] = None      # Large Immature Cells Absolute
    
    # Platelet indices
    mpv: Optional[float] = None          # Mean Platelet Volume
    pdw_sd: Optional[float] = None       # Platelet Distribution Width (SD)
    pdw_cv: Optional[float] = None       # Platelet Distribution Width (CV)
    pct: Optional[float] = None          # Plateletcrit
    p_lcr: Optional[float] = None        # Platelet Large Cell Ratio
    p_lcc: Optional[float] = None        # Platelet Large Cell Count
    
    # Quality control and flags
    abnormal_flags: List[str] = field(default_factory=list)
    clinical_alerts: List[str] = field(default_factory=list)
    critical_values: List[str] = field(default_factory=list)
    morphology_flags: List[str] = field(default_factory=list)
    
    # Raw data for debugging
    raw_obx_data: Dict[str, Any] = field(default_factory=dict)


class HL7CBCProcessor:
    """Enhanced HL7 processor with comprehensive CBC analysis"""
    
    # Expanded LOINC codes mapping - including all Erba analyzer codes
    LOINC_MAPPING = {
        # Main CBC Parameters
        '6690-2': 'wbc',      # White Blood Cell Count
        '789-8': 'rbc',       # Red Blood Cell Count
        '718-7': 'hgb',       # Hemoglobin
        '4544-3': 'hct',      # Hematocrit
        '777-3': 'plt',       # Platelet Count
        
        # Red Cell Indices
        '787-2': 'mcv',       # Mean Corpuscular Volume
        '785-6': 'mch',       # Mean Corpuscular Hemoglobin
        '786-4': 'mchc',      # Mean Corpuscular Hemoglobin Concentration
        '788-0': 'rdw_cv',    # Red Cell Distribution Width (CV)
        '21000-5': 'rdw_sd',  # Red Cell Distribution Width (SD)
        
        # Differential Count (Percentages)
        '770-8': 'neu_pct',   # Neutrophils %
        '736-9': 'lym_pct',   # Lymphocytes %
        '5905-5': 'mon_pct',  # Monocytes %
        '713-8': 'eos_pct',   # Eosinophils %
        '706-2': 'bas_pct',   # Basophils %
        
        # Differential Count (Absolute)
        '751-8': 'neu_abs',   # Neutrophils Absolute
        '731-0': 'lym_abs',   # Lymphocytes Absolute
        '742-7': 'mon_abs',   # Monocytes Absolute
        '711-2': 'eos_abs',   # Eosinophils Absolute
        '704-7': 'bas_abs',   # Basophils Absolute
        
        # Atypical cells
        '26477-0': 'aly_abs', # Atypical Lymphocytes Absolute
        '13046-8': 'aly_pct', # Atypical Lymphocytes %
        
        # Platelet indices
        '32623-1': 'mpv',     # Mean Platelet Volume
        '32207-3': 'pdw_sd',  # Platelet Distribution Width (SD)
        '48386-7': 'p_lcr',   # Platelet Large Cell Ratio
        '34167-7': 'p_lcc',   # Platelet Large Cell Count
    }
    
    # Erba-specific codes (99MRC system)
    ERBA_MAPPING = {
        '11001': 'lic_abs',   # Large Immature Cells Absolute
        '11002': 'lic_pct',   # Large Immature Cells %
        '11003': 'pct',       # Plateletcrit
        '11090': 'pdw_cv',    # Platelet Distribution Width (CV)
    }
    
    # Combined mapping
    ALL_MAPPINGS = {**LOINC_MAPPING, **ERBA_MAPPING}
    
    # Enhanced reference ranges with age/gender considerations
    REFERENCE_RANGES = {
        'wbc': (4.0, 10.0, '×10³/μL'),
        'rbc': (3.5, 5.5, '×10⁶/μL'),
        'hgb': (11.0, 16.0, 'g/dL'),
        'hct': (37.0, 54.0, '%'),
        'plt': (100, 300, '×10³/μL'),
        'mcv': (80.0, 100.0, 'fL'),
        'mch': (27.0, 34.0, 'pg'),
        'mchc': (32.0, 36.0, 'g/dL'),
        'rdw_cv': (11.0, 16.0, '%'),
        'rdw_sd': (35.0, 56.0, 'fL'),
        'neu_pct': (50.0, 70.0, '%'),
        'lym_pct': (20.0, 40.0, '%'),
        'mon_pct': (3.0, 12.0, '%'),
        'eos_pct': (0.5, 5.0, '%'),
        'bas_pct': (0.0, 1.0, '%'),
        'neu_abs': (2.0, 7.0, '×10³/μL'),
        'lym_abs': (0.8, 4.0, '×10³/μL'),
        'mon_abs': (0.12, 1.2, '×10³/μL'),
        'eos_abs': (0.02, 0.5, '×10³/μL'),
        'bas_abs': (0.0, 0.1, '×10³/μL'),
        'aly_pct': (0.0, 2.0, '%'),
        'aly_abs': (0.0, 0.2, '×10³/μL'),
        'lic_pct': (0.0, 2.5, '%'),
        'lic_abs': (0.0, 0.2, '×10³/μL'),
        'mpv': (6.5, 12.0, 'fL'),
        'pdw_sd': (9.0, 17.0, 'fL'),
        'pdw_cv': (10.0, 17.9, '%'),
        'pct': (0.108, 0.282, '%'),
        'p_lcr': (11.0, 45.0, '%'),
        'p_lcc': (30, 90, '×10⁹/L'),
    }
    
    # Critical value thresholds
    CRITICAL_VALUES = {
        'wbc': {'low': 2.0, 'high': 30.0},
        'hgb': {'low': 7.0, 'high': 20.0},
        'hct': {'low': 20.0, 'high': 60.0},
        'plt': {'low': 50, 'high': 1000},
        'neu_abs': {'low': 1.0, 'high': 20.0},
    }
    
    def process_hl7_file(self, file_path: str) -> List[str]:
        """Enhanced file processing with better transaction handling"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            # Handle multiple separator types
            # First try Form Feed character
            if '\\x0C' in content:
                transactions = content.split('\\x0C')
            elif '[FS]' in content:
                transactions = content.split('[FS]')
            else:
                # Try to split on multiple MSH segments
                transactions = re.split(r'(?=\\[VT\\]MSH)', content)
                
        except Exception as e:
            print(f"ERROR reading file: {e}")
            return []

        rebuilt_messages = []
        
        for i, transaction in enumerate(transactions):
            if not transaction.strip():
                continue
            
            # Enhanced cleaning - handle all control characters
            clean_transaction = re.sub(r'\\[VT\\]|\\[CR\\]|\\[FS\\]', '\\r', transaction)
            clean_transaction = re.sub(r'[\\x00-\\x1F\\x7F]', '\\r', clean_transaction)
            
            # Better segment reconstruction
            segmented = re.sub(r'([A-Z]{3}\\|)', r'\\r\\1', clean_transaction)
            
            # Extract only ORU messages
            final_segments = []
            in_oru = False
            
            for segment in segmented.split('\\r'):
                segment = segment.strip()
                if not segment:
                    continue
                
                if segment.startswith('MSH'):
                    in_oru = 'ORU^R01' in segment
                
                if in_oru and re.match(r'^[A-Z]{3}\\|', segment):
                    final_segments.append(segment)
            
            if final_segments:
                rebuilt_messages.append('\\r'.join(final_segments))
        
        return rebuilt_messages

    def extract_cbc_data(self, hl7_message: str) -> Optional[CBCResult]:
        """Enhanced CBC data extraction with comprehensive error handling"""
        try:
            h = hl7.parse(hl7_message)
            
            result = CBCResult()
            
            # Extract message header information
            self._extract_header_info(h, result)
            
            # Process all OBX segments
            obx_segments = h.segments('OBX')
            processed_count = 0
            
            for obx in obx_segments:
                if self._process_obx_segment(obx, result):
                    processed_count += 1
            
            if processed_count == 0:
                return None
            
            # Post-processing analysis
            self._calculate_derived_values(result)
            self._analyze_clinical_significance(result)
            
            return result
            
        except Exception as e:
            print(f"Error processing HL7 message: {e}")
            return None

    def _extract_header_info(self, h, result: CBCResult):
        """Extract header information from MSH and OBR segments"""
        try:
            msh = h.segment('MSH')
            if msh and len(msh) > 10:
                result.message_control_id = str(msh[10]) if msh else "Unknown"
                if len(msh) > 3:
                    result.analyzer_info = f"{msh[3]} {msh[4]}" if msh and msh else "Unknown"
            
            obr = h.segment('OBR')
            if obr:
                if len(obr) > 3 and obr[3]:
                    result.specimen_id = str(obr)
                if len(obr) > 6 and obr:
                    result.test_datetime = self._parse_datetime(str(obr))
                elif len(obr) > 7 and obr:
                    result.test_datetime = self._parse_datetime(str(obr))
                    
        except Exception as e:
            print(f"Warning: Error extracting header info: {e}")

    def _process_obx_segment(self, obx, result: CBCResult) -> bool:
        """Enhanced OBX processing with comprehensive field handling"""
        try:
            if not obx or len(obx) < 6:
                return False
            
            # Extract fields safely
            data_type = self._safe_extract(obx, 2)
            test_info = self._safe_extract(obx, 3)
            value = self._safe_extract(obx, 5)
            units = self._safe_extract(obx, 6)
            ref_range = self._safe_extract(obx, 7)
            abnormal_flag = self._safe_extract(obx, 8)
            
            if not test_info or not value:
                return False
            
            # Extract test code
            test_code = self._extract_test_code(test_info)
            if not test_code:
                return False
            
            # Store raw data for debugging
            result.raw_obx_data[test_code] = {
                'value': value,
                'units': units,
                'ref_range': ref_range,
                'abnormal_flag': abnormal_flag
            }
            
            # Process numeric values
            if data_type == 'NM' and test_code in self.ALL_MAPPINGS:
                return self._process_numeric_value(test_code, value, abnormal_flag, result)
            
            # Process text flags and alerts
            elif data_type == 'IS' and value in ['T', 'True', 'Y', 'Yes']:
                return self._process_text_flag(test_info, result)
            
            return False
            
        except Exception as e:
            print(f"Warning: Error processing OBX segment: {e}")
            return False

    def _safe_extract(self, segment, index):
        """Safely extract field from HL7 segment"""
        try:
            if len(segment) <= index:
                return None
            
            field = segment[index]
            if not field:
                return None
            
            # Handle nested structures
            if isinstance(field, list):
                if len(field) > 0:
                    return field[0] if not isinstance(field, list) else field if len(field) > 0 else None
            
            return str(field) if field else None
            
        except Exception:
            return None

    def _extract_test_code(self, test_info):
        """Extract test code from complex test info structure"""
        try:
            if isinstance(test_info, str):
                return test_info
            elif isinstance(test_info, list) and len(test_info) > 0:
                if isinstance(test_info[0], list) and len(test_info) > 0:
                    return str(test_info)
                else:
                    return str(test_info)
            return None
        except Exception:
            return None

    def _process_numeric_value(self, test_code: str, value_str: str, abnormal_flag: str, result: CBCResult) -> bool:
        """Process numeric test values"""
        try:
            # Clean and convert value
            clean_value = re.sub(r'[^\\d.-]', '', str(value_str))
            if not clean_value:
                return False
            
            numeric_value = float(clean_value)
            field_name = self.ALL_MAPPINGS[test_code]
            setattr(result, field_name, numeric_value)
            
            # Record abnormal flags
            if abnormal_flag and abnormal_flag in ['H', 'L', 'A', 'HH', 'LL']:
                flag_desc = self._get_flag_description(abnormal_flag)
                result.abnormal_flags.append(f"{field_name}: {flag_desc}")
            
            # Check for critical values
            if field_name in self.CRITICAL_VALUES:
                self._check_critical_value(field_name, numeric_value, result)
            
            return True
            
        except (ValueError, TypeError):
            return False

    def _process_text_flag(self, test_info, result: CBCResult) -> bool:
        """Process text flags and morphology alerts"""
        try:
            # Extract test name
            test_name = "Unknown Alert"
            if isinstance(test_info, list) and len(test_info) > 0:
                comp = test_info[0]          # first repetition
                if isinstance(comp, list):
                    test_name = str(comp[1] or comp)  # use name if present, else code
                else:
                    test_name = str(comp)
            
            # Categorize alerts
            if any(keyword in test_name.lower() for keyword in ['morphology', 'cell', 'blast', 'atypical']):
                result.morphology_flags.append(test_name)
            else:
                result.clinical_alerts.append(test_name)
            
            return True
            
        except Exception:
            return False

    def _get_flag_description(self, flag: str) -> str:
        """Convert flag codes to descriptions"""
        flag_map = {
            'H': 'High',
            'L': 'Low', 
            'A': 'Abnormal',
            'HH': 'Critical High',
            'LL': 'Critical Low'
        }
        return flag_map.get(flag, flag)

    def _check_critical_value(self, field_name: str, value: float, result: CBCResult):
        """Check if value is critical and needs immediate attention"""
        if field_name not in self.CRITICAL_VALUES:
            return
        
        thresholds = self.CRITICAL_VALUES[field_name]
        
        if value <= thresholds['low']:
            result.critical_values.append(f"CRITICAL LOW {field_name.upper()}: {value}")
        elif value >= thresholds['high']:
            result.critical_values.append(f"CRITICAL HIGH {field_name.upper()}: {value}")

    def _calculate_derived_values(self, result: CBCResult):
        """Calculate derived parameters and validate consistency"""
        try:
            # Calculate differential ratios if absolute counts are available
            if result.wbc and result.wbc > 0:
                for pct_field, abs_field in [('neu_pct', 'neu_abs'), ('lym_pct', 'lym_abs'), 
                                           ('mon_pct', 'mon_abs'), ('eos_pct', 'eos_abs')]:
                    pct_val = getattr(result, pct_field)
                    abs_val = getattr(result, abs_field)
                    
                    if pct_val and not abs_val:
                        calculated_abs = (pct_val / 100.0) * result.wbc
                        setattr(result, abs_field, round(calculated_abs, 2))
                    elif abs_val and not pct_val:
                        calculated_pct = (abs_val / result.wbc) * 100.0
                        setattr(result, pct_field, round(calculated_pct, 1))
                        
        except Exception as e:
            print(f"Warning: Error calculating derived values: {e}")

    def _analyze_clinical_significance(self, result: CBCResult):
        """Advanced clinical analysis and interpretation"""
        try:
            # Anemia classification
            if result.hgb and result.mcv:
                if result.hgb < self.REFERENCE_RANGES['hgb'][0]:
                    if result.mcv < self.REFERENCE_RANGES['mcv']:
                        result.clinical_alerts.append("Microcytic Anemia (consider iron deficiency)")
                    elif result.mcv > self.REFERENCE_RANGES['mcv'][1]:
                        result.clinical_alerts.append("Macrocytic Anemia (consider B12/folate deficiency)")
                    else:
                        result.clinical_alerts.append("Normocytic Anemia")
            
            # Infection patterns
            if result.wbc and result.neu_pct:
                if result.wbc > self.REFERENCE_RANGES['wbc'][1]:
                    if result.neu_pct > self.REFERENCE_RANGES['neu_pct']:
                        result.clinical_alerts.append("Neutrophilic Leukocytosis (suggests bacterial infection)")
                    elif result.lym_pct and result.lym_pct > self.REFERENCE_RANGES['lym_pct'][1]:
                        result.clinical_alerts.append("Lymphocytic Leukocytosis (suggests viral infection)")
            
            # Thrombocytopenia severity
            if result.plt:
                if result.plt < 20:
                    result.clinical_alerts.append("Severe Thrombocytopenia - HIGH bleeding risk")
                elif result.plt < 50:
                    result.clinical_alerts.append("Moderate Thrombocytopenia - Increased bleeding risk")
                elif result.plt < 100:
                    result.clinical_alerts.append("Mild Thrombocytopenia")
                    
        except Exception as e:
            print(f"Warning: Error in clinical analysis: {e}")

    def _parse_datetime(self, datetime_str: str) -> str:
        """Enhanced datetime parsing"""
        if not datetime_str or len(datetime_str) < 8:
            return "Unknown"
        
        try:
            clean_dt = re.sub(r'[^\\d]', '', datetime_str)
            
            if len(clean_dt) >= 14:
                dt = datetime.strptime(clean_dt[:14], "%Y%m%d%H%M%S")
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            elif len(clean_dt) >= 8:
                dt = datetime.strptime(clean_dt[:8], "%Y%m%d")
                return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
        
        return datetime_str