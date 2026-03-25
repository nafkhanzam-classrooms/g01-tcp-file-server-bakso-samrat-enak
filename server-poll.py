import socket
import os
import json
import select
from pathlib import Path

HOST = '127.0.0.1'
PORT = 5000
BUFFER_SIZE = 2048
SERVER_FILES_DIR = './server_files'

Path(SERVER_FILES_DIR).mkdir(exist_ok=True)

class ClientState:
    def __init__(self, sock, address):
        self.socket = sock
        self.address = address
        self.state = 'waiting_command'
        self.buffer = b''
        self.filename = None
        self.file_size = 0
        self.bytes_processed = 0
        self.file_ptr = None

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.setblocking(False)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)

    poller = select.poll()
    poller.register(server_socket, select.POLLIN)

    clients = {}
    fd_to_socket = {server_socket.fileno(): server_socket}

    print(f"[SERVER] Listening on {HOST}:{PORT}")

    try:
        while True:
            events = poller.poll(1000)
            for fd, flag in events:
                if fd == server_socket.fileno():
                    client_sock, addr = server_socket.accept()
                    client_sock.setblocking(False)
                    print(f"[CONNECTED] {addr}")
                    
                    poller.register(client_sock, select.POLLIN)
                    fd_to_socket[client_sock.fileno()] = client_sock
                    clients[client_sock.fileno()] = ClientState(client_sock, addr)

                elif flag & select.POLLIN:
                    handle_client_logic(fd, clients, poller, fd_to_socket)

                elif flag & (select.POLLERR | select.POLLHUP):
                    cleanup(fd, clients, poller, fd_to_socket)

    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
    finally:
        server_socket.close()

def handle_client_logic(fd, clients, poller, fd_to_socket):
    state = clients[fd]
    sock = state.socket
    addr = state.address

    try:
        if state.state == 'waiting_command':
            data = sock.recv(BUFFER_SIZE).decode('utf-8').strip()
            if not data:
                cleanup(fd, clients, poller, fd_to_socket)
                return

            print(f"[COMMAND] {addr}: {data}")
            parts = data.split()
            cmd = parts[0].lower()

            if cmd == '/list':
                files = [f for f in os.listdir(SERVER_FILES_DIR) if os.path.isfile(os.path.join(SERVER_FILES_DIR, f))]
                sock.send(json.dumps({'status': 'success', 'files': files, 'count': len(files)}).encode('utf-8'))
                print(f"[LIST] Sent list to {addr}")

            elif cmd == '/upload':
                state.state = 'waiting_upload_metadata'

            elif cmd == '/download':
                if len(parts) < 2:
                    sock.send(json.dumps({'status':'error','message':'Usage: /download <filename>'}).encode('utf-8'))
                else:
                    filename = os.path.basename(parts[1])
                    path = os.path.join(SERVER_FILES_DIR, filename)
                    if os.path.exists(path):
                        state.file_size = os.path.getsize(path)
                        state.filename = filename
                        sock.send(json.dumps({'status':'found','filename':filename,'size':state.file_size}).encode('utf-8'))
                        state.state = 'waiting_download_ready'
                    else:
                        sock.send(json.dumps({'status':'error','message':'File not found'}).encode('utf-8'))

            elif cmd == '/quit':
                sock.send(json.dumps({'status':'success','message':'Bye!'}).encode('utf-8'))
                cleanup(fd, clients, poller, fd_to_socket)

        elif state.state == 'waiting_upload_metadata':
            chunk = sock.recv(BUFFER_SIZE)
            state.buffer += chunk
            if b'\n' in state.buffer:
                line, rest = state.buffer.split(b'\n', 1)
                metadata = json.loads(line.decode('utf-8').strip())
                state.filename = os.path.basename(metadata['filename'])
                state.file_size = metadata['size']
                state.bytes_processed = 0
                state.file_ptr = open(os.path.join(SERVER_FILES_DIR, state.filename), 'wb')
                
                print(f"[UPLOAD] Starting upload: {state.filename} from {addr}")
                sock.send(json.dumps({'status':'ready','message':'Ready to receive file'}).encode('utf-8'))
                state.state = 'uploading'
                state.buffer = rest 

        elif state.state == 'uploading':
            chunk = sock.recv(BUFFER_SIZE)
            if chunk:
                state.file_ptr.write(chunk)
                state.bytes_processed += len(chunk)
                if state.bytes_processed >= state.file_size:
                    state.file_ptr.close()
                    sock.send(json.dumps({'status':'success','message':f'File {state.filename} uploaded','filename':state.filename,'size':state.bytes_processed}).encode('utf-8'))
                    print(f"[UPLOAD] Completed: {state.filename} from {addr}")
                    state.state = 'waiting_command'

        elif state.state == 'waiting_download_ready':
            ack = sock.recv(1024).decode('utf-8')
            if 'ready' in ack.lower():
                print(f"[DOWNLOAD] Starting download: {state.filename} to {addr}")
                path = os.path.join(SERVER_FILES_DIR, state.filename)
                with open(path, 'rb') as f:
                    sock.sendall(f.read())
                print(f"[DOWNLOAD] Completed: {state.filename} to {addr}")
                state.state = 'waiting_command'

    except Exception as e:
        print(f"[ERROR] {addr}: {e}")
        cleanup(fd, clients, poller, fd_to_socket)

def cleanup(fd, clients, poller, fd_to_socket):
    if fd in clients:
        state = clients[fd]
        if state.file_ptr: state.file_ptr.close()
        print(f"[DISCONNECTED] {state.address}")
        del clients[fd]
    if fd in fd_to_socket:
        sock = fd_to_socket[fd]
        poller.unregister(fd)
        sock.close()
        del fd_to_socket[fd]

if __name__ == '__main__':
    start_server()