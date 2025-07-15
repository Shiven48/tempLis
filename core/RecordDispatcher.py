from Analyzers.Bs240.Astm.Records.CommentRecord import ExtendedCommentRecord
from Analyzers.Bs240.Astm.Records.HeaderRecord import ExtendedHeaderRecord
from Analyzers.Bs240.Astm.Records.OrderRecord import ExtendedOrderRecord
from Analyzers.Bs240.Astm.Records.PatientRecord import ExtendedPatientRecord
from Analyzers.Bs240.Astm.Records.ResultRecord import ExtendedResultRecord
from Analyzers.Bs240.Astm.Records.TerminatorRecord import ExtendedTerminatorRecord
from Analyzers.Bs240.Astm.Records.QueryRecord import ExtendedQueryRecord
from astm.server import BaseRecordsDispatcher
from astm.codec import decode_record
from astm.constants import ENCODING
from utility import setup_logger

log = setup_logger(
    file_path=__file__,
    log_file="logs/core.log",
    separate_levels=True
)

class ExtendedBaseRecordsDispatcher(BaseRecordsDispatcher):
    encoding = ENCODING
    def __init__(self, encoding=None):
        self.encoding = encoding or self.encoding
        super(ExtendedBaseRecordsDispatcher, self).__init__(encoding=self.encoding)
        self.dispatch.update({
            'Q': self.on_query,
        })
        self.wrappers.update({
            'H': ExtendedHeaderRecord,
            'P': ExtendedPatientRecord,
            'O': ExtendedOrderRecord,
            'R': ExtendedResultRecord,
            'C': ExtendedCommentRecord,
            'Q': ExtendedQueryRecord,
            'L': ExtendedTerminatorRecord
        })

    def __call__(self, message):
        recordsList = decode_record(message, self.encoding)
        if not isinstance(recordsList, list):
            log.warning("Dispatcher: decode_record did not return a list.")
            return
        for record in recordsList:
            if not record:
                continue
            record_type = record[0]
            wrapped = self.wrap(record)
            self.dispatch.get(record_type, self.on_unknown)(wrapped)

    def wrap(self, record):
        recordType = record[0]
        if recordType in self.wrappers:
            return self.wrappers[recordType](*record)
        return record