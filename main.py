from httpserver import HTTPServer, HTTPResponder, HTTPRoute

HOST = "localhost"
PORT = 8000

routes = (
	HTTPRoute(r"^/socket$", type="websocket"),
	HTTPRoute(r"^/.*$", content_handler=lambda content: HTTPResponder.generate_HTTP_response(200, content["path"]))
)

with HTTPServer(HOST, PORT, routes) as server:
	server.start()