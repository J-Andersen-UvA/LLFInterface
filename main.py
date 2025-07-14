"""
Main script for launching a LiveLinkFaceServer.

This script imports necessary modules to set up and launch a LiveLinkFaceServer instance.
It fetches configuration settings from a YAML file using the SetUp class from src.config.setup module.
Then, it initializes a LiveLinkFaceServer instance with a specified model name and the fetched arguments.
Finally, it launches the server using the init_server() method.

Usage:
    python main.py

    - Ensure 'config.yaml' exists in the 'src.config' directory with required settings.

Modules:
    - SetUp: Class for setting up configurations from a YAML file.
    - LiveLinkFaceServer: Class for handling LiveLinkFace server setup and launch.
"""

import asyncio
from LiveLinkFace import LiveLinkFaceServer
import yaml
import zeroconfScream
from discoveryServer import WebSocketServer
import threading 

async def main():
    # Load configuration
    with open("C:\\Users\\VICON\\Desktop\\Code\\recording\\LLFInterface\\config.yaml", "r") as f:
        args = yaml.safe_load(f)

    # 1) Register Zeroconf _off_ the main loop to avoid deadlock
    try:
        zc, service_info = await asyncio.to_thread(
            zeroconfScream.register_service,
            args.get("listen_port", 8005)
        )
    except Exception as e:
        print(f"[Error] Unable to register Zeroconf service: {e}")
        return

    # 2) Spin up WebSocket + OSC servers together
    #    (remove the old blocking disco.start_server() call)
    disco = WebSocketServer(
        server_host=args.get("listen_ip", "0.0.0.0"),
        server_port=args.get("listen_port", 8005)
    )
    llf = LiveLinkFaceServer("testGloss", args)
    disco.llf_server = llf

    # 3) Launch OSC in a daemon thread so it won't block process exit
    osc_thread = threading.Thread(
        target=llf.init_server,
        name="OSC-Server-Thread",
        daemon=True
    )
    osc_thread.start()

    try:
        print("Starting LiveLinkFace interface…")
        await asyncio.gather(
            disco.start_server_async()
        )
    except KeyboardInterrupt:
        print("Interrupted by user, shutting down…")
    except Exception as e:
        print(f"[Error] Server runtime exception: {e}")
    finally:
        await asyncio.to_thread(
            zeroconfScream.unregister_service,
            zc, service_info
        )

        disco.stop_event.set()
        llf.stop_server()
        osc_thread.join(timeout=2)
        print("Cleaned up and exiting.")

if __name__ == "__main__":
    asyncio.run(main())
