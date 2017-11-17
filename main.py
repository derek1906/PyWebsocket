import os
from httpserver import HTTPServer, HTTPResponder, HTTPRoute
from log import *
import socket
import mimetypes

HOST = "0.0.0.0"	#"localhost"
PORT = 8000

def fetch_page(path):
	www_dir_path = os.path.abspath("www/")
	requested_file_path = os.path.abspath(os.path.join(www_dir_path, path))

	log("File accessed: {}".format(requested_file_path))

	if os.path.commonprefix([www_dir_path, requested_file_path]) != www_dir_path:
		# bad address
		return HTTPResponder.generate_HTTP_response(404, "Not found")

	if not os.path.isfile(requested_file_path):
		# check if directory
		if os.path.isdir(requested_file_path):
			return fetch_page(os.path.join(path, "index.html"))

		# file not found
		return HTTPResponder.generate_HTTP_response(404, "Not found")

	with open(requested_file_path, "rb") as file:
		content_type, encoding = mimetypes.guess_type(requested_file_path)
		return HTTPResponder.generate_HTTP_response(200, file.read(), {
			"Content-Type": content_type,
			"Content-Encoding": encoding
		})

routes = (
	HTTPRoute(r"^/socket$", type="websocket"),
	HTTPRoute(r"^/.*$", content_handler=lambda content: fetch_page(content["path"][1:]))
)

with HTTPServer(HOST, PORT, routes) as server:
	server.start()