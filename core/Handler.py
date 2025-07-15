from astm.protocol import ASTMProtocol 
from astm.constants import CRLF, EOT, ACK, ETB, NAK
from astm.exceptions import NotAccepted, InvalidState
from utility import setup_logger

log = setup_logger(
    file_path=__file__,
    log_file="logs/core.log",
    separate_levels=True
)

"""
    This class/layer is used to handle the overall communication flow of the astm standard
    all the request and response triggers are handled in this layer

    e.g :- 
    1) The analyzer starts the session using the ENQ then we handle it using 'on_enq' method
    2) The analyzer starts giving astm message then it is handled using 'on_messge' method
    3) Suppose in case a time out happens then it is handled using 'on_timeout' method

    NOTE:- All of the flow us being controlled from parent class ASTMProtocol like sending
           and receiving the bytes
"""
class RequestHandler(ASTMProtocol):

    def __init__(self, sock, dispatcher, encoding, timeout=None):
        super(RequestHandler, self).__init__(sock, timeout=timeout)
        self._chunks = []
        host, port = sock.getpeername() if sock is not None else (None, None)
        self.client_info = {'host': host, 'port': port}
        self.dispatcher = dispatcher
        self._is_transfer_state = False
        self.terminator = 1
        self.encoding = encoding

    def on_enq(self):
        if not self._is_transfer_state:
            self._subordinate_mode = True
            log.debug("Received the enq on server")
            self._is_transfer_state = True
            self.terminator = [CRLF, EOT, ETB]
            return ACK
        else:
            log.error('ENQ is not expected')
            return NAK
    
    def on_ack(self):
        raise NotAccepted('Server should not be ACKed.')

    def on_nak(self):
        raise NotAccepted('Server should not be NAKed.')

    def on_eot(self):
        if self._is_transfer_state:
            self._is_transfer_state = False
            self.terminator = 1
            return ACK
        else:
            raise InvalidState('Server is not ready to accept EOT message.')
            
    def close_socket_connection(self):
        if self._is_transfer_state:
            self._is_transfer_state = False
            self.terminator = 1
            return ACK
        else:
            raise InvalidState('Server is not ready to accept EOT message.')
        
    def on_etb(self):
        pass

    def on_message(self):
        if not self._is_transfer_state:
            self.discard_input_buffers()
            return NAK
        try:
            if isinstance(self._last_recv_data, str):
                self._last_recv_data = self._last_recv_data.strip().encode(self.encoding)
            
            self.dispatcher(self._last_recv_data)
            return ACK
        except ValueError as ve:
            log.exception("Value Error occured", ve.with_traceback())
            return NAK
        except TypeError as te:
            log.exception("Type Error occured", te)
            return NAK
        except KeyError as ke:
            log.exception("Key Error occured", ke)
            return NAK
        except Exception as e:
            log.exception("Error processing ASTM message", e)
            return NAK

    def discard_input_buffers(self):
        self._chunks = []
        return super(RequestHandler, self).discard_input_buffers()

    def on_timeout(self):
        """Closes connection on timeout."""
        super(RequestHandler, self).on_timeout()
        self.close()