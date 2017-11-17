## PyWebsocket

Building a HTTP/WebSocket server from scratch with Python. Do not use this
in any production code!

![](/screenshot.png)

### How to use
Run

    python main.py

to start the server. The HTTP server will look for files only inside the `www/` directory.

Currently the WebSocket can only receive data. Transmitting data is not implemented yet.

### Why
The main goal is to understand how HTTP and WebSocket protocols work under the hood.

### Interesting Discoveries
- Performing tests with Chrome showed that Chrome opens up a new TCP connection
  after all the HTTP requests are completed. This behavior was not found in other
  browsers including Safari and Lynx. Both desktop and mobile versions of Chrome
  demonstrate this behavior of preopenning a connection in case the page makes 
  another request.

- Without gzipping the content, serving a relatively big single-page application is 
  reasonably fast given that the server can handle multiple requests at the same time.

### Caveats
In no way the HTTP/WebSocket server is complete or secure. Things that it does not support:

- Almost all headers such as `Cookies` and `Expect` are not supported. The only headers it supports
  are `Connection`, `Upgrade`, and `Sec-WebSocket-Key` which are necessary for upgrading protocol
  to the WebSocket protocol.

- Content and payloads are not compressed.