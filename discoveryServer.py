import asyncio
# import logging
import sys
import websockets
import logging

# logging.getLogger("websockets").addHandler(logging.NullHandler())
# logging.getLogger("websockets").propagate = False
logging.getLogger("websockets").setLevel(logging.CRITICAL)

class WebSocketServer:
    def __init__(self, server_host='0.0.0.0', server_port=8004):
        self.server_host = server_host
        self.server_port = server_port
        self.stop_event = asyncio.Event()
        self.server = None
        self.llf_server = None  # Placeholder for LiveLinkFaceServer instance

    async def start_server_async(self):
        print(f"[WebSocket] Starting server on {self.server_host}:{self.server_port}")
        self.server = await websockets.serve(
            self.handler, self.server_host, self.server_port
        )
        await self.stop_event.wait()  # ✅ Wait until "Kill" is received
        await self.shutdown_server()

    async def shutdown_server(self):
        print("[WebSocket] Shutting down server...")
        self.server.close()
        await self.server.wait_closed()
        print("[WebSocket] Server stopped.")

    def start_server(self):
        loop = asyncio.get_event_loop()
        # logging.getLogger("websockets").setLevel(logging.CRITICAL)
        loop.run_until_complete(self.start_server_async())

    async def handler(self, websocket):
        print(f"[WebSocket] Connection from {websocket.remote_address}")
        async for message in websocket:
            if self.llf_server:
                print(f"[WebSocket] Received message: {message}")
                await self.msg_to_func(message, websocket)
            else:
                print(f"[WebSocket] Received message (no llf_server): {message}")
        # except websockets.ConnectionClosed:
        #     print("[WebSocket] Connection closed.")

    async def msg_to_func(self, msg, websocket=None):
        """
        Convert a message to a function call.
        This is a placeholder for actual message processing logic.
        """
        if msg == "Start":
            print("[LLF WebSocket] Received 'Start' message.")
            self.llf_server.start_recording()
        elif msg == "Stop":
            print("[LLF WebSocket] Received 'Stop' message.")
            self.llf_server.stop_recording()
        elif msg.startswith("SetName"):
            print(f"[LLF WebSocket] Received 'SetName' message: {msg[len('SetName '):]}")
            self.llf_server.set_filename(websocket, msg[len('SetName '):])
            # self.llf_server.client.set_filename(msg[len('SetName '):])
            # self.llf_server.send_file_name_tcp(websocket, msg[len('SetName '):])
        elif msg.startswith("health"):
            print("[LLF WebSocket] Received 'health' message.")
            if not self.llf_server.client.phone_present:
                iphone_ip = msg[len('health '):]
                self.llf_server.client.init_apple_con(iphone_ip)

            status, response = self.llf_server.health_check()
            response = "Good" if status else response
            print(f"[LLF WebSocket] Health check status: {status}, response: {response}")
            await websocket.send("Good" if status else response) if websocket else None
