import socket
import threading
import os
import json

HOST = '127.0.0.1'
PORT = 9999
BUFFER_SIZE = 2048
SERVER_FILES_DIR = './server_files'

os.makedirs(SERVER_FILES_DIR, exist_ok=True)

def handle_list(client_socket, addr):
    try:
        files = [f for f in os.listdir(SERVER_FILES_DIR) if os.path.isfile(os.path.join(SERVER_FILES_DIR, f))]
        response = {'status': 'success', 'files': files, 'count': len(files)}
        client_socket.send(json.dumps(response).encode('utf-8'))
        print(f"[LIST] Sent list to {addr}")
    except Exception as e:
        client_socket.send(json.dumps({'status': 'error','message': str(e)}).encode('utf-8'))

def handle_upload(client_socket, addr):
    try:
        metadata_bytes = b''
        while True:
            chunk = client_socket.recv(1)
            if not chunk:
                break
            metadata_bytes += chunk
            if metadata_bytes.endswith(b'\n'):
                break
        metadata = json.loads(metadata_bytes.decode('utf-8').strip())
        filename = os.path.basename(metadata['filename'])
        size = metadata['size']

        print(f"[UPLOAD] Starting upload: {filename} from {addr}")
        client_socket.send(json.dumps({'status':'ready','message':'Ready to receive file'}).encode('utf-8'))

        received = 0
        with open(os.path.join(SERVER_FILES_DIR, filename), 'wb') as f:
            while received < size:
                chunk_size = min(BUFFER_SIZE, size - received)
                chunk = client_socket.recv(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                received += len(chunk)

        client_socket.send(json.dumps({'status':'success','message':f'File {filename} uploaded','filename':filename,'size':received}).encode('utf-8'))
        print(f"[UPLOAD] Completed: {filename} from {addr}")

    except Exception as e:
        client_socket.send(json.dumps({'status':'error','message':str(e)}).encode('utf-8'))

def handle_download(client_socket, addr, filename):
    try:
        filename = os.path.basename(filename)
        path = os.path.join(SERVER_FILES_DIR, filename)
        if not os.path.exists(path):
            client_socket.send(json.dumps({'status':'error','message':'File not found'}).encode('utf-8'))
            return

        size = os.path.getsize(path)
        client_socket.send(json.dumps({'status':'found','filename':filename,'size':size}).encode('utf-8'))
        ack = client_socket.recv(1024).decode('utf-8')
        if 'ready' not in ack.lower():
            return

        print(f"[DOWNLOAD] Starting download: {filename} to {addr}")
        sent = 0
        with open(path,'rb') as f:
            while sent < size:
                chunk = f.read(BUFFER_SIZE)
                if not chunk:
                    break
                client_socket.sendall(chunk)
                sent += len(chunk)
        print(f"[DOWNLOAD] Completed: {filename} to {addr}")

    except Exception as e:
        client_socket.send(json.dumps({'status':'error','message':str(e)}).encode('utf-8'))

def handle_client(client_socket, addr):
    print(f"[CONNECTED] {addr}")
    try:
        while True:
            data = client_socket.recv(BUFFER_SIZE).decode('utf-8').strip()
            if not data:
                break
            print(f"[COMMAND] {addr}: {data}")

            parts = data.split()
            cmd = parts[0].lower()

            if cmd == '/list':
                handle_list(client_socket, addr)
            elif cmd == '/upload':
                handle_upload(client_socket, addr)
            elif cmd == '/download':
                if len(parts) < 2:
                    client_socket.send(json.dumps({'status':'error','message':'Usage: /download <filename>'}).encode('utf-8'))
                else:
                    handle_download(client_socket, addr, parts[1])
            elif cmd == '/quit':
                client_socket.send(json.dumps({'status':'success','message':'Bye!'}).encode('utf-8'))
                break
            else:
                client_socket.send(json.dumps({'status':'error','message':'Unknown command'}).encode('utf-8'))
    finally:
        client_socket.close()
        print(f"[DISCONNECTED] {addr}")

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print(f"[SERVER] Listening on {HOST}:{PORT}")

    try:
        while True:
            client_socket, addr = server_socket.accept()
            threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
    finally:
        server_socket.close()

if __name__ == '__main__':
    start_server()