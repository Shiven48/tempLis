import asyncio
from datetime import datetime
from typing import Callable, Optional

ENQ = b"\x05"
ACK = b"\x06"
NAK = b"\x15"
EOT = b"\x04"

GuiLogger = Optional[Callable[[str], None]]

async def start_astm_server(host: str, port: int, gui_log: GuiLogger = None):
	server = await asyncio.start_server(lambda r, w: handle_client(r, w, gui_log), host, port)
	addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
	if gui_log:
		gui_log(f"ASTM server listening on {addrs}")
	async with server:
		await server.serve_forever()


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, gui_log: GuiLogger = None):
	peer = writer.get_extra_info('peername')
	if gui_log:
		gui_log(f"ASTM connection from {peer}")

	# Simple ASTM state machine for ENQ/ACK
	try:
		while True:
			data = await reader.read(1)
			if not data:
				break
			if data == ENQ:
				writer.write(ACK)
				await writer.drain()
				if gui_log:
					gui_log("[RECV] ENQ -> [SEND] ACK")
				# Now read records until EOT in a naive way
				record = await reader.readuntil(EOT)
				payload = record[:-1]  # strip EOT
				if gui_log:
					gui_log(f"[RECV] RECORD {payload!r}")
				# TODO: decode ASTM frames and checksum
				await forward_to_processor(payload)
			else:
				# For unexpected bytes, send NAK
				writer.write(NAK)
				await writer.drain()
				if gui_log:
					gui_log(f"[SEND] NAK for {data!r}")
	except asyncio.IncompleteReadError:
		pass
	finally:
		writer.close()
		await writer.wait_closed()
		if gui_log:
			gui_log(f"ASTM connection closed {peer}")


async def forward_to_processor(raw: bytes):
	from middleware.processor import process_and_send
	await process_and_send({"raw": raw.decode(errors='ignore'), "ts": datetime.utcnow().isoformat()}, "http://127.0.0.1:8000/v1/data") 