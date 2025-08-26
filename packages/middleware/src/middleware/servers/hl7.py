import asyncio
from datetime import datetime
from typing import Callable, Optional

VT = b"\x0b"  # <SB>
FS = b"\x1c"  # <FS>
CR = b"\x0d"  # <CR>

GuiLogger = Optional[Callable[[str], None]]

async def start_hl7_server(host: str, port: int, gui_log: GuiLogger = None):
	server = await asyncio.start_server(lambda r, w: handle_client(r, w, gui_log), host, port)
	addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
	if gui_log:
		gui_log(f"HL7 server listening on {addrs}")
	async with server:
		await server.serve_forever()


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, gui_log: GuiLogger = None):
	peer = writer.get_extra_info('peername')
	if gui_log:
		gui_log(f"HL7 connection from {peer}")
	try:
		while True:
			chunk = await reader.readuntil(FS + CR)
			if not chunk:
				break
			if chunk.startswith(VT) and chunk.endswith(FS + CR):
				payload = chunk[1:-2]
				if gui_log:
					gui_log(f"[RECV HL7] {payload[:80]!r}...")
				await forward_to_processor(payload)
				# MLLP ACK
				writer.write(VT + b"MSH|^~\\&|LIS|ACK|..." + FS + CR)
				await writer.drain()
		else:
			break
	except asyncio.IncompleteReadError:
		pass
	finally:
		writer.close()
		await writer.wait_closed()
		if gui_log:
			gui_log(f"HL7 connection closed {peer}")


async def forward_to_processor(raw: bytes):
	from middleware.processor import process_and_send
	await process_and_send({"hl7": raw.decode(errors='ignore'), "ts": datetime.utcnow().isoformat()}, "http://127.0.0.1:8000/v1/data") 