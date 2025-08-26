# import asyncio
# from hl7.mllp import start_hl7_server,HL7StreamReader, HL7StreamWriter
# from middleware.processor import HL7CBCProcessor

# processor = HL7CBCProcessor()

# import asyncio
# from hl7.mllp import HL7StreamReader, HL7StreamWriter
# # from middleware.processor import HL7CBCProcessor # Your processor import

# # processor = HL7CBCProcessor() # Your processor instance

# async def handle_hl7_connection(reader: HL7StreamReader, writer: HL7StreamWriter):
#     peer = writer.get_extra_info('peername')
#     print(f"Connection from {peer}")

#     try:
#         while not writer.is_closing():
#             message = None  # Initialize message to None at the start of each loop
#             try:
#                 # BLOCK 1: Try to read a message from the network.
#                 # This is where connection errors are most likely.
#                 message = await reader.readmessage()

#             except asyncio.IncompleteReadError:
#                 # This is a CONNECTION error. The client disconnected.
#                 # It's normal for health checks or if the client closes the connection.
#                 print(f"Client {peer} disconnected gracefully.")
#                 break # Exit the while loop for this connection.

#             # If we get here, 'message' is guaranteed to exist.
#             try:
#                 # BLOCK 2: Try to process the message.
#                 # Errors here are related to the message content itself.
#                 print(f"Message received: {str(message)[:80]}")
#                 msg_str = str(message)

#                 # Your custom processing logic
#                 # cbc_result = processor.extract_cbc_data(msg_str)
#                 # print(f"CBC structured result: {cbc_result}")

#                 # Create and send a positive acknowledgment (ACK)
#                 ack = message.create_ack(ack_code='AA')
#                 writer.writemessage(ack)
#                 await writer.drain()
#                 print("ACK sent.")

#             except Exception as e:
#                 # This is a PROCESSING error. We have a message, but couldn't process it.
#                 print(f"Error processing message from {peer}: {e}")
                
#                 # It is now SAFE to create a NACK because 'message' exists.
#                 if message:
#                     nack = message.create_ack(ack_code='AE', err_msg=str(e))
#                     writer.writemessage(nack)
#                     await writer.drain()
#                     print("NACK sent due to processing error.")
                
#                 # Depending on the error, you might want to continue or break.
#                 # For a critical processing error, breaking is often safer.
#                 break

#     finally:
#         if not writer.is_closing():
#             writer.close()
#             await writer.wait_closed()
#         print(f"Connection with {peer} is fully closed.")

# async def main():
#     host = '127.0.0.1'
#     port = 15200
#     print(f"Starting HL7 MLLP server on {host}:{port}...")
#     server = await start_hl7_server(handle_hl7_connection, host=host, port=port)
#     async with server:
#         await server.serve_forever()

# if __name__ == "__main__":
#     asyncio.run(main())

# new_hl7_server.py

import asyncio
import threading
from hl7.mllp import start_hl7_server, HL7StreamReader, HL7StreamWriter

class HL7Server:
    """
    A manageable HL7 MLLP server that runs in a separate thread.
    """
    def __init__(self, host: str, port: int, message_queue: asyncio.Queue):
        self.host = host
        self.port = port
        self.message_queue = message_queue
        self.loop = None
        self.server_task = None
        self._thread = None

    async def _handle_connection(self, reader: HL7StreamReader, writer: HL7StreamWriter):
        """ The internal connection handler. """
        peer = writer.get_extra_info('peername')
        print(f"Connection from {peer}")
        try:
            while not writer.is_closing():
                message = None
                try:
                    message = await reader.readmessage()
                    # ### CRITICAL CHANGE ###
                    # Instead of processing, put the raw message string into the queue.
                    await self.message_queue.put(str(message))

                    # Create and send ACK
                    ack = message.create_ack(ack_code='AA')
                    writer.writemessage(ack)
                    await writer.drain()
                    print(f"ACK sent to {peer}.")

                except asyncio.IncompleteReadError:
                    print(f"Client {peer} disconnected gracefully.")
                    break
                except Exception as e:
                    print(f"Error processing message from {peer}: {e}")
                    if message:
                        nack = message.create_ack(ack_code='AE', err_msg=str(e))
                        writer.writemessage(nack)
                        await writer.drain()
                    break
        finally:
            print(f"Connection with {peer} is fully closed.")

    async def _run_server(self):
        """ Coroutine to start and run the server forever. """
        server = await start_hl7_server(self._handle_connection, host=self.host, port=self.port)
        print(f"HL7 server started on {self.host}:{self.port}")
        async with server:
            await server.serve_forever()

    def _start_loop(self):
        """ Runs the asyncio event loop in the new thread. """
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.server_task = self.loop.create_task(self._run_server())
        try:
            self.loop.run_forever()
        finally:
            self.loop.close()

    def start(self):
        """ Starts the server in a new thread. """
        if self._thread is not None:
            print("Server is already running.")
            return
        print("Starting HL7 server thread...")
        self._thread = threading.Thread(target=self._start_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """ Stops the server gracefully from the main thread. """
        if self.loop and self.server_task:
            print("Stopping HL7 server...")
            # Use thread-safe call to cancel the task in the other thread's loop
            self.loop.call_soon_threadsafe(self.server_task.cancel)
            # Use thread-safe call to stop the loop itself
            self.loop.call_soon_threadsafe(self.loop.stop)
            self._thread.join() # Wait for the thread to finish
            self._thread = None
            print("HL7 server stopped.")