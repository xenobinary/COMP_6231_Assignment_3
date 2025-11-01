import socket
import random
from threading import Thread
import os
import shutil
from pathlib import Path
import time


class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = None
    
    def _recv_exact(self, active_socket: socket.socket, n: int) -> bytearray:
        """Receive exactly n bytes from the socket, or raise if connection closes early."""
        data = bytearray()
        while len(data) < n:
            packet = active_socket.recv(n - len(data))
            if not packet:
                raise ConnectionError("Socket closed before receiving expected bytes")
            data.extend(packet)
        return data

    def _read_frame_with_remainder(self, active_socket: socket.socket, buffer_size: int, eof_token):
        """Read from socket until the first occurrence of eof_token is found anywhere in the stream.
        Returns a tuple: (payload_without_token, remainder_after_token).
        This avoids blocking when the next payload starts in the same TCP packet.
        """
        token_bytes = eof_token.encode('utf-8') if isinstance(eof_token, str) else eof_token
        buf = bytearray()
        token_len = len(token_bytes)
        while True:
            chunk = active_socket.recv(buffer_size)
            if not chunk:
                # No more data; return whatever we have (no token found)
                return buf, bytearray()
            buf.extend(chunk)
            idx = buf.find(token_bytes)
            if idx != -1:
                # Split at first occurrence of token
                payload = buf[:idx]
                remainder = buf[idx + token_len:]
                return payload, remainder

    def start(self) -> None:
        """
        1) Create server, bind and start listening.
        2) Accept clinet connections and serve the requested commands.

        Note: Use ClientThread for each client connection.
        """
        # Create a socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with self.server_socket as s:
            # Enable address reuse before binding
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind the socket to the specified address and port
            s.bind((self.host, self.port))
        # Listen for incoming connections
            s.listen()
            print(f"Server listening on {self.host}:{self.port}")
        # while True:
        # Accept incoming connections
        # print(f"Accepted connection from {client_address}")
        # send random eof token
            while True:
                client_socket, client_address = s.accept()
                print(f"Accepted connection from {client_address}")
                # Generate a random EOF token
                eof_token = self.generate_random_eof_token()
                # Send the random EOF token to the client
                client_socket.send(eof_token.encode('utf-8'))

                try:
                    # Handle the client requests using ClientThread
                    client_thread = ClientThread(self, client_socket, client_address, eof_token)
                    client_thread.start()
                except Exception as e:
                    print(f"Error: {e}")
                # Do NOT close client_socket here; the ClientThread owns and closes it

        # raise NotImplementedError("Your implementation here.")

    def get_working_directory_info(self, working_directory) -> str:
        """
        Creates a string representation of a working directory and its contents.
        :param working_directory: path to the directory
        :return: string of the directory and its contents.
        """
        dirs = "\n-- " + "\n-- ".join(
            [i.name for i in Path(working_directory).iterdir() if i.is_dir()]
        )
        files = "\n-- " + "\n-- ".join(
            [i.name for i in Path(working_directory).iterdir() if i.is_file()]
        )
        dir_info = f"Current Directory: {working_directory}:\n|{dirs}{files}"
        return dir_info

    def generate_random_eof_token(self) -> str:
        """Helper method to generates a random token that starts with '<' and ends with '>'.
        The total length of the token (including '<' and '>') should be 10.
        Examples: '<1f56xc5d>', '<KfOVnVMV>'
        return: the generated token.
        """
        token = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))
        return f"<{token}>"

    def receive_message_ending_with_token(
        self, active_socket, buffer_size, eof_token
    ) -> bytearray:
        """
        Same implementation as in receive_message_ending_with_token() in client.py
        A helper method to receives a bytearray message of arbitrary size sent on the socket.
        This method returns the message WITHOUT the eof_token at the end of the last packet.
        :param active_socket: a socket object that is connected to the server
        :param buffer_size: the buffer size of each recv() call
        :param eof_token: a token that denotes the end of the message.
        :return: a bytearray message with the eof_token stripped from the end.
        """
        # Normalize token to bytes once
        token_bytes = eof_token.encode('utf-8') if isinstance(eof_token, str) else eof_token
        data = bytearray()
        token_len = len(token_bytes)
        while True:
            packet = active_socket.recv(buffer_size)
            if not packet:
                break  # Connection closed
            data.extend(packet)
            # Only stop when the aggregated buffer ends with the token
            if len(data) >= token_len and data.endswith(token_bytes):
                # Strip the token before returning
                data = data[:-token_len]
                break
        return data
        # raise NotImplementedError("Your implementation here.")

    def handle_cd(self, current_working_directory, new_working_directory) -> str:
        """
        Handles the client cd commands. Reads the client command and changes the current_working_directory variable
        accordingly. Returns the absolute path of the new current working directory.
        :param current_working_directory: string of current working directory
        :param new_working_directory: name of the sub directory or '..' for parent
        :return: absolute path of new current working directory
        """
        try:
            if new_working_directory == "..":
                new_dir = os.path.join(current_working_directory, "..")
            else:
                new_dir = os.path.join(current_working_directory, new_working_directory)
            if os.path.exists(new_dir) and os.path.isdir(new_dir):
                return os.path.abspath(new_dir)
            else:
                return current_working_directory
        except Exception as e:
            print(f"Error changing directory to {new_working_directory}: {e}")
            return current_working_directory

    def handle_mkdir(self, current_working_directory, directory_name) -> None:
        """
        Handles the client mkdir commands. Creates a new sub directory with the given name in the current working directory.
        :param current_working_directory: string of current working directory
        :param directory_name: name of new sub directory
        """
        try:
            os.mkdir(os.path.join(current_working_directory, directory_name))
        except Exception as e:
            print(f"Error creating directory {directory_name}: {e}")
        # raise NotImplementedError("Your implementation here.")

    def handle_rm(self, current_working_directory, object_name) -> None:
        """
        Handles the client rm commands. Removes the given file or sub directory. Uses the appropriate removal method
        based on the object type (directory/file).
        :param current_working_directory: string of current working directory
        :param object_name: name of sub directory or file to remove
        """
        path = os.path.join(current_working_directory, object_name)
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.isfile(path):
                os.remove(path)
        except Exception as e:
            print(f"Error removing {object_name}: {e}")
        # raise NotImplementedError("Your implementation here.")

    def handle_ul(
        self,
        current_working_directory,
        file_name,
        service_socket,
        eof_token,
        expected_len=None,
        initial_remainder=b"",
    ) -> None:
        """
        Handles the client ul commands. First, it reads the payload, i.e. file content from the client, then creates the
        file in the current working directory.
        Use the helper method: receive_message_ending_with_token() to receive the message from the client.
        :param current_working_directory: string of current working directory
        :param file_name: name of the file to be created.
        :param service_socket: active socket with the client to read the payload/contents from.
        :param eof_token: a token to indicate the end of the message.
        """
        try:
            # Ensure file is created within server's current directory
            safe_name = os.path.basename(file_name)
            file_path = os.path.join(current_working_directory, safe_name)
            print(f"[UL] Start: name={safe_name}")
            if expected_len is None:
                # Backward compatibility: read size header now
                size_bytes, remainder = self._read_frame_with_remainder(service_socket, 1024, eof_token)
                size_str = size_bytes.decode('utf-8').strip()
                expected_len = int(size_str)
                init_bytes = remainder
            else:
                init_bytes = initial_remainder or b""
            if expected_len < 0:
                raise ValueError("Invalid file size")
            print(f"[UL] Size header ok: expected_len={expected_len}, remainder_after_header={len(init_bytes)}")

            # We may have already received part of the file in 'init_bytes'
            received = bytearray(init_bytes)
            to_read = expected_len - len(received)
            if to_read < 0:
                # More bytes than needed were already read; truncate the extra
                received = received[:expected_len]
                to_read = 0

            if to_read > 0:
                print(f"[UL] Reading exact bytes: to_read={to_read}")
                received.extend(self._recv_exact(service_socket, to_read))

            with open(file_path, 'wb') as f:
                f.write(received)
            print(f"[UL] Done for {safe_name}: wrote={len(received)} bytes at {file_path}")
        except Exception as e:
            print(f"Error uploading file {file_name}: {e}")
            # service_socket.sendall((eof_token).encode('utf-8'))
        # raise NotImplementedError("Your implementation here.")

    def handle_dl(
        self, current_working_directory, file_name, service_socket, eof_token
    ) -> None:
        """
        Handles the client dl commands. First, it loads the given file as binary, then sends it to the client via the
        given socket.
        :param current_working_directory: string of current working directory
        :param file_name: name of the file to be sent to client
        :param service_socket: active service socket with the client
        :param eof_token: a token to indicate the end of the message.
        """
        try:
            # Ensure file path is based on server's cwd
            safe_name = os.path.basename(file_name)
            file_path = os.path.join(current_working_directory, safe_name)
            with open(file_path, 'rb') as f:
                file_data = f.read()
            # Send size header (token-terminated), then raw file bytes
            service_socket.sendall((str(len(file_data)) + eof_token).encode('utf-8'))
            service_socket.sendall(file_data)
        except Exception as e:
            print(f"Error downloading file {file_name}: {e}")
            # service_socket.sendall((eof_token).encode('utf-8'))
        # raise NotImplementedError("Your implementation here.")

    def handle_search(
        self, current_working_directory, file_name, wordslist, service_socket, eof_token
    ) -> None:
        """
        Handles the search  commands. First, it opens the file and  perform search, then sends  the dictionary of words with their the number of case-insensitive matches i.e {  token1: 5, token2: 6, ...,}. to the client via the given socket.
        :param current_working_directory: string of current working directory
        :param file_name: name of the file to be sent to client
        :param wordslist: list of search words
        :param service_socket: active service socket with the client
        :param eof_token: a token to indicate the end of the message.
        """
        try:
            with open(os.path.join(current_working_directory, file_name), 'r') as f:
                text = f.read().lower()
            words = [word.strip('.,;:!?()[]{}"\'') for word in text.split()]
            word_count = {word: words.count(word.lower()) for word in wordslist}
            result = "\n".join([f"{word}: {count}" for word, count in word_count.items()])
            service_socket.sendall((result + eof_token).encode('utf-8'))
        except Exception as e:
            print(f"Error searching in {file_name}: {e}")
            # service_socket.sendall((eof_token).encode('utf-8'))
        # raise NotImplementedError("Your implementation here.")

    def handle_split(
        self, current_working_directory, file_name, splitlist, service_socket, eof_token
    ) -> None:
        """
        Handles the split  commands. First, it opens the file and perform search, then save the splits into files with naming pattern {filename}_split_{split number}.txt
        then sends the number of splits to the client via the given socket.
        :param current_working_directory: string of current working directory
        :param file_name: name of the file to be sent to client
        :param splitlist: list of split words
        :param service_socket: active service socket with the client
        :param eof_token: a token to indicate the end of the message.
        """
        try:
            with open(os.path.join(current_working_directory, file_name), 'r') as f:
                text = f.read().lower()
            
            # Initialize splits with the entire text
            splits = [text]
            
            # For each split word, further split all current segments
            for split_word in splitlist:
                new_splits = []
                for segment in splits:
                    # Split the segment by the current split word and filter out empty segments
                    parts = [part for part in segment.split(split_word.strip()) if part.strip()]
                    new_splits.extend(parts)
                splits = new_splits
            
            # Write each split to a file
            for i, split in enumerate(splits):
                split_file_name = f"{file_name}_split_{i+1}.txt"
                with open(os.path.join(current_working_directory, split_file_name), 'w') as sf:
                    sf.write(split)
                    print(split_file_name + " with")
                    print("'" + split + "'\n")
            
            # Send the number of splits back to the client
            service_socket.sendall((str(len(splits)) + eof_token).encode('utf-8'))
        except Exception as e:
            print(f"Error splitting {file_name}: {e}")
            # service_socket.sendall(("0" + eof_token).encode('utf-8'))

    def handle_wordsort(
        self, current_working_directory, file_name, service_socket, eof_token
    ) -> None:
        """
        Handles the wordsort commands. First, it opens the file and perform unique listing for words then sort them,  then sends the list of alphabetically sorted words via the
        to the client via the given socket.
        :param current_working_directory: string of current working directory
        :param file_name: name of the file to be sent to client
        :param splitlist: list of split words
        :param service_socket: active service socket with the client
        :param eof_token: a token to indicate the end of the message.
        """
        try:
            with open(os.path.join(current_working_directory, file_name), 'r') as f:
                text = f.read().lower()
            words = [word.strip('.,;:!?()[]{}"\'') for word in text.split()]
            unique_words = set(words)
            sorted_words = sorted(unique_words)
            result = "\n".join(sorted_words)
            service_socket.sendall((result + eof_token).encode('utf-8'))
        except Exception as e:
            print(f"Error sorting words in {file_name}: {e}")
            # service_socket.sendall((eof_token).encode('utf-8'))
        # raise NotImplementedError("Your implementation here.")

    def handle_wordcount(
        self, current_working_directory, file_name, service_socket, eof_token
    ) -> None:
        """
        Handles the wordcount commands. First, it opens the file and perform unique listing for words and count them,  then sends the count of unique words to the client via the given socket.
        :param current_working_directory: string of current working directory
        :param file_name: name of the file to be sent to client
        :param splitlist: list of split words
        :param service_socket: active service socket with the client
        :param eof_token: a token to indicate the end of the message.
        """
        try:
            with open(os.path.join(current_working_directory, file_name), 'r') as f:
                text = f.read().lower()
            words = [word.strip('.,;:!?()[]{}"\'') for word in text.split()]
            unique_words = set(words)
            count = len(unique_words)
            service_socket.sendall((str(count) + eof_token).encode('utf-8'))
        except Exception as e:
            print(f"Error counting words in {file_name}: {e}")
            # service_socket.sendall(("0" + eof_token).encode('utf-8'))

class ClientThread(Thread):
    def __init__(
        self,
        server: Server,
        service_socket: socket.socket,
        address: str,
        eof_token: str,
    ):
        Thread.__init__(self)
        self.server_obj = server
        self.service_socket = service_socket
        self.address = address
        self.eof_token = eof_token
        # Buffer to hold any bytes read beyond a token-delimited frame
        self._recv_buffer = bytearray()

    def _read_frame(self) -> bytearray:
        """Read a token-terminated frame from the socket using an internal buffer.
        Returns payload without the token. Any bytes after the token stay in the buffer.
        """
        token_bytes = self.eof_token.encode('utf-8')
        token_len = len(token_bytes)
        # Check if token already in buffer
        while True:
            idx = self._recv_buffer.find(token_bytes)
            if idx != -1:
                payload = self._recv_buffer[:idx]
                # keep remainder after token in buffer
                self._recv_buffer = self._recv_buffer[idx + token_len:]
                return payload
            # Need more data
            chunk = self.service_socket.recv(4096)
            if not chunk:
                # Return whatever is left (no token)
                payload = bytes(self._recv_buffer)
                self._recv_buffer.clear()
                return bytearray(payload)
            self._recv_buffer.extend(chunk)

    def run(self):
        print ("Connection from : ", self.address)
        # raise NotImplementedError("Your implementation here.")

        try:
            # establish working directory for current client
            current_working_directory = os.path.abspath(os.getcwd())
            # send the current dir info
            dir_info = self.server_obj.get_working_directory_info(current_working_directory)
            self.service_socket.sendall((dir_info + self.eof_token).encode('utf-8'))

            while True:
                # get the command and arguments and call the corresponding method
                raw_msg = self._read_frame()
                try:
                    command_and_arg = raw_msg.decode('utf-8').strip()
                except UnicodeDecodeError:
                    # If decoding fails, we most likely consumed a leftover binary chunk
                    # (e.g., from an upload). Discard and continue waiting for the next
                    # proper UTF-8 command instead of crashing.
                    print(f"Warning: Discarded non-UTF-8 payload of {len(raw_msg)} bytes from {self.address}")
                    continue
                print(f"Received command: {command_and_arg} from {self.address}")
                if not command_and_arg:
                    break  # client disconnected
                # Handle mkdir command
                if command_and_arg.startswith("mkdir "):
                    directory_name = command_and_arg[6:].strip()
                    self.server_obj.handle_mkdir(current_working_directory, directory_name)
                # Handle cd command
                elif command_and_arg.startswith("cd "):
                    new_working_directory = command_and_arg[3:].strip()
                    current_working_directory = self.server_obj.handle_cd(current_working_directory, new_working_directory)
                # Handle ul command
                elif command_and_arg.startswith("ul "):
                    file_name = command_and_arg[3:].strip()
                    # Next frame is the size header
                    size_header = self._read_frame()
                    try:
                        expected_len = int(size_header.decode('utf-8').strip())
                    except Exception:
                        print(f"Invalid UL size header from {self.address}: {size_header!r}")
                        expected_len = 0
                    # Any bytes already in buffer belong to file payload
                    initial = bytes(self._recv_buffer)
                    self._recv_buffer.clear()
                    self.server_obj.handle_ul(
                        current_working_directory,
                        file_name,
                        self.service_socket,
                        self.eof_token,
                        expected_len,
                        initial,
                    )
                # Handle dl command
                elif command_and_arg.startswith("dl "):
                    file_name = command_and_arg[3:].strip()
                    self.server_obj.handle_dl(current_working_directory, file_name, self.service_socket, self.eof_token)
                # Handle wordcount command
                elif command_and_arg.startswith("wordcount "):
                    file_name = command_and_arg[10:].strip()
                    self.server_obj.handle_wordcount(current_working_directory, file_name, self.service_socket, self.eof_token)
                elif command_and_arg.startswith("wordsort "):
                    file_name = command_and_arg[9:].strip()
                    self.server_obj.handle_wordsort(current_working_directory, file_name, self.service_socket, self.eof_token)
                # Handle search command
                elif command_and_arg.startswith("search "):
                    parts = command_and_arg[7:].strip().split()
                    # Handle invalid format
                    if(len(parts) < 2):
                        print(f"Invalid search command format from {self.address}")
                        continue

                    file_name = parts[0]
                    wordslist = [word.strip() for word in parts[1].split(',')]

                    self.server_obj.handle_search(current_working_directory, file_name, wordslist, self.service_socket, self.eof_token)
                # Handle split command
                elif command_and_arg.startswith("split "):
                    parts = command_and_arg[6:].strip().split()
                    # Handle invalid format
                    if(len(parts) < 2):
                        print(f"Invalid split command format from {self.address}")
                        continue

                    file_name = parts[0]
                    splitlist = [split.strip() for split in parts[1].split(',')]

                    self.server_obj.handle_split(current_working_directory, file_name, splitlist, self.service_socket, self.eof_token)
                # Handle rm command
                elif command_and_arg.startswith("rm "):
                    object_name = command_and_arg[3:].strip()
                    self.server_obj.handle_rm(current_working_directory, object_name)
                # Handle exit command
                elif command_and_arg == "exit":
                    self.service_socket.sendall(("Exiting. Goodbye!" + self.eof_token).encode('utf-8'))
                    break

                # sleep for 1 second
                time.sleep(1)
                # send current dir info
                dir_info = self.server_obj.get_working_directory_info(current_working_directory)
                self.service_socket.sendall((dir_info + self.eof_token).encode('utf-8'))

        finally:
            try:
                self.service_socket.close()
            except Exception:
                pass
            print('Connection closed from:', self.address)


def run_server():
    HOST = "0.0.0.0"
    PORT = 65432

    server = Server(HOST, PORT)
    server.start()


if __name__ == "__main__":
    run_server()
