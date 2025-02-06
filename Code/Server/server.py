import socket  # Import the socket module
import fcntl  # Import the fcntl module
import struct  # Import the struct module
from tcp_server import TCPServer  # Import the TCPServer class from tcp_server module

class TankServer:
    def __init__(self):
        # Initialize the TankServer instance
        self.ip = self.get_interface_ip()  # Get the IP address of the network interface
        self.cmdServer = TCPServer()  # Initialize the command server
        self.videoServer = TCPServer()  # Initialize the video server
        self.cmdServerIsBusy = False  # Flag to indicate whether the command server is busy
        self.videoServerIsBusy = False  # Flag to indicate whether the video server is busy

    def get_interface_ip(self):
        # Get the IP address of the wlan0 interface
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Create a UDP socket
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', b'wlan0'[:15]))[20:24])  # Get the IP address of the wlan0 interface

    def startTcpServer(self, port1=5003, port2=8003, max_clients=1, listen_count=1):
        # Start the TCP servers on specified ports
        self.cmdServer.start(self.ip, port1, max_clients, listen_count)  # Start the command server
        self.videoServer.start(self.ip, port2, max_clients, listen_count)  # Start the video server

    def stopTcpServer(self):
        # Stop the TCP servers
        self.cmdServer.close()  # Close the command server
        self.videoServer.close()  # Close the video server

    def set_cmd_server_busy(self, state):
        # Set the busy state of the command server
        self.cmdServerIsBusy = state

    def set_video_server_busy(self, state):
        # Set the busy state of the video server
        self.videoServerIsBusy = state

    def get_cmd_server_busy(self):
        # Get the busy state of the command server
        return self.cmdServerIsBusy

    def get_video_server_busy(self):
        # Get the busy state of the video server
        return self.videoServerIsBusy

    def sendDataToCmdClinet(self, data, ip_address=None):
        # Send data to the command server client(s)
        self.set_cmd_server_busy(True)
        if ip_address is not None:
            self.cmdServer.send_to_client(ip_address, data)  # Send data to a specific client
        else:
            self.cmdServer.send_to_all_client(data)  # Send data to all connected clients of the command server
        self.set_cmd_server_busy(False)

    def sendDataToVideoClient(self, data, ip_address=None):
        # Send data to the video server client(s)
        self.set_video_server_busy(True)
        if ip_address is not None:
            self.videoServer.send_to_client(ip_address, data)  # Send data to a specific client
        else:
            self.videoServer.send_to_all_client(data)  # Send data to all connected clients of the video server
        self.set_video_server_busy(False)

    def readDataFromCmdServer(self):
        # Read data from the command server's message queue
        return self.cmdServer.message_queue

    def readDataFromVideoServer(self):
        # Read data from the video server's message queue
        return self.videoServer.message_queue

    def isCmdServerConnected(self):
        # Check if the command server has any active connections
        if self.cmdServer.active_connections == 0:
            return False
        else:
            return True

    def isVideoServerConnected(self):
        # Check if the video server has any active connections
        if self.videoServer.active_connections == 0:
            return False
        else:
            return True

    def getCmdServerClientIps(self):
        # Get the list of client IP addresses connected to the command server
        return self.cmdServer.get_client_ips()

    def getVideoServerClientIps(self):
        # Get the list of client IP addresses connected to the video server
        return self.videoServer.get_client_ips()

# Example usage
if __name__ == "__main__":
    server = TankServer()  # Create an instance of TankServer
    server.startTcpServer(5003, 8003)  # Start the TCP servers on specified ports

    try:
        while True:
            cmdQueue = server.readDataFromCmdServer()  # Get the command server's message queue
            if cmdQueue.qsize() > 0:  # Check if there are messages in the queue
                client_address, message = cmdQueue.get()  # Get a message from the queue
                print(client_address, message)  # Print the client address and message
                server.cmdServer.send_to_client(client_address, message)  # Send the message back to the client

            videoQueue = server.readDataFromVideoServer()  # Get the video server's message queue
            if videoQueue.qsize() > 0:  # Check if there are messages in the queue
                client_address, message = videoQueue.get()  # Get a message from the queue
                print(client_address, message)  # Print the client address and message
                server.videoServer.send_to_client(client_address, message)  # Send the message back to the client

    except KeyboardInterrupt:  # Catch keyboard interrupt
        print("Received interrupt signal, stopping server...")  # Print interrupt information
        server.stopTcpServer()  # Stop the TCP servers