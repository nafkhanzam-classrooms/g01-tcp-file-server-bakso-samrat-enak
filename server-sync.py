import socket
import os
import json
from pathlib import Path

HOST = '127.0.0.1'
PORT = 5000
BUFFER_SIZE = 2048 #2KB
SERVER_FILES_DIR = './server_files'

# /list
def get_file_list():
    try:
        files = os.listdir(SERVER_FILES_DIR)
        files = [f for f in files if os.path.isfile(os.path.join(SERVER_FILES_DIR, f))]
        return files
    except Exception as e:
        return []


def handle_list_command(client_socket):
    try:
        files = get_file_list()
        response = {
            'status': 'success',
            'command': 'list',
            'files': files,
            'count': len(files)
        }
        client_socket.send(json.dumps(response).encode('utf-8'))
        print(f"[LIST] Sent file list with {len(files)} files")
    except Exception as e:
        response = {'status': 'error', 'message': str(e)}
        client_socket.send(json.dumps(response).encode('utf-8'))
        print(f"[ERROR] List command failed: {e}")

# /upload
def handle_upload_command(client_socket):
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
        filename = metadata.get('filename', '')
        file_size = metadata.get('size', 0)
        
        filename = os.path.basename(filename)
        file_path = os.path.join(SERVER_FILES_DIR, filename)
        
        response = {'status': 'ready', 'message': 'Ready to receive file'}
        client_socket.send(json.dumps(response).encode('utf-8'))
        
        received = 0
        with open(file_path, 'wb') as f:
            while received < file_size:
                chunk_size = min(BUFFER_SIZE, file_size - received)
                chunk = client_socket.recv(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                received += len(chunk)
        
        response = {
            'status': 'success',
            'message': f'File {filename} uploaded successfully',
            'filename': filename,
            'size': received
        }
        client_socket.send(json.dumps(response).encode('utf-8'))
        print(f"[UPLOAD] Received file: {filename} ({received} bytes)")
        
    except Exception as e:
        response = {'status': 'error', 'message': str(e)}
        client_socket.send(json.dumps(response).encode('utf-8'))
        print(f"[ERROR] Upload command failed: {e}")

# /download
def handle_download_command(client_socket, filename):
    """Handle /download command - send file to client"""
    try:
        filename = os.path.basename(filename)
        file_path = os.path.join(SERVER_FILES_DIR, filename)
        
        #file exist?
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            response = {'status': 'error', 'message': f'File {filename} not found'}
            client_socket.send(json.dumps(response).encode('utf-8'))
            print(f"[DOWNLOAD] File not found: {filename}")
            return
        
        #file size
        file_size = os.path.getsize(file_path)
        
        # Send metadata
        metadata = {
            'status': 'found',
            'filename': filename,
            'size': file_size
        }
        client_socket.send(json.dumps(metadata).encode('utf-8'))
        
        ack = client_socket.recv(1024).decode('utf-8')
        if 'ready' not in ack.lower():
            print(f"[DOWNLOAD] Client not ready for {filename}")
            return
        
        sent = 0
        with open(file_path, 'rb') as f:
            while sent < file_size:
                chunk = f.read(BUFFER_SIZE)
                if not chunk:
                    break
                client_socket.sendall(chunk)
                sent += len(chunk)
        
        print(f"[DOWNLOAD] Sent file: {filename} ({sent} bytes)")
        
    except Exception as e:
        response = {'status': 'error', 'message': str(e)}
        client_socket.send(json.dumps(response).encode('utf-8'))
        print(f"[ERROR] Download command failed: {e}")


def handle_client(client_socket, client_address):
    """Handle a single client connection"""
    print(f"\n[CONNECTED] Client: {client_address}")
    
    try:
        while True:
            data = client_socket.recv(BUFFER_SIZE).decode('utf-8').strip()
            
            if not data:
                print(f"[DISCONNECTED] Client {client_address}")
                break
            
            print(f"[COMMAND] Received: {data}")
            
            parts = data.split()
            command = parts[0].lower() if parts else ''
            
            if command == '/list':
                handle_list_command(client_socket)
            
            elif command == '/upload':
                handle_upload_command(client_socket)
            
            elif command == '/download':
                if len(parts) < 2:
                    response = {'status': 'error', 'message': 'Usage: /download <filename>'}
                    client_socket.send(json.dumps(response).encode('utf-8'))
                else:
                    filename = parts[1]
                    handle_download_command(client_socket, filename)
            
            else:
                response = {
                    'status': 'error',
                    'message': 'Unknown command. Available: /list, /upload, /download <filename>, /quit'
                }
                client_socket.send(json.dumps(response).encode('utf-8'))
    
    except Exception as e:
        print(f"[ERROR] While handling client {client_address}: {e}")
    
    finally:
        client_socket.close()


def start_server():
    """Start the TCP file server"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(1)
        print(f"[SERVER] Server is ready...")
        
        while True:
            client_socket, client_address = server_socket.accept()
            
            handle_client(client_socket, client_address)
    
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
    except Exception as e:
        print(f"[ERROR] Server error: {e}")
    finally:
        server_socket.close()


if __name__ == '__main__':
    start_server()
