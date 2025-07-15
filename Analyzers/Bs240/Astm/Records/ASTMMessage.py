class LISMessage:
    """
    A class to handle LIS (Laboratory Information System) messages
    with proper record structure and encoding/decoding capabilities.
    """
    
    def __init__(self):
        self.header = None
        self.patients = []
        self.orders = []
        self.results = []
        self.comments = []
        self.terminator = None
        
    def set_header(self, header_data):
        """Set the header record (single record)"""
        if isinstance(header_data, list) and len(header_data) > 0 and header_data[0] == 'H':
            self.header = header_data
        else:
            raise ValueError("Header must be a list starting with 'H'")
    
    def add_patient(self, patient_data):
        """Add a patient record"""
        if isinstance(patient_data, list) and len(patient_data) > 0 and patient_data[0] == 'P':
            self.patients.append(patient_data)
        else:
            raise ValueError("Patient record must be a list starting with 'P'")
    
    def add_order(self, order_data):
        """Add an order record"""
        if isinstance(order_data, list) and len(order_data) > 0 and order_data[0] == 'O':
            self.orders.append(order_data)
        else:
            raise ValueError("Order record must be a list starting with 'O'")
    
    def add_result(self, result_data):
        """Add a result record"""
        if isinstance(result_data, list) and len(result_data) > 0 and result_data[0] == 'R':
            self.results.append(result_data)
        else:
            raise ValueError("Result record must be a list starting with 'R'")
    
    def add_comment(self, comment_data):
        """Add a comment record"""
        if isinstance(comment_data, list) and len(comment_data) > 0 and comment_data[0] == 'C':
            self.comments.append(comment_data)
        else:
            raise ValueError("Comment record must be a list starting with 'C'")
    
    def set_terminator(self, terminator_data):
        """Set the terminator record (single record)"""
        if isinstance(terminator_data, list) and len(terminator_data) > 0 and terminator_data[0] == 'L':
            self.terminator = terminator_data
        else:
            raise ValueError("Terminator must be a list starting with 'L'")
    
    def _encode_field(self, field, component_separator='^', repeat_separator='\\'):
        """
        Encode a field that can be a string, None, or list of components
        """
        if field is None:
            return ''
        elif isinstance(field, str):
            return field
        elif isinstance(field, list):
            # Handle component separation
            encoded_components = []
            for component in field:
                if component is None:
                    encoded_components.append('')
                else:
                    encoded_components.append(str(component))
            return component_separator.join(encoded_components)
        else:
            return str(field)
    
    def _encode_record(self, record, field_separator='|', component_separator='^', repeat_separator='\\'):
        """
        Encode a single record (list) into a string
        """
        if not record:
            return ''
        
        encoded_fields = []
        for field in record:
            encoded_fields.append(self._encode_field(field, component_separator, repeat_separator))
        
        return field_separator.join(encoded_fields)
    
    def encode_to_string(self, field_separator='|', component_separator='^', repeat_separator='\\', record_separator='\r'):
        """
        Encode the entire LIS message to a string format
        """
        encoded_records = []
        
        # Encode header
        if self.header:
            encoded_records.append(self._encode_record(self.header, field_separator, component_separator, repeat_separator))
        
        # Encode patients
        for patient in self.patients:
            encoded_records.append(self._encode_record(patient, field_separator, component_separator, repeat_separator))
        
        # Encode orders
        for order in self.orders:
            encoded_records.append(self._encode_record(order, field_separator, component_separator, repeat_separator))
        
        # Encode results
        for result in self.results:
            encoded_records.append(self._encode_record(result, field_separator, component_separator, repeat_separator))
        
        # Encode comments
        for comment in self.comments:
            encoded_records.append(self._encode_record(comment, field_separator, component_separator, repeat_separator))
        
        # Encode terminator
        if self.terminator:
            encoded_records.append(self._encode_record(self.terminator, field_separator, component_separator, repeat_separator))
        
        return record_separator.join(encoded_records)
    
    def encode_to_bytes(self, field_separator='|', component_separator='^', repeat_separator='\\', record_separator='\r'):
        """
        Encode the entire LIS message to bytes
        """
        message_string = self.encode_to_string(field_separator, component_separator, repeat_separator, record_separator)
        return message_string.encode('utf-8')
    
    def frame_message(self, stx=b'\x02', etx=b'\x03', cr=b'\r', lf=b'\n', frame_individual=True):
        """
        Frame the message with control characters
        
        Args:
            stx: Start of Text character
            etx: End of Text character
            cr: Carriage Return
            lf: Line Feed
            frame_individual: If True, frame each record individually, else frame entire message
        """
        if frame_individual:
            # Frame each record individually
            framed_records = []
            
            if self.header:
                header_str = self._encode_record(self.header)
                framed_records.append(stx + header_str.encode() + etx + cr + lf)
            
            for patient in self.patients:
                patient_str = self._encode_record(patient)
                framed_records.append(stx + patient_str.encode() + etx + cr + lf)
            
            for order in self.orders:
                order_str = self._encode_record(order)
                framed_records.append(stx + order_str.encode() + etx + cr + lf)
            
            for result in self.results:
                result_str = self._encode_record(result)
                framed_records.append(stx + result_str.encode() + etx + cr + lf)
            
            for comment in self.comments:
                comment_str = self._encode_record(comment)
                framed_records.append(stx + comment_str.encode() + etx + cr + lf)
            
            if self.terminator:
                terminator_str = self._encode_record(self.terminator)
                framed_records.append(stx + terminator_str.encode() + etx + cr + lf)
            
            return b''.join(framed_records)
        else:
            # Frame entire message as one block
            message_bytes = self.encode_to_bytes()
            return stx + message_bytes + etx + cr + lf
    
    def get_all_records(self):
        """Get all records as a list"""
        all_records = []
        if self.header:
            all_records.append(self.header)
        all_records.extend(self.patients)
        all_records.extend(self.orders)
        all_records.extend(self.results)
        all_records.extend(self.comments)
        if self.terminator:
            all_records.append(self.terminator)
        return all_records
    
    def create_lis_obj(self, decoded_records):
        for record in decoded_records:
            if not record or len(record) == 0:
                continue
                
            record_type = record[0]
            
            if record_type == 'H':
                self.set_header(record)
            elif record_type == 'P':
                self.add_patient(record)
            elif record_type == 'O':
                self.add_order(record)
            elif record_type == 'R':
                self.add_result(record)
            elif record_type == 'C':
                self.add_comment(record)
            elif record_type == 'L':
                self.set_terminator(record)
        
        return self

    def __str__(self):
        """String representation of the LIS message"""
        return self.encode_to_string()
    
    def __repr__(self):
        """Detailed representation of the LIS message"""
        return f"LISMessage(header={bool(self.header)}, patients={len(self.patients)}, orders={len(self.orders)}, results={len(self.results)}, comments={len(self.comments)}, terminator={bool(self.terminator)})"
    
    @classmethod
    def from_decoded_records(cls, decoded_records):
        """
        Create LISMessage instance from decoded records (your decode function output)
        
        Args:
            decoded_records: List of decoded records from your decode function
        """
        lis_msg = cls()
        
        for record in decoded_records:
            if not record or len(record) == 0:
                continue
                
            record_type = record[0]
            print(record_type)
            
            if record_type == 'H':
                lis_msg.set_header(record)
            elif record_type == 'P':
                lis_msg.add_patient(record)
            elif record_type == 'O':
                lis_msg.add_order(record)
            elif record_type == 'R':
                lis_msg.add_result(record)
            elif record_type == 'C':
                lis_msg.add_comment(record)
            elif record_type == 'L':
                lis_msg.set_terminator(record)
        
        return lis_msg
    
    @classmethod
    def from_raw_message(cls, sample_records, decode_function, frame_function):
        """
        Create LISMessage instance from raw message using your decode and frame functions
        
        Args:
            sample_records: List of string records
            decode_function: Your decode function
            frame_function: Your frame_message_block function
        """
        try:
            block_framed = frame_function(sample_records)
            decoded_records = decode_function(block_framed)
            return cls.from_decoded_records(decoded_records)
        except Exception as e:
            raise ValueError(f"Failed to create LISMessage from raw message: {e}")
    
    def to_dict(self):
        """
        Convert LISMessage to dictionary for JSON serialization
        """
        def serialize_field(field):
            """Helper to serialize fields that might contain None or lists"""
            if field is None:
                return None
            elif isinstance(field, list):
                return [serialize_field(item) for item in field]
            else:
                return field
        
        def serialize_record(record):
            """Helper to serialize a complete record"""
            if record is None:
                return None
            return [serialize_field(field) for field in record]
        
        return {
            "message_type": "LIS",
            "header": serialize_record(self.header),
            "patients": [serialize_record(patient) for patient in self.patients],
            "orders": [serialize_record(order) for order in self.orders],
            "results": [serialize_record(result) for result in self.results],
            "comments": [serialize_record(comment) for comment in self.comments],
            "terminator": serialize_record(self.terminator),
            "record_counts": {
                "patients": len(self.patients),
                "orders": len(self.orders),
                "results": len(self.results),
                "comments": len(self.comments)
            }
        }
    
    @classmethod
    def from_dict(cls, data_dict):
        """
        Create LISMessage instance from dictionary (reverse of to_dict)
        """
        lis_msg = cls()
        
        if data_dict.get("header"):
            lis_msg.set_header(data_dict["header"])
            
        for patient in data_dict.get("patients", []):
            lis_msg.add_patient(patient)
            
        for order in data_dict.get("orders", []):
            lis_msg.add_order(order)
            
        for result in data_dict.get("results", []):
            lis_msg.add_result(result)
            
        for comment in data_dict.get("comments", []):
            lis_msg.add_comment(comment)
            
        if data_dict.get("terminator"):
            lis_msg.set_terminator(data_dict["terminator"])
            
        return lis_msg
    
    def to_json(self, indent=2):
        """
        Convert LISMessage to JSON string
        """
        import json
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_json(cls, json_string):
        """
        Create LISMessage instance from JSON string
        """
        import json
        data_dict = json.loads(json_string)
        return cls.from_dict(data_dict)