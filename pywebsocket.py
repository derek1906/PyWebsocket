import socket
import hashlib
import base64
import struct

from pprint import pprint
import traceback

WEBSOCKET_HANDSHAKE_KEY = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def recv(socket, nbytes):
	'''
	Guarentee to receive nbytes of data
	'''
	data = bytearray()
	while len(data) < nbytes:
		data += socket.recv(nbytes - len(data))
	return data

def parseHTTPHeader(header_str):
	header_str = header_str.split("\n")

	headers = header_str[1:]
	headers = [header.strip().split(":", 1) for header in headers]

	request_parts = header_str[0].split(" ")
	request = {
		"type": request_parts[0].strip(),
		"path": request_parts[1].strip(),
		"protocol": request_parts[2].strip(),
		"headers": {header[0].strip(): header[1].strip() for header in headers if len(header) == 2}
	}

	return request

def handle_request(header, socket):
	if header["protocol"] != "HTTP/1.1":
		print("Protocol not supported. Responded with HTTP 505.")
		socket.send(
"""HTTP/1.1 505 HTTP Version Not Supported
Content-Type: text/html
Content-Length: 379
Connection: close
Date: Thu, 16 Nov 2017 07:59:22 GMT
Server: pywebsocket

505 - HTTP Version Not Supported""")

	elif header["path"] == "/" and \
		header["headers"]["Connection"] == "Upgrade" and \
		header["headers"]["Upgrade"] == "websocket":
		print("Starting websocket handshaking...")
		handle_websocket(header["headers"]["Sec-WebSocket-Key"], socket)

	elif header["path"] == "/":
		print("Responded with HTTP 202.")
		socket.send(
"""HTTP/1.1 200 OK
Content-Type: text/html

hello world""")

	else:
		print("Responded with HTTP 404.")
		socket.send(
"""HTTP/1.1 404 Not Found
Content-Type: text/html

Not found""")

def handle_websocket(key, socket):
	key += WEBSOCKET_HANDSHAKE_KEY
	return_key = base64.b64encode(hashlib.sha1(key).digest())

	socket.send(
"""HTTP/1.1 101 Switching Protocols\r
Upgrade: websocket\r
Connection: Upgrade\r
Sec-WebSocket-Accept: %s\r
\r
""" % return_key)
	print("Handshake completed.")


	while 1:
		if not read_frame(socket):
			break

def read_frame(socket):
	#str = ["{0:08b}".format(c) + ("\n" if i % 4 == 3 else "") for i, c in enumerate(frame)]
	#print(" ".join(str))
	
	props = {}
	
	# byte 1
	byte = recv(socket, 1)[0]
	props["fin"] = bool(byte >> 7 & 0b1)
	props["opcode"] = byte & 0b00001111

	if props["opcode"] == 8:
		# Close frame
		print("Received close frame. Closing connection...")
		return False

	# byte 2
	byte = recv(socket, 1)[0]
	props["mask"] = bool(byte >> 7& 0b1)
	props["payload_len"] = byte & 0b01111111

	if not props["mask"]:
		# Client frames must be masked
		print("Client frame not masked. Closing connection...")
		return False

	# extended payload length
	if props["payload_len"] == 126:
		data = recv(socket, 2)
		props["payload_len"] = struct.unpack("I", data)
	elif props["payload_len"] == 127:
		data = recv(socket, 4)
		props["payload_len"] = struct.unpack("I", data)

	# content
	data = recv(socket, 4)
	props["mask_key"] = data

	decoded_bytes = bytearray()
	for i in range(props["payload_len"]):
		byte = recv(socket, 1)[0]
		decoded_bytes.append(byte ^ (props["mask_key"][i % 4] & 0xFF))

	props["decoded_string"] = decoded_bytes.decode("utf-8")

	print("Received frame:")
	pprint(props)
	print("Message: %s" % props["decoded_string"])

	return True

#create an INET, STREAMing socket
serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#bind the socket to a public host,
# and a well-known port
serversocket.bind(("localhost", 8000))
#become a server socket
serversocket.listen(1)

while 1:
	try:
		print("=========================")
		print("Waiting for new client...")
		#accept connections from outside
		(clientsocket, address) = serversocket.accept()
		print("New client connected.")

		data = clientsocket.recv(2048)
		header = parseHTTPHeader(data)

		print("Received header:")
		pprint(header)

		handle_request(header, clientsocket)

		clientsocket.close()
		print("Closed connection.")

	except Exception:
		print(traceback.format_exc())
		try:
			clientsocket.close()
		except Exception:
			pass

		break

clientsocket.close()
serversocket.close()