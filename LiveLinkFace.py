"""
File: LiveLinkFace.py

Description:
This file defines the LiveLinkFaceClient and LiveLinkFaceServer classes for
communicating with an iPhone server via OSC (Open Sound Control) protocol.

Classes:
- LiveLinkFaceClient: Sends messages to the iPhone Live Link server.
- LiveLinkFaceServer: Launches the Live Link server and communicates with the iPhone.

LiveLinkFaceClient:
- The __init__ method initializes the client and sets the Python server address on the iPhone.
- The start_capture method instructs the iPhone to start capturing.
- The stop_capture method instructs the iPhone to stop capturing.
- The set_filename method sets the file name for capturing.
- The request_battery method requests the battery status from the iPhone.
- The save_file method sends a transport message to the iPhone to save a file.

LiveLinkFaceServer:
- The __init__ method initializes the server and client objects for communication with the iPhone.
- The init_server method starts the server to receive messages from the iPhone.
- The quit_server method exits the server and client.
- The start_recording method starts recording with the iPhone and TCP socket.
- The send_close_tcp method sends a close command to the TCP socket.
- The send_file_name_tcp method sends a file name to the TCP socket.
- The send_are_you_okay_tcp method checks if the TCP socket is okay.
- The send_signal_recording_tcp method sets the TCP socket to file receiving mode.
- The ping_back method responds to requests, indicating that the OSC server is alive.
- The default method prints all received messages by default.
"""
from pythonosc.udp_client import SimpleUDPClient
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
from fileReceiver import FileReceiver
import sys
import socket
import struct

# Pick up your machine’s LAN IP and pack to 4-byte form
IP_MACHINE = socket.gethostbyname(socket.gethostname())
IP_IPHONE = ""

class LiveLinkFaceClient:
    """
    Class LiveLinkFaceClient sends messages to the live link server on the iPhone.

    Methods:
    - __init__: Initializes the client and sets the Python server address on the iPhone.
    - start_capture: Sends a message to start capturing to the iPhone server.
    - stop_capture: Sends a message to stop capturing to the iPhone server.
    - set_filename: Sets the file name for capturing on the iPhone server.
    - request_battery: Requests battery information from the iPhone server.
    - save_file: Sends a transport message to the iPhone for saving a file.

    Attributes:
    - toIphone: SimpleUDPClient instance for communication with the iPhone server.
    - gloss: Current gloss set for capturing.
    - args: Arguments for configuring the client.
    """

    def __init__(self, args, gloss):
        """
        Initialize the LiveLinkFaceClient.

        Args:
        - args: The arguments containing necessary configurations.
        - gloss: The initial gloss for capturing.

        Description:
        This method initializes the LiveLinkFaceClient instance. It sets up the UDP client
        for communication with the iPhone server, sets the Python server address on the iPhone,
        and initializes other necessary attributes.
        """
        global IP_IPHONE
        self.port = args.get('llf_port', None)
        self.phone_present = False

        self.record_stop_confirm = True

        if IP_IPHONE == "":
            print("Please set the IP of the iPhone, and then call LiveLinkFaceClient.init_apple_con().")
        else:
            self.init_apple_con(IP_IPHONE)

        self.gloss = gloss
        self.args = args

        # Set gloss of first sign
        self.set_filename(self.gloss)
        self.takenumber = 0
    
    def init_apple_con(self, ip_iphone):
        global IP_IPHONE

        if self.phone_present:
            return

        IP_IPHONE = ip_iphone
        print("Phone initialized, sending to: ", IP_IPHONE, self.port)
        self.toIphone = SimpleUDPClient(IP_IPHONE, self.port)
        self.phone_present = True
        self.send_message_to_iphone("/OSCSetSendTarget", [IP_MACHINE, self.port])
        self.send_message_to_iphone("/VideoDisplayOn", [])

    def send_message_to_iphone(self, msg, *args):
        """Extra in between function to check if we can actually send messages."""
        global IP_IPHONE

        if IP_IPHONE == "" and not self.phone_present:
            print("Please set the IP of the iPhone, and then call LiveLinkFaceClient.init_apple_con().")
        else:
            print(f"Sending msg {msg} with args {args}")
            self.toIphone.send_message(msg, *args)

    def start_capture(self, *args):
        """
        Start capturing on the iPhone server.

        Returns:
        The current capture number.

        Description:
        This method sends a message to the iPhone server to start capturing.
        It increments the capture number and returns it.
        """
        self.send_message_to_iphone("/RecordStart", [self.gloss, self.takenumber])
        return self.takenumber

    def stop_capture(self, *args):
        """
        Stop capturing on the iPhone server.

        Description:
        This method sends a message to the iPhone server to stop capturing.
        It also increments the capture number.
        """
        self.send_message_to_iphone("/RecordStop", [])
        self.takenumber += 1
        self.record_stop_confirm = False

    def set_filename(self, gloss, *args):
        """
        Set the file name for capturing on the iPhone server.

        Args:
        - gloss: The gloss to be set as the file name.

        Description:
        This method sets the file name for capturing on the iPhone server.
        It also resets the capture number.
        """
        print("Setting filename to: ", gloss)

        # Don't reset the take number if the gloss is the same
        if self.gloss != gloss:
            self.takenumber = 0

        self.gloss = gloss
        self.send_message_to_iphone("/Slate", [self.gloss])
    
    def request_battery(self, *args):
        """
        Request battery information from the iPhone server.

        Description:
        This method sends a message to the iPhone server to request battery information.
        """
        self.send_message_to_iphone("/BatteryQuery", [])

    def save_file(self, command, timecode, blendshapeCSV, referenceMOV, *args):
        """
        Save a file on the iPhone server.

        Args:
        - timecode: Timecode information.
        - blendshapeCSV: Blendshape CSV data.
        - referenceMOV: Reference MOV file.

        Description:
        This method sends a transport message to the iPhone server to save a file.
        """
        self.record_stop_confirm = True
        # File name has the format 20250714_test7_250714_5_0/test7_250714_5_0_vislabLivelink_cal.csv so lets remove the first part
        splitBlendshapeCSV = blendshapeCSV.split("/")[-1]
        splitReferenceMOV = referenceMOV.split("/")[-1]
        csv_receiver = FileReceiver(host=IP_MACHINE, port=self.args.get('receive_csv_port', None), output_dir=self.args.get('llf_save_path_csv', None), filename=splitBlendshapeCSV)
        mov_receiver = FileReceiver(host=IP_MACHINE, port=self.args.get('receive_video_port', None), output_dir=self.args.get('llf_save_path_video', None), filename=splitReferenceMOV)
        print(f"send the transport towards:\tCSV{IP_MACHINE}:{str(self.args.get('receive_csv_port', None))}\tMOV{IP_MACHINE}:{str(self.args.get('receive_video_port', None))}")
        self.send_message_to_iphone("/Transport", [IP_MACHINE + ':' + str(csv_receiver.port), blendshapeCSV])
        self.send_message_to_iphone("/Transport", [IP_MACHINE + ':' + str(mov_receiver.port), referenceMOV])

class LiveLinkFaceServer: 
    """
    Class LiveLinkFaceServer launches the live link server that communicates with the iPhone.

    Description:
    The IP used in this server should be the same as the listener in the iPhone.
    The server is NOT launched asynchronously, but it contains the client object to do any communication
    to the iPhone where necessary.
    The server is a man in the middle for all the communication with the iPhone, including setting up the
    TCP connection for the file transfer.
    """
    def __init__(self, gloss, args):
        """
        Initialize the LiveLinkFaceServer.

        Args:
        - gloss: The gloss for capturing.
        - args: The arguments containing necessary configurations.

        Description:
        This method initializes the LiveLinkFaceServer instance. It sets up the dispatcher for handling
        incoming messages, initializes the client object, and sets up rules for message handling.
        """
        self.gloss = gloss
        self.args = args
        self.battery_percentage = 100.0
        self.client = LiveLinkFaceClient(args, gloss)

        # Start server rules here, add a default rule for all other incoming messages
        self.dispatcher = Dispatcher()
        self.dispatcher.map("/OSCSetSendTargetConfirm", print)
        self.dispatcher.map("/QuitServer", self.quit_server)

        # Start client requests here
        self.dispatcher.map("/BatteryQuery", self.client.request_battery)
        self.dispatcher.map("/SetFileName", lambda address, file_name: self.set_filename(address, file_name))
        self.dispatcher.map("/RecordStart", self.start_recording)
        self.dispatcher.map("/RecordStop", self.client.stop_capture)
        # When the recording is fully finished, instruct the client to save the file locally
        self.dispatcher.map("/RecordStopConfirm", self.client.save_file)

        # Start health check requests here
        self.dispatcher.map("/Battery", lambda address, *args : self.set_battery_percentage(*args))

        # What to do with unknown messages
        self.dispatcher.set_default_handler(self.default)

    def init_server(self):
        """
        Start the server.

        Description:
        This method starts the server to receive messages from the iPhone.
        """
        print("Receiving iPhone On: ", IP_MACHINE, self.args.get('llf_port', None))
        self.server = BlockingOSCUDPServer((IP_MACHINE, self.args.get('llf_port', None)), self.dispatcher)
        self.server.serve_forever()

    def quit_server(self, *args):
        """
        Exit the server.

        Description:
        This method exits the server and client through the /QuitServer handle.
        """
        sys.exit()

    def start_recording(self, *args):
        """
        Start recording with the iPhone.

        Description:
        This method starts recording with the iPhone and starts accepting a file with the TCP socket.
        """
        self.client.start_capture()
    
    def stop_recording(self, *args):
        """
        Stop recording with the iPhone.

        Description:
        This method stops recording with the iPhone.
        """
        self.client.stop_capture()

    def set_filename(self, addr, file_name, *args):
        self.client.set_filename(file_name)

    def default(self, address, *args):
        """
        Print all messages by default.

        Args:
        - address: The address that we receive the message from.
        - args: Additional arguments.

        Description:
        This method prints all messages by default.
        """
        print(f"{address}: {args}")

    def health_check(self, *args):
        """
        Perform a health check.

        Description:
        This method performs a health check by sending a message to the iPhone server.
        """
        try:
            self.client.request_battery()
            if self.battery_percentage < 10.0:
                print(f"[LLF Warning] Battery percentage is low: {self.battery_percentage}%")
                return False, "Battery percentage is low"
            if not self.client.phone_present:
                print("[LLF Warning] iPhone is not present.")
                return False, "iPhone is not present"
            if not self.client.record_stop_confirm:
                print("[LLF Warning] Record stop confirm not received by iPhone.")
                return False, "Record stop confirm not received by iPhone"
            return True, ""
        except Exception as e:
            print(f"[Warning] Exception during health check: {e}")

    def set_battery_percentage(self, flt):
        """
        Set the battery percentage.

        Args:
        - percentage: The battery percentage to be set.

        Description:
        This method sets the battery percentage for the iPhone server.
        """
        self.battery_percentage = flt * 100.0

    def stop_server(self):
        """
        Stop the OSC server gracefully.

        Description:
        This method stops the OSC server gracefully.
        """
        try:
            if hasattr(self, 'server') and self.server:
                self.server.server_close()  # Close the socket
        except Exception as e:
            print(f"[Warning] Exception while stopping OSC server: {e}")