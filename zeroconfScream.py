from zeroconf import Zeroconf, ServiceInfo
import socket

BROADCAST_NAME = "LiveLinkFaceServer.local."
SERVICE_TYPE = "_mocap._tcp.local."
SERVICE_NAME = f"LiveLinkFaceServer.{SERVICE_TYPE}"

def register_service(port):
    """
    Register a service with Zeroconf.
    
    Args:
        name (str): The name of the service.
        port (int): The port number for the service.
    """
    # Zeroconf setup
    zeroconf = Zeroconf()

    # Pick up your machine’s LAN IP and pack to 4-byte form
    ip_str = socket.gethostbyname(socket.gethostname())
    addr_bytes = socket.inet_aton(ip_str)

    props = {
        "path": "/",
        "format": "json"
    }

    service_info = ServiceInfo(
        type_=SERVICE_TYPE,
        name=SERVICE_NAME,
        addresses=[addr_bytes],        # <- list, not `address=`
        port=port,
        properties=props,
        server=BROADCAST_NAME
    )

    # Register the service
    zeroconf.register_service(service_info)
    print(f"Service registered on port {port} with Zeroconf.")
    return zeroconf, service_info

def unregister_service(zeroconf, service_info):
    """
    Unregister a service from Zeroconf.
    
    Args:
        zeroconf (Zeroconf): The Zeroconf instance.
        service_info (ServiceInfo): The service information to unregister.
    """
    zeroconf.unregister_service(service_info)
    zeroconf.close()
    print(f"Service {service_info.name} unregistered from Zeroconf.")

