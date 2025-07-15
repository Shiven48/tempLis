from core.Dispatcher import MyDispatcher
from core.Handler import RequestHandler
from astm.asynclib import Dispatcher, loop
from astm.constants import ENCODING
from utility import setup_logger
import errno
import socket

log = setup_logger(
    file_path=__file__,
    log_file="logs/core.log",
    separate_levels=True
)

class AstmServer(Dispatcher):
    """
        Server class that listens for client connections
    """

    dispatcher = MyDispatcher(encoding=ENCODING)
    def __init__(self, host='localhost', port=15200, request=None, encoding=None, timeout=None):
        super(AstmServer, self).__init__()
        self.host = host
        self.port = port
        self.encoding = encoding
        self.timeout = timeout
        self.requestHandler = request or RequestHandler
        self.configureConnection()

    def configureConnection(self):
        """Configure Socket Connection for the Server"""
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        if self.host and self.port:
            self.bind((self.host, self.port))
        else:
            raise ConnectionError(f"Disconnected or invalid socket state. Error code: {errno.ENOTCONN}")
        self.listen(5)

    def handle_accept(self):
        """Handle new client connections"""
        pair = self.accept()
        if pair is None:
            return
        sock, addr = pair
        log.info('New client connection from %s:%d', addr[0], addr[1])
        self.requestHandler(sock=sock, dispatcher=self.dispatcher, encoding=self.encoding, timeout=self.timeout)

    # def serve_forever(self, timeout=30.0):        
    def serve_forever(self, timeout=1.0):
        """Start the server and handle connections indefinitely"""
        try:
            loop(timeout=timeout)
        except KeyboardInterrupt:
            log.info('Server shutting down...')
        finally:
            log.info("closing the session from server")
            self.close()

if __name__ == '__main__':
    server = AstmServer(
            host='localhost',
            port=15200,
            encoding='latin-1'
    )    
    log.info("Server starting on localhost:15200")
    log.info("Press Ctrl+C to stop the server")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("\nServer stopped.")