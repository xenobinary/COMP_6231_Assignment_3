import socket
import os

class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client_socket = None
        self.eof_token = None

    def _recv_exact(self, active_socket: socket.socket, n: int) -> bytearray:
        """Receive exactly n bytes from the socket, or raise if connection closes early."""
        data = bytearray()
        while len(data) < n:
            packet = active_socket.recv(n - len(data))
            if not packet:
                raise ConnectionError("Socket closed before receiving expected bytes")
            data.extend(packet)
        return data

    def _read_frame_with_remainder(self, active_socket: socket.socket, buffer_size: int, eof_token) -> tuple[bytearray, bytearray]:
        """Read until the first occurrence of eof_token is found. Return (payload, remainder after token)."""
        if isinstance(eof_token, (bytes, bytearray, memoryview)):
            token_bytes = bytes(eof_token)
        else:
            token_bytes = str(eof_token).encode('utf-8')
        buf = bytearray()
        token_len = len(token_bytes)
        active_socket.settimeout(10.0)
        while True:
            try:
                chunk = active_socket.recv(buffer_size)
                if not chunk:
                    return buf, bytearray()
                buf.extend(chunk)
                idx = buf.find(token_bytes)
                if idx != -1:
                    payload = buf[:idx]
                    remainder = buf[idx + token_len:]
                    return payload, remainder
            except socket.timeout:
                continue

    def receive_message_ending_with_token(
        self, active_socket, buffer_size, eof_token
    ) -> bytearray:
        """
        Same implementation as in receive_message_ending_with_token() in server.py
        A helper method to receives a bytearray message of arbitrary size sent on the socket.
        This method returns the message WITHOUT the eof_token at the end of the last packet.
        :param active_socket: a socket object that is connected to the server
        :param buffer_size: the buffer size of each recv() call
        :param eof_token: a token that denotes the end of the message.
        :return: a bytearray message with the eof_token stripped from the end.
        """
        # Normalize token to bytes once
        token_bytes = eof_token if isinstance(eof_token, (bytes, bytearray)) else eof_token.encode('utf-8')
        token_len = len(token_bytes)
        data = bytearray()
        active_socket.settimeout(10.0)
        while True:
            try:
                packet = active_socket.recv(buffer_size)
                if not packet:
                    break  # Connection closed by the server
                data.extend(packet)
                # Only stop when buffer definitively ends with token
                if len(data) >= token_len and data.endswith(token_bytes):
                    data = data[:-token_len]
                    break
            except socket.timeout:
                # Continue waiting; otherwise return partial binary payloads on timeout
                continue
        return data
        # raise NotImplementedError("Your implementation here.")

    def initialize(self, host, port) -> tuple[socket.socket, str]:
        """
        1) Creates a socket object and connects to the server.
        2) receives the random token (10 bytes) used to indicate end of messages.
        3) Displays the current working directory returned from the server (output of get_working_directory_info() at the server).
        Use the helper method: receive_message_ending_with_token() to receive the message from the server.
        :param host: the ip address of the server
        :param port: the port number of the server
        :return: the created socket object
        :return: the eof_token
        """
        # Step 1: Create a socket and connect to the server
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))
        print('Connected to server at IP:', host, 'and Port:', port)
        # Step 2: Receive the EOF token from the server (exact 10 bytes)
        expected_len = 10
        eof_token = bytearray()
        while len(eof_token) < expected_len:
            chunk = client_socket.recv(expected_len - len(eof_token))
            if not chunk:
                raise ConnectionError("Failed to receive full EOF token from server")
            eof_token.extend(chunk)
        print('Handshake Done. EOF is:', eof_token)
        # Step 3: Receive and display the current working directory from the server
        cwd_info = self.receive_message_ending_with_token(client_socket, 1024, eof_token)
        print('Current Working Directory:', cwd_info.decode('utf-8'))
        return client_socket, eof_token.decode('utf-8')

        # raise NotImplementedError("Your implementation here.")

    def issue_cd(self, command_and_arg, client_socket, eof_token) -> None:
        """
        Sends the full cd command entered by the user to the server. The server changes its cwd accordingly and sends back
        the new cwd info.
        Use the helper method: receive_message_ending_with_token() to receive the message from the server.
        :param command_and_arg: full command (with argument) provided by the user.
        :param client_socket: the active client socket object.
        :param eof_token: a token to indicate the end of the message.
        """
        client_socket.sendall((command_and_arg + eof_token).encode('utf-8'))
        response = self.receive_message_ending_with_token(client_socket, 1024, eof_token.encode('utf-8'))
        print(response.decode('utf-8'))
        # raise NotImplementedError("Your implementation here.")

    def issue_mkdir(self, command_and_arg, client_socket, eof_token) -> None:
        """
        Sends the full mkdir command entered by the user to the server. The server creates the sub directory and sends back
        the new cwd info.
        Use the helper method: receive_message_ending_with_token() to receive the message from the server.
        :param command_and_arg: full command (with argument) provided by the user.
        :param client_socket: the active client socket object.
        :param eof_token: a token to indicate the end of the message.
        """
        client_socket.sendall((command_and_arg + eof_token).encode('utf-8'))
        response = self.receive_message_ending_with_token(client_socket, 1024, eof_token.encode('utf-8'))
        print(response.decode('utf-8'))
        # raise NotImplementedError("Your implementation here.")

    def issue_rm(self, command_and_arg, client_socket, eof_token) -> None:
        """
        Sends the full rm command entered by the user to the server. The server removes the file or directory and sends back
        the new cwd info.
        Use the helper method: receive_message_ending_with_token() to receive the message from the server.
        :param command_and_arg: full command (with argument) provided by the user.
        :param client_socket: the active client socket object.
        :param eof_token: a token to indicate the end of the message.
        """
        client_socket.sendall((command_and_arg + eof_token).encode('utf-8'))
        response = self.receive_message_ending_with_token(client_socket, 1024, eof_token.encode('utf-8'))
        print(response.decode('utf-8'))
        # raise NotImplementedError("Your implementation here.")

    def issue_ul(self, command_and_arg, client_socket, eof_token) -> None:
        """
        Sends the full ul command entered by the user to the server. Then, it reads the file to be uploaded as binary
        and sends it to the server. The server creates the file on its end and sends back the new cwd info.
        Use the helper method: receive_message_ending_with_token() to receive the message from the server.
        :param command_and_arg: full command (with argument) provided by the user.
        :param client_socket: the active client socket object.
        :param eof_token: a token to indicate the end of the message.
        """
        file_path = command_and_arg.split(" ", 1)[1].strip()
        
        try:
            with open(file_path, 'rb') as file:
                file_data = file.read()
            print(f"[UL] Sending command and size: name={file_path}, size={len(file_data)}")
            client_socket.sendall((command_and_arg + eof_token).encode('utf-8'))
            # Send length header (token-terminated), then raw bytes
            client_socket.sendall((str(len(file_data)) + eof_token).encode('utf-8'))
            client_socket.sendall(file_data)
            print("[UL] Waiting for server response (cwd info)...")
            response = self.receive_message_ending_with_token(client_socket, 1024, eof_token.encode('utf-8'))
            print(response.decode('utf-8'))
        except Exception as e:
            print(f"An error occurred during upload: {e}")
        # raise NotImplementedError("Your implementation here.")

    def issue_dl(self, command_and_arg, client_socket, eof_token) -> None:
        """
        Sends the full dl command entered by the user to the server. Then, it receives the content of the file via the
        socket and re-creates the file in the local directory of the client. Finally, it receives the latest cwd info from
        the server.
        Use the helper method: receive_message_ending_with_token() to receive the message from the server.
        :param command_and_arg: full command (with argument) provided by the user.
        :param client_socket: the active client socket object.
        :param eof_token: a token to indicate the end of the message.
        """
        client_socket.sendall((command_and_arg + eof_token).encode('utf-8'))
        # First, receive the size header (token-terminated), allowing for coalesced file bytes
        size_bytes, remainder = self._read_frame_with_remainder(client_socket, 1024, eof_token.encode('utf-8'))
        size_str = size_bytes.decode('utf-8').strip()
        expected_len = int(size_str)
        # Then, receive exactly expected_len raw bytes, accounting for any remainder already read
        received = bytearray(remainder)
        to_read = expected_len - len(received)
        if to_read < 0:
            received = received[:expected_len]
            to_read = 0
        if to_read > 0:
            received.extend(self._recv_exact(client_socket, to_read))
        file_data = bytes(received)
        file_name = command_and_arg.split(" ", 1)[1].strip()
                
        try:
            with open(file_name, 'wb') as file:
                file.write(file_data)
            print(f"File downloaded successfully to: {file_name}")
        except Exception as e:
            print(f"Error saving downloaded file: {e}")
        
        response = self.receive_message_ending_with_token(client_socket, 1024, eof_token.encode('utf-8'))
        print(response.decode('utf-8'))
        # raise NotImplementedError("Your implementation here.")

    def issue_wordcount(self, command_and_arg, client_socket, eof_token) -> int:
        """
        Sends the full wordcount command entered by the user to the server. Then, it receives the number of words in the file via the socket. Finally, it receives the latest cwd info from
        the server.
        Use the helper method: receive_message_ending_with_token() to receive the message from the server.
        :param command_and_arg: full command (with argument) provided by the user.
        :param client_socket: the active client socket object.
        :param eof_token: a token to indicate the end of the message.
        :return: wordcount int
        """
        client_socket.sendall((command_and_arg + eof_token).encode('utf-8'))
        wordcount_data = self.receive_message_ending_with_token(client_socket, 1024, eof_token.encode('utf-8'))
        wordcount = int(wordcount_data.decode('utf-8'))
        print('Word Count:', wordcount)
        response = self.receive_message_ending_with_token(client_socket, 1024, eof_token.encode('utf-8'))
        print(response.decode('utf-8'))
        return wordcount
        # raise NotImplementedError("Your implementation here.")

    def issue_wordsort(self, command_and_arg, client_socket, eof_token) -> list[str]:
        """
        Sends the full wordsort command entered by the user to the server. Then, it receives the list of alphabetically sorted words via the
        socket. Finally, it receives the latest cwd info from the server.
        Use the helper method: receive_message_ending_with_token() to receive the message from the server.
        :param command_and_arg: full command (with argument) provided by the user.
        :param client_socket: the active client socket object.
        :param eof_token: a token to indicate the end of the message.
        :return: list
        """
        client_socket.sendall((command_and_arg + eof_token).encode('utf-8'))
        sorted_words_data = self.receive_message_ending_with_token(client_socket, 1024, eof_token.encode('utf-8'))
        sorted_words = sorted_words_data.decode('utf-8').splitlines()
        print('Sorted Words:', sorted_words)
        response = self.receive_message_ending_with_token(client_socket, 1024, eof_token.encode('utf-8'))
        print(response.decode('utf-8'))
        return sorted_words
        # raise NotImplementedError("Your implementation here.")

    def issue_search(self, command_and_arg, client_socket, eof_token) -> dict[str, int]:
        """
        Sends the full search command entered by the user to the server. Then, it receives the dictionary of words their the number of matches i.e {  token1: 5, token2: 6, ...,} via the socket.
        Finally, it receives the latest cwd info from the server.
        Use the helper method: receive_message_ending_with_token() to receive the message from the server.
        :param command_and_arg: full command (with argument) provided by the user.
        :param client_socket: the active client socket object.
        :param eof_token: a token to indicate the end of the message.
        :return: dict
        """
        client_socket.sendall((command_and_arg + eof_token).encode('utf-8'))
        search_results_data = self.receive_message_ending_with_token(client_socket, 1024, eof_token.encode('utf-8'))
        search_results_lines = search_results_data.decode('utf-8').splitlines()
        search_results = {}
        for line in search_results_lines:
            if ': ' in line:
                word, count = line.split(': ', 1)
                search_results[word] = int(count)
        print('Search Results:', search_results)

        response = self.receive_message_ending_with_token(client_socket, 1024, eof_token.encode('utf-8'))
        print(response.decode('utf-8'))
        return search_results
        # raise NotImplementedError("Your implementation here.")

    def issue_split(self, command_and_arg, client_socket, eof_token) -> int:
        """
        Sends the full split command entered by the user to the server. Then, save the splits into files with naming pattern filename}_split_{split number}.txt
        then receives the number of splits via the socket. Finally, it receives the latest cwd info from the server.
        Use the helper method: receive_message_ending_with_token() to receive the message from the server.
        :param command_and_arg: full command (with argument) provided by the user.
        :param client_socket: the active client socket object.
        :param eof_token: a token to indicate the end of the message.
        :return: splitcount int
        """
        client_socket.sendall((command_and_arg + eof_token).encode('utf-8'))
        splitcount_data = self.receive_message_ending_with_token(client_socket, 1024, eof_token.encode('utf-8'))
        splitcount = int(splitcount_data.decode('utf-8'))
        print('Number of splits:', splitcount)
        response = self.receive_message_ending_with_token(client_socket, 1024, eof_token.encode('utf-8'))
        print(response.decode('utf-8'))
        return splitcount
        # raise NotImplementedError("Your implementation here.")

    # def issue_exit(command_and_arg, client_socket, eof_token) -> None:
    def issue_exit(self, command_and_arg, client_socket, eof_token) -> None:
        """
        Sends the full exit command entered by the user to the server. Then, close the client socket and  print message "the client has exited".
        Use the helper method: receive_message_ending_with_token() to receive the message from the server.
        :param command_and_arg: full command (with argument) provided by the user.
        :param client_socket: the active client socket object.
        :param eof_token: a token to indicate the end of the message.
        :return:
        """
        client_socket.sendall((command_and_arg + eof_token).encode('utf-8'))
        
        exit_message = self.receive_message_ending_with_token(client_socket, 1024, eof_token.encode('utf-8'))
        print(exit_message.decode('utf-8'))
        print("the client has exited")

        client_socket.close()
        # raise NotImplementedError("Your implementation here.")

    def start(self) -> None:
        """
        1) Initialization
        2) Accepts user input and issue commands until exit.
        """
        # initialize
        self.client_socket, self.eof_token = self.initialize(self.host, self.port)
        # raise NotImplementedError("Your implementation here.")
        while True:
            # get user input
            user_input = input("Enter command (or 'exit' to quit): ")
            command_and_arg = user_input.strip().split(" ", 1)
            command = command_and_arg[0]
            if command == "mkdir":
                self.issue_mkdir(user_input, self.client_socket, self.eof_token)
            elif command == "cd":
                self.issue_cd(user_input, self.client_socket, self.eof_token)
            elif command == "ul":
                self.issue_ul(user_input, self.client_socket, self.eof_token)
            elif command == "dl":
                self.issue_dl(user_input, self.client_socket, self.eof_token)
            elif command == "wordcount":
                self.issue_wordcount(user_input, self.client_socket, self.eof_token)
            elif command == "wordsort":
                self.issue_wordsort(user_input, self.client_socket, self.eof_token)
            elif command == "search":
                self.issue_search(user_input, self.client_socket, self.eof_token)
            elif command == "split":
                self.issue_split(user_input, self.client_socket, self.eof_token)
            elif command == "rm":
                self.issue_rm(user_input, self.client_socket, self.eof_token)
            elif command == "exit":
                self.issue_exit(user_input, self.client_socket, self.eof_token)
                break
            else:
                print("Invalid command. Please try again.")

        print('Exiting the application.')


## Don't Modify Below ##
def run_client():
    # HOST = "127.0.0.1"  # The server's hostname or IP address
    # PORT = 65432  # The port used by the server
    HOST = os.getenv("SERVER_IP", "127.0.0.1")
    PORT = int(os.getenv("SERVER_PORT", "65432"))

    client = Client(HOST, PORT)
    client.start()


if __name__ == "__main__":
    run_client()