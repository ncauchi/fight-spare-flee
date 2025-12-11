import socket

def get_local_ip():
    """
    Finds the local IP address using a temporary UDP socket connection.
    """
    s = None
    try:
        # Create a temporary UDP socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Connect to an external IP address (Google's public DNS server)
        s.connect(("8.8.8.8", 80))
        # Get the local IP address assigned to the socket
        local_ip = s.getsockname()[0]
        return local_ip
    except socket.error:
        # Fallback for environments where the above method fails (e.g., no default route)
        # This approach uses the system's hostname resolution, which might return 127.0.0.1 on some systems
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            if local_ip.startswith("127."):
                return "127.0.0.1 (Loopback or resolution issue)"
            return local_ip
        except socket.error:
            return "Could not determine IP address"
    finally:
        if s:
            s.close()
