import socket
import threading
import re
import hashlib
import base64
import struct
from httpcodes import http_code_lookup
from log import log

def recv(socket, nbytes):
	'''
	Guarentee to receive nbytes of data
	'''
	data = bytearray()
	while len(data) < nbytes:
		data += socket.recv(nbytes - len(data))
	return data

# HTTP Server
class HTTPServer:
	def __init__(self, host, port, routes):
		self.host = host
		self.port = port
		self.routes = routes
		self.server_socket = None
		self.max_connections = 5

	def start(self):
		# Start server
		log("Starting server at {} port {}".format(self.host, self.port))
		self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server_socket.bind((self.host, self.port))
		self.server_socket.listen(self.max_connections)

		while True:
			try:
				(client_socket, address) = self.server_socket.accept()

				responder = HTTPResponder(self, client_socket, address)
				responder.start()
			except KeyboardInterrupt:
				log("Stopping...")
				break
		
	def __enter__(self):
		# Create server socket
		self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		return self

	def __exit__(self, exception_type, exception_value, traceback):
		# Close server socket
		if self.server_socket.fileno() > -1:
			self.server_socket.close()

# HTTP Responder
class HTTPResponder(threading.Thread):

	protocol = "HTTP/1.1"
	server_name = "PyWebsocket"

	def __init__(self, server, client_socket, address):
		super(HTTPResponder, self).__init__()

		self.server = server
		self.client_socket = client_socket
		self.address = address

		self.daemon = True

	def run(self):
		log("Client connected from {} port {}".format(self.address[0], self.address[1]))

		try:
			content = self.parse_http_content()

			self.handle_request(content)

		except ConnectionClosedException:
			log("Connection closed by client.")
		except ProtocolChangeException as e:
			log("Protocol change requested by handler.")
			e.cb(self.server, self.client_socket, self.address)

		self.client_socket.close()
		log("Closed connection for {} port {}".format(self.address[0], self.address[1]))

	def parse_http_content(self):
		# Fetch data
		data = ""
		while data[-2:] != "\r\n":
			new_data = self.client_socket.recv(2048)
			log("{}".format(new_data))
			if len(new_data) == 0:
				# connection closed
				raise ConnectionClosedException()
			data += new_data

		# Split lines
		data = data.split("\n")

		headers = data[1:]
		headers = [header.strip().split(":", 1) for header in headers]

		request_parts = data[0].split(" ")
		if len(request_parts) != 3:
			return None

		request = {
			"type": request_parts[0].strip(),
			"path": request_parts[1].strip(),
			"protocol": request_parts[2].strip(),
			"headers": {header[0].strip(): header[1].strip() for header in headers if len(header) == 2}
		}

		return request

	def handle_request(self, content):
		if content is None:
			response = HTTPResponder.generate_HTTP_response(400, "Bad Request")

		else:
			route = HTTPRoute.find_route(content["path"], self.server.routes)

			if route is None:
				response = HTTPResponder.generate_HTTP_response(404, "Not Found")
			else:
				response = route.handler(content)

		self.client_socket.send(response)

	@staticmethod
	def generate_HTTP_response(http_code, content, additional_headers={}, replace_headers=False):
		headers = {
			"Connection": "close",
			"Server": HTTPResponder.server_name
		}
		if content is not None:
			headers.update({
				"Content-Type": "text/html",
				"Content-Length": len(content),
			})
		if replace_headers:
			headers = additional_headers
		else:
			headers.update(additional_headers)

		top_str = "{} {} {}\r\n".format(HTTPResponder.protocol, http_code, http_code_lookup(http_code))

		headers_str = ""
		for key, value in headers.iteritems():
			headers_str += "{}: {}\r\n".format(key, value)

		if content is None:
			response = "{}{}\r\n".format(top_str, headers_str)
		else:
			response = "{}{}\r\n{}\r\n".format(top_str, headers_str, content)

		return response

class WebSocketResponder:
	SERVER_HANDSHAKE_KEY = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

	def __init__(self, server, client_socket, address):
		self.server = server
		self.client_socket = client_socket
		self.address = address

	def handle_switch(self, client_handshake_key):
		log("Switching protocol to WebSocket...")
		return_key = base64.b64encode(hashlib.sha1(client_handshake_key + WebSocketResponder.SERVER_HANDSHAKE_KEY).digest())
		response = HTTPResponder.generate_HTTP_response(101, None, {
			"Upgrade": "websocket",
			"Connection": "Upgrade",
			"Sec-WebSocket-Accept": return_key
		}, True)
		self.client_socket.send(response)

	def run(self):
		log("Starting WebSocket protocol...")
		while True:
			frame = WebSocketDataFrame.recv_frame(self.client_socket)
			payload = frame.payload
			opcode = frame.opcode

			if frame is None:
				log("Invalid data received.")
				break
			if frame.opcode == WebSocketDataFrame.OP_CLOSE:
				log("WebSocket connection close requested by client.")
				break

			while frame.fin == 0:
				frame = WebSocketDataFrame.recv_frame(self.client_socket)
				payload += frame.payload

			if frame.opcode == WebSocketDataFrame.OP_PING:
				log("OP_PING not implemented.")
				break

			decoded_payload = WebSocketDataFrame.decode_payload(payload, opcode)
			log("Message received from client: {}".format(decoded_payload))



class WebSocketDataFrame:
	OP_CONTINUATION = 0x0
	OP_TEXT = 0x1
	OP_BINARY = 0x2
	OP_CLOSE = 0x8
	OP_PING = 0x9
	OP_PONG = 0xA

	def __init__(self):
		pass

	@staticmethod
	def decode_payload(payload, opcode):
		if opcode == WebSocketDataFrame.OP_TEXT:
			# text
			return payload.decode("utf-8")
		elif opcode == WebSocketDataFrame.OP_BINARY:
			# binary
			return payload
		else:
			raise Exception("Invalid opcode.")

	@staticmethod
	def recv_frame(socket):
		frame = WebSocketDataFrame()
	
		# byte 1
		byte = recv(socket, 1)[0]
		frame.fin = bool(byte >> 7 & 0b1)
		frame.opcode = byte & 0b00001111

		# byte 2
		byte = recv(socket, 1)[0]
		frame.mask = bool(byte >> 7& 0b1)
		frame.payload_len = byte & 0b01111111

		if not frame.mask:
			# Client frames must be masked
			log("Payload in data frame is not masked. Aborting...")
			return None

		# extended payload length
		if frame.payload_len == 126:
			data = recv(socket, 2)
			frame.payload_len = struct.unpack(">H", data)[0]
			print(frame.payload_len)
		elif frame.payload_len == 127:
			data = recv(socket, 4)
			frame.payload_len = struct.unpack(">I", data)[0]

		# content
		data = recv(socket, 4)
		frame.mask_key = data

		decoded_bytes = bytearray()
		for i in range(frame.payload_len):
			byte = recv(socket, 1)[0]
			decoded_bytes.append(byte ^ (frame.mask_key[i % 4] & 0xFF))

		frame.payload = decoded_bytes

		log("Received data frame: {}".format(frame))

		return frame

	@staticmethod
	def send_frame(socket, payload, payload_type, mask=True):
		response = bytearray()

		# byte 1
		byte = payload_type # opcode
		byte |= 0b10000000 # fin bit



class ConnectionClosedException(Exception):
	"""Connection closed unexpectedly"""
	pass

class ProtocolChangeException(Exception):
	"""Connection closed unexpectedly"""
	def __init__(self, cb):
		super(ProtocolChangeException, self).__init__("Protocol change requested")
		self.cb = cb

class HTTPRoute:
	"""An HTTP route"""
	def __init__(self, path_regex, **args):
		default_args = {
			"content_handler": lambda c: None,
			"type": "html"
		}
		default_args.update(args)
		args = default_args

		self.path_regex = path_regex
		self.content_handler = args["content_handler"]
		self.type = args["type"]

	def handler(self, content):
		if self.type == "html":
			return self.content_handler(content)
		elif self.type == "websocket":
			if content["type"] == "GET" and \
				content["headers"]["Connection"] == "Upgrade" and \
				content["headers"]["Upgrade"] == "websocket":
				raise ProtocolChangeException(self.create_init_websocketresponder(content["headers"]["Sec-WebSocket-Key"]))
			else:
				HTTPResponder.generate_HTTP_response(400, "Bad Request")
		else:
			log("Unsupported type.")
			return HTTPResponder.generate_HTTP_response(500, "Whoops")

	def create_init_websocketresponder(self, client_handshake_key):
		def init(server, client_socket, address):
			res = WebSocketResponder(server, client_socket, address)
			res.handle_switch(client_handshake_key)
			res.run()
			return res

		return init

	@staticmethod
	def find_route(path, routes):
		for route in routes:
			match = re.match(route.path_regex, path)
			if match:
				return route
		return None