import socket
import struct
import threading
from pathlib import Path
from typing import Union
import time

class FileReceiver:
    def __init__(
        self,
        host: str,
        port: int,
        output_dir: Union[str, Path],
        filename: str,
    ):
        """
        Start listening immediately on `port`. When a client connects and sends
        a 4-byte BE length prefix + that many bytes of file data, we write it to
        output_dir/filename and then close everything.
        """
        self.host = host
        self.port = port
        self.output_dir = Path(output_dir)
        self.filename = filename
        self._init_output_dir()

        # set up the listening socket
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(1)

        # background thread to handle exactly one transfer
        self._thread = threading.Thread(target=self._serve_once, daemon=True)
        self._thread.start()
        print(f"[receiver:{self.filename}] Listening on port {self.port}")

    def _init_output_dir(self):
        """Initialize the output directory if it doesn't exist. Then make a subdirectory based on the date following the format DD-MM-YYYY."""
        self.output_dir.mkdir(parents=True, exist_ok=True)        
        date_str = time.strftime("%d-%m-%Y")
        self.output_dir = self.output_dir / date_str
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"[receiver:{self.filename}] Output directory initialized at {self.output_dir}")

    def _serve_once(self):
        conn, addr = self._sock.accept()
        print(f"[receiver:{self.filename}] Connection from {addr}")
        try:
            # 1) read 4-byte BE length
            size_data = conn.recv(4)
            if len(size_data) < 4:
                raise RuntimeError("Failed to read length prefix")
            total_size = struct.unpack(">I", size_data)[0]

            # 2) read the payload
            remaining = total_size
            chunks = []
            while remaining > 0:
                chunk = conn.recv(min(4096, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)

            if remaining:
                print(f"[receiver:{self.filename}] Warning: only got {total_size-remaining}/{total_size} bytes")

            # 3) write to disk
            out_path = self.output_dir / self.filename
            with open(out_path, "wb") as f:
                for chunk in chunks:
                    f.write(chunk)
            print(f"[receiver:{self.filename}] Saved file to {out_path}")

        except Exception as e:
            print(f"[receiver:{self.filename}] Error: {e}")
        finally:
            conn.close()
            self._sock.close()
            print(f"[receiver:{self.filename}] Shutdown listener")
