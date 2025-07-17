"""
Main ASTM/HL7 Server with Profile-based Configuration
"""
import asyncio
import logging
from astm.server import Server
from astm.constants import ENCODING
from dispatcher import Disp
from profile_factory import ProfileFactory
from logger import logger


logger = logging.getLogger(__name__)

class ProfileBasedServer:
    """Server that initializes based on machine profile"""
    
    def __init__(self, machine_type: str, config_path: str = "config.json"):
        self.machine_type = machine_type
        self.profile = ProfileFactory.create_profile(machine_type, config_path)
        self.protocol_type = self.profile.get_protocol_type()
        
        logger.info(f"Initializing server for {machine_type}")
        logger.info(f"Protocol: {self.protocol_type}")
        
    async def _start_socket_server(self):
        """Start TCP socket server"""
        host = 'localhost'
        port = 15200

        def dispatcher_factory(encoding=None):
            return Disp(encoding or ENCODING, self.machine_type, self.profile)

        logger.info(f"Starting socket server on {host}:{port}")
        
        server = Server(
            host=host,
            port=port,
            dispatcher=dispatcher_factory,
            timeout=30,
            encoding=ENCODING
        )
        
        await server.serve_forever()

def read_analyzer_type() -> str:
    """ Reads machine from `current_machine.txt` """
    with open(file="current_machine.txt", mode="r") as file:
        return file.read()


async def main():
    """Main entry point"""
    # You can change this to any supported machine type
    machine_type:str = read_analyzer_type()
    logger.info(f"The selected analyzer profile(machine_type) is: {machine_type}")
    
    try:
        server = ProfileBasedServer(machine_type)
        await server._start_socket_server()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())