import socket
import struct
import threading
from pathlib import Path
from typing import Union
import time
import errno
import os
import requests

class FileReceiver:
    def __init__(
        self,
        host: str,
        port: int,
        output_dir: Union[str, Path],
        filename: str,
        max_port_tries: int = 5,
        endpoint: str = 'https://signcollect.nl/razerUpload/upload.php',
        send_to_endpoint: bool = True
    ):
        """
        Start listening immediately on `port`. When a client connects and sends
        a 4-byte BE length prefix + that many bytes of file data, we write it to
        output_dir/filename and then close everything.
        """
        self.host = host
        self.port = port
        self.output_dir = Path(output_dir)
        self.endpoint = endpoint
        self.send_to_endpoint = send_to_endpoint
        self.filename = filename
        self._init_output_dir()

        # set up the listening socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # attempt to bind across a small range
        for offset in range(max_port_tries):
            try_port = port + offset
            try:
                sock.bind((self.host, try_port))
                self.port = try_port
                break
            except OSError as e:
                if e.errno == errno.EADDRINUSE:
                    print(f"[receiver:{self.filename}] Port {try_port} in use, trying {try_port+1}…")
                    continue
                else:
                    sock.close()
                    raise

        if self.port is None:
            sock.close()
            raise RuntimeError(f"[receiver:{self.filename}] Could not bind on ports {port}–{port+max_port_tries-1}")

        sock.listen(1)
        self._sock = sock

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

            if self.send_to_endpoint:
                self._go_send_files_to_endpoint()

        except Exception as e:
            print(f"[receiver:{self.filename}] Error: {e}")
        finally:
            conn.close()
            self._sock.close()
            print(f"[receiver:{self.filename}] Shutdown listener")

    def _go_send_files_to_endpoint(self):
        """
        Send all files in self.output_dir to the endpoint.
        """
        for file in self.output_dir.glob("*"):
            if file.is_file():
                try:
                    response = self._send_file_to_endpoint(
                        self.endpoint,
                        file,
                        field_name="file",
                        extra_data={"filename": file.name},
                    )
                    print(f"[receiver:{self.filename}] Successfully uploaded {file.name}: {response.status_code}")
                except requests.HTTPError as e:
                    print(f"[receiver:{self.filename}] Failed to upload {file.name}: {e}")
                except Exception as e:
                    print(f"[receiver:{self.filename}] Error sending file {file.name}: {e}")

    def _send_file_to_endpoint(self, endpoint: str, file_path: str, field_name: str = "file", extra_data: dict = None, headers: dict = None) -> requests.Response:
        """
        Sends a file to a specified HTTP endpoint using multipart/form-data.

        :param endpoint: The server's upload URL (e.g. "https://signcollect.nl/studioFilesServer/upload-mocap").
        :param file_path: Path to the file to be sent.
        :param field_name: The form field name expected by the server for file uploads.
        :param extra_data: Optional dict of additional form fields to include in the POST.
        :param headers: Optional dict of HTTP headers to include (e.g. authentication tokens).
        :return: The `requests.Response` object from the server.
        :raises: `requests.HTTPError` if the upload fails (non-2xx status code).
        """
        # Verify the file exists
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"No such file: {file_path}")

        # Prepare extra form fields
        data = extra_data or {}
        
        # Open the file in binary mode and send it
        with open(file_path, "rb") as f:
            files = {
                field_name: (os.path.basename(file_path), f)
            }
            # Perform the POST
            resp = requests.post(endpoint, files=files, data=data, headers=headers)
        
        # Raise an exception for error codes (4xx, 5xx)
        resp.raise_for_status()
        return resp
    