import socket
import os
import json
import select
from pathlib import Path

HOST = '127.0.0.1'
PORT = 5000
BUFFER_SIZE = 2048  # 2KB
SERVER_FILES_DIR = './server_files'

Path(SERVER_FILES_DIR).mkdir(exist_ok=True)


class ClientState:
    def __init__(self, socket, address):
        self.socket = socket
        self.address = address
        self.state = 'waiting_command'
        self.upload_filename = None
        self.upload_size = 0
        self.upload_received = 0
        self.upload_file = None
        self.download_filename = None
        self.download_size = 0
        self.download_sent = 0
        self.download_file = None
        self.buffer = b''

# /list
def get_file_list():
    try:
        files = os.listdir(SERVER_FILES_DIR)
        files = [f for f in files if os.path.isfile(os.path.join(SERVER_FILES_DIR, f))]
        return files
    except Exception as e:
        return []


def handle_list_command(client_state):
    try:
        files = get_file_list()
        response = {
            'status': 'success',
            'command': 'list',
            'files': files,
            'count': len(files)
        }
        client_state.socket.send(json.dumps(response).encode('utf-8'))
        print(f"[LIST] Sent file list with {len(files)} files to {client_state.address}")
    except Exception as e:
        response = {'status': 'error', 'message': str(e)}
        client_state.socket.send(json.dumps(response).encode('utf-8'))
        print(f"[ERROR] List command failed for {client_state.address}: {e}")

# /upload
def start_upload(client_state, filename, file_size):
    """Initialize file upload"""
    try:
        filename = os.path.basename(filename)
        file_path = os.path.join(SERVER_FILES_DIR, filename)

        client_state.state = 'uploading'
        client_state.upload_filename = filename
        client_state.upload_size = file_size
        client_state.upload_received = 0
        client_state.upload_file = open(file_path, 'wb')

        response = {'status': 'ready', 'message': 'Ready to receive file'}
        client_state.socket.send(json.dumps(response).encode('utf-8'))
        print(f"[UPLOAD] Starting upload: {filename} ({file_size} bytes) from {client_state.address}")

    except Exception as e:
        response = {'status': 'error', 'message': str(e)}
        client_state.socket.send(json.dumps(response).encode('utf-8'))
        print(f"[ERROR] Upload initialization failed for {client_state.address}: {e}")


def continue_upload(client_state):
    """Continue receiving file data"""
    try:
        while True:
            remaining = client_state.upload_size - client_state.upload_received
            if remaining <= 0:
                client_state.upload_file.close()
                response = {
                    'status': 'success',
                    'message': f'File {client_state.upload_filename} uploaded successfully',
                    'filename': client_state.upload_filename,
                    'size': client_state.upload_received
                }
                client_state.socket.send(json.dumps(response).encode('utf-8'))
                print(f"[UPLOAD] Completed: {client_state.upload_filename} ({client_state.upload_received} bytes)")

                client_state.state = 'waiting_command'
                client_state.upload_filename = None
                client_state.upload_size = 0
                client_state.upload_received = 0
                client_state.upload_file = None
                break

            chunk_size = min(BUFFER_SIZE, remaining)
            chunk = client_state.socket.recv(chunk_size)

            if not chunk:
                if client_state.upload_file:
                    client_state.upload_file.close()
                print(f"[UPLOAD] Connection lost during upload from {client_state.address}")
                break

            client_state.upload_file.write(chunk)
            client_state.upload_received += len(chunk)

    except Exception as e:
        if client_state.upload_file:
            client_state.upload_file.close()
        response = {'status': 'error', 'message': str(e)}
        client_state.socket.send(json.dumps(response).encode('utf-8'))
        print(f"[ERROR] Upload failed for {client_state.address}: {e}")
        client_state.state = 'waiting_command'

# /download
def start_download(client_state, filename):
    try:
        filename = os.path.basename(filename)
        file_path = os.path.join(SERVER_FILES_DIR, filename)

        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            response = {'status': 'error', 'message': f'File {filename} not found'}
            client_state.socket.send(json.dumps(response).encode('utf-8'))
            print(f"[DOWNLOAD] File not found: {filename} for {client_state.address}")
            return

        file_size = os.path.getsize(file_path)

        client_state.state = 'downloading'
        client_state.download_filename = filename
        client_state.download_size = file_size
        client_state.download_sent = 0
        client_state.download_file = open(file_path, 'rb')

        metadata = {
            'status': 'found',
            'filename': filename,
            'size': file_size
        }
        client_state.socket.send(json.dumps(metadata).encode('utf-8'))
        print(f"[DOWNLOAD] Starting download: {filename} ({file_size} bytes) to {client_state.address}")

    except Exception as e:
        response = {'status': 'error', 'message': str(e)}
        client_state.socket.send(json.dumps(response).encode('utf-8'))
        print(f"[ERROR] Download initialization failed for {client_state.address}: {e}")


def continue_download(client_state):
    """Continue sending file data"""
    try:
        while True:
            remaining = client_state.download_size - client_state.download_sent
            if remaining <= 0:
                client_state.download_file.close()
                print(f"[DOWNLOAD] Completed: {client_state.download_filename} ({client_state.download_sent} bytes)")

                client_state.state = 'waiting_command'
                client_state.download_filename = None
                client_state.download_size = 0
                client_state.download_sent = 0
                client_state.download_file = None
                break

            chunk = client_state.download_file.read(min(BUFFER_SIZE, remaining))
            if not chunk:
                break

            client_state.socket.sendall(chunk)
            client_state.download_sent += len(chunk)

    except Exception as e:
        if client_state.download_file:
            client_state.download_file.close()
        response = {'status': 'error', 'message': str(e)}
        client_state.socket.send(json.dumps(response).encode('utf-8'))
        print(f"[ERROR] Download failed for {client_state.address}: {e}")
        client_state.state = 'waiting_command'


def process_command(client_state, command):
    try:
        parts = command.split()
        cmd = parts[0].lower() if parts else ''

        if cmd == '/list':
            handle_list_command(client_state)

        elif cmd == '/upload':
            pass

        elif cmd == '/download':
            if len(parts) < 2:
                response = {'status': 'error', 'message': 'Usage: /download <filename>'}
                client_state.socket.send(json.dumps(response).encode('utf-8'))
            else:
                filename = parts[1]
                start_download(client_state, filename)
                
        else:
            response = {
                'status': 'error',
                'message': 'Unknown command. Available: /list, /upload, /download <filename>, /quit'
            }
            client_state.socket.send(json.dumps(response).encode('utf-8'))

    except Exception as e:
        response = {'status': 'error', 'message': str(e)}
        client_state.socket.send(json.dumps(response).encode('utf-8'))
        print(f"[ERROR] Command processing failed for {client_state.address}: {e}")

    return True


def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.setblocking(False)
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        print(f"[SERVER] Server ready...")

        sockets_list = [server_socket]
        clients = {}

        while True:
            read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)

            for notified_socket in read_sockets:
                if notified_socket == server_socket:
                    #new client connection
                    client_socket, client_address = server_socket.accept()
                    client_socket.setblocking(False)

                    sockets_list.append(client_socket)
                    clients[client_socket] = ClientState(client_socket, client_address)
                    print(f"[CONNECTED] Client: {client_address}")

                else:
                    client_state = clients[notified_socket]

                    if client_state.state == 'waiting_command':
                        try:
                            data = notified_socket.recv(BUFFER_SIZE).decode('utf-8').strip()
                            if not data:
                                print(f"[DISCONNECTED] Client {client_state.address}")
                                if client_state.upload_file:
                                    client_state.upload_file.close()
                                if client_state.download_file:
                                    client_state.download_file.close()
                                sockets_list.remove(notified_socket)
                                del clients[notified_socket]
                                notified_socket.close()
                                continue

                            print(f"[COMMAND] {client_state.address}: {data}")

                            if data == '/upload':
                                client_state.state = 'waiting_upload_metadata'
                            else:
                                if not process_command(client_state, data):
                                    sockets_list.remove(notified_socket)
                                    del clients[notified_socket]
                                    notified_socket.close()

                        except Exception as e:
                            print(f"[ERROR] Reading command from {client_state.address}: {e}")
                            sockets_list.remove(notified_socket)
                            del clients[notified_socket]
                            notified_socket.close()

                    elif client_state.state == 'waiting_upload_metadata':
                        try:
                            chunk = notified_socket.recv(1)
                            if not chunk:
                                print(f"[DISCONNECTED] Client {client_state.address} during metadata")
                                sockets_list.remove(notified_socket)
                                del clients[notified_socket]
                                notified_socket.close()
                                continue

                            client_state.buffer += chunk
                            if client_state.buffer.endswith(b'\n'):
                                metadata = json.loads(client_state.buffer.decode('utf-8').strip())
                                filename = metadata.get('filename', '')
                                file_size = metadata.get('size', 0)

                                if not filename:
                                    response = {'status': 'error', 'message': 'No filename provided'}
                                    notified_socket.send(json.dumps(response).encode('utf-8'))
                                    client_state.state = 'waiting_command'
                                    client_state.buffer = b''
                                else:
                                    start_upload(client_state, filename, file_size)
                                    client_state.buffer = b''

                        except Exception as e:
                            print(f"[ERROR] Reading metadata from {client_state.address}: {e}")
                            response = {'status': 'error', 'message': str(e)}
                            notified_socket.send(json.dumps(response).encode('utf-8'))
                            client_state.state = 'waiting_command'
                            client_state.buffer = b''

                    elif client_state.state == 'uploading':
                        continue_upload(client_state)

                    elif client_state.state == 'downloading':
                        try:
                            ack = notified_socket.recv(1024).decode('utf-8')
                            if 'ready' in ack.lower():
                                continue_download(client_state)
                        except:
                            pass

            for notified_socket in exception_sockets:
                if notified_socket in clients:
                    client_state = clients[notified_socket]
                    print(f"[ERROR] Exception on socket for {client_state.address}")
                    if client_state.upload_file:
                        client_state.upload_file.close()
                    if client_state.download_file:
                        client_state.download_file.close()
                sockets_list.remove(notified_socket)
                if notified_socket in clients:
                    del clients[notified_socket]
                notified_socket.close()

    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
    except Exception as e:
        print(f"[ERROR] Server error: {e}")
    finally:
        for sock in sockets_list:
            sock.close()


if __name__ == '__main__':
    start_server()
