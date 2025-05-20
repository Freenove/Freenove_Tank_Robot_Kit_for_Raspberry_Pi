# Define the MessageParser class to handle message parsing
class MessageParser:
    def __init__(self):
        """Initialize the MessageParser class with empty parameters."""
        self.inputString = None    # The raw input string
        self.stringParameter = []  # List to store string parameters
        self.intParameter = []     # List to store integer parameters
        self.commandString = None  # The command string extracted from the input

    def clearParameters(self):
        """Clear all parsed parameters."""
        self.inputString = None       # Reset the input string
        self.stringParameter.clear()  # Clear the list of string parameters
        self.intParameter.clear()     # Clear the list of integer parameters
        self.commandString = None     # Reset the command string

    def parser(self, msg):
        """Parse the input message and extract command and parameters."""
        try:
            self.clearParameters()                              # Clear any existing parameters
            self.inputString = msg.strip()                      # Remove leading and trailing whitespace from the input message
            self.stringParameter = self.inputString.split("#")  # Split the input string by '#' to get parameters
            self.commandString = self.stringParameter[0]        # The first element is the command string
            bufStringParameter = self.stringParameter[1:]       # Remaining elements are parameters
            if len(bufStringParameter) > 0:
                for x in bufStringParameter:
                    if x != "" and x != '':                        # Ensure the parameter is not an empty string
                        self.intParameter.append(round(float(x)))  # Convert the parameter to an integer and append to the list
        except Exception as e:
            print("Error: Invalid command or parameter.")       # Print an error message if parsing fails
            print("msg:{}".format(msg))                         # Print the original message
            self.clearParameters()                              # Clear parameters in case of error
            print("Error:", e)                                  # Print the exception details

# Main program logic follows:
if __name__ == '__main__':
    from queue import Queue  # Import the Queue class from the queue module

    msg = MessageParser()                 # Create an instance of the MessageParser class
    myQueue = Queue()                     # Create a queue to hold messages
    
    print("MessageParser Test")           # Print a test start message
    print("Put message to queue")         # Indicate that a message is being added to the queue
    myQueue.put("CMD_LED#0#255#0#0#15#")  # Add a test message to the queue

    print("Get message from queue\n")     # Indicate that messages are being processed from the queue
    while not myQueue.empty():            # Process messages until the queue is empty
        print("Queue size: " + str(myQueue.qsize()))  # Print the current size of the queue
        msg.parser(myQueue.get())         # Parse the message from the queue
        if len(msg.intParameter) > 0 and len(msg.stringParameter) > 0:
            print("msg.inputString: {}".format(msg.inputString))          # Print the raw input string
            print("msg.stringParameter: {}".format(msg.stringParameter))  # Print the list of string parameters
            print("msg.commandString: {}".format(msg.commandString))      # Print the command string
            print("msg.intParameter:{}\n".format(msg.intParameter))       # Print the list of integer parameters
        elif len(msg.stringParameter) > 0 and len(msg.intParameter) == 0:
            print("msg.inputString: {}".format(msg.inputString))          # Print the raw input string
            print("msg.commandString: {}\n".format(msg.commandString))    # Print the command string
        else:
            print("msg.inputString: {}".format(msg.inputString))          # Print the raw input string

    print("Test end")  # Indicate the end of the test