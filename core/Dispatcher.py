from Analyzers.Bs240.Astm.Parser.Astmparser import enhanced_decode
from core.RecordDispatcher import ExtendedBaseRecordsDispatcher
from utility import setup_logger

log = setup_logger(
    file_path=__file__,
    log_file="logs/core.log",
    separate_levels=True
)

class MyDispatcher(ExtendedBaseRecordsDispatcher):

    def __init__(self, encoding=None):
        super(MyDispatcher, self).__init__(encoding)

    def __call__(self, message):
        try:

            try:
                recordsList = enhanced_decode(message, self.encoding)
            except ValueError as ve:
                raise ve

            if not isinstance(recordsList, list):
                raise TypeError("Dispatcher: decode_record did not return a list.")
            
            for record in recordsList:
                if not record:
                    continue

                record_type = record[0]
                data_dict = self.wrap(record, record_type)
                
                try:
                    wrapperClass = self.wrappers[record_type]
                    wrapperObj = wrapperClass()
                except KeyError:
                    raise KeyError(f"No wrapper found for record type {record_type}")

                for key, value in data_dict.items():
                    if hasattr(wrapperObj, key):
                        try:
                            setattr(wrapperObj, key, value)
                        except Exception as attr_e:
                            raise Exception(f"Failed to set {key} = {value}: {attr_e}")
                    else:
                        log.warning(f"Attribute {key} not found in wrapper object")
                
                return wrapperObj
        except Exception as e:
            log.error("Unexpected error during decoding", exc_info=e)
            raise

    def wrap(self, record, record_type):
        if record_type in self.wrappers:
            fields = [name for name, _ in self.wrappers[record_type]._fields]
            return dict(zip(fields, record))
    
    # def debugg(self, record, record_type, data_dict):
    #     wrapper_cls = self.wrappers[record_type]
    #     # for name, field in wrapper_cls._fields:
    #         # field_type = type(field).__name__
    #         # default = getattr(field, 'default', None)
    #         # required = getattr(field, 'required', None)
        
    #         # If it's a component, dive into the inner structure
    #         # if isinstance(field, ComponentField):
    #         #     if hasattr(field.mapping, '_fields'):
    #         #         for subname, subfield in field.mapping._fields:
    #         #             sub_type = type(subfield).__name__
    #         #             sub_default = getattr(subfield, 'default', None)
    #     expected_fields = [name for name, _ in self.wrappers[record_type]._fields]

    def on_header(self, record):
        """Header record handler."""
        self._default_handler(record)

    def on_comment(self, record):
        """Comment record handler."""
        self._default_handler(record)

    def on_patient(self, record):
        """Patient record handler."""
        self._default_handler(record)

    def on_order(self, record):
        """Order record handler."""
        self._default_handler(record)

    def on_result(self, record):
        """Result record handler."""
        self._default_handler(record)

    def on_query(self, record):
        """Query reocrd handler to get patient info from LIS 
            Analyzer => host
        """
        self._default_handler(record)

    def on_terminator(self, record):
        """Terminator record handler."""
        self._default_handler(record)

    def on_unknown(self, record):
        """Raise Error and log the error"""
        self._default_handler(record)
    
    def _default_handler(self, record):
        log.warning('Received Machine Record: %s', record)