import socket
import json
import os
import sys

HOST = '127.0.0.1'
PORT = 5000
BUFFER_SIZE = 2048


def send_command(sock, command):
    sock.send(command.encode('utf-8'))


def receive_response(sock):
    response = b''
    while True:
        chunk = sock.recv(BUFFER_SIZE)
        if not chunk:
            break
        response += chunk
        try:
            return json.loads(response.decode('utf-8'))
        except:
            continue
    return None


def cmd_list(sock):
    send_command(sock, '/list')
    response = receive_response(sock)
    
    if response.get('status') == 'success':
        files = response.get('files', [])
        print(f"\n[FILES] Found {response.get('count')} files on server:")
        if files:
            for i, f in enumerate(files, 1):
                print(f"  {i}. {f}")
        else:
            print("  (empty)")
    else:
        print(f"[ERROR] {response.get('message')}")


def cmd_upload(sock):
    filename = input("Enter filename to upload: ").strip()
    
    if not os.path.exists(filename):
        print(f"[ERROR] File not found: {filename}")
        return
    
    file_size = os.path.getsize(filename)
    basename = os.path.basename(filename)
    
    metadata = {
        'filename': basename,
        'size': file_size
    }
    send_command(sock, '/upload\n')
    
    import time
    time.sleep(0.1)
    
    sock.send(json.dumps(metadata).encode('utf-8') + b'\n')
    
    response = receive_response(sock)
    print(f"[DEBUG] Server response: {response}")
    
    if response.get('status') == 'ready':
        print(f"[UPLOADING] Sending {basename} ({file_size} bytes)...")
        with open(filename, 'rb') as f:
            sent = 0
            while sent < file_size:
                chunk = f.read(BUFFER_SIZE)
                if not chunk:
                    break
                sock.sendall(chunk)
                sent += len(chunk)
                print(f"\r[PROGRESS] {sent}/{file_size} bytes", end='', flush=True)
        
        response = receive_response(sock)
        print()
        if response.get('status') == 'success':
            print(f"[SUCCESS] {response.get('message')}")
        else:
            print(f"[ERROR] {response.get('message')}")
    else:
        print(f"[ERROR] {response.get('message')}")


def cmd_download(sock):
    """Download a file from server"""
    filename = input("Enter filename to download: ").strip()
    
    if not filename:
        print("[ERROR] No filename specified")
        return
    
    send_command(sock, f'/download {filename}')

    response = receive_response(sock)
    print(f"[DEBUG] Server response: {response}")
    
    if response.get('status') != 'found':
        print(f"[ERROR] {response.get('message')}")
        return
    
    file_size = response.get('size', 0)
    remote_filename = response.get('filename', filename)
    
    send_command(sock, 'ready')
    
    print(f"[DOWNLOADING] {remote_filename} ({file_size} bytes)...")
    received = 0
    with open(remote_filename, 'wb') as f:
        while received < file_size:
            chunk_size = min(BUFFER_SIZE, file_size - received)
            chunk = sock.recv(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            received += len(chunk)
            print(f"\r[PROGRESS] {received}/{file_size} bytes", end='', flush=True)
    
    print()
    if received == file_size:
        print(f"[SUCCESS] File downloaded: {remote_filename}")
    else:
        print(f"[ERROR] Incomplete download ({received}/{file_size} bytes)")

def main():
    """Main client loop"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"[CONNECTING] to {HOST}:{PORT}...")
        sock.connect((HOST, PORT))
        print("[CONNECTED] Successfully connected to server\n")
        
        while True:
            try:
                command = input("\nEnter command: ").strip().lower()
                
                if not command:
                    continue
                
                if command == '/list':
                    cmd_list(sock)
                
                elif command == '/upload':
                    cmd_upload(sock)
                
                elif command == '/download':
                    cmd_download(sock)
                
                elif command == '/quit' or command == '/exit':
                    send_command(sock, '/quit')
                    response = receive_response(sock)
                    print(f"[SERVER] {response.get('message')}")
                    break
                
                else:
                    print("[ERROR] Unknown command. Try: /list, /upload, /download, /quit")
            
            except KeyboardInterrupt:
                print("\n[INTERRUPTED] Closing connection...")
                send_command(sock, '/quit')
                break
            except Exception as e:
                print(f"[ERROR] {e}")
    
    except ConnectionRefusedError:
        print(f"[ERROR] Could not connect to server at {HOST}:{PORT}")
        print("Make sure the server is running first!")
    except Exception as e:
        print(f"[ERROR] Connection error: {e}")
    finally:
        sock.close()
        print("[DISCONNECTED]")
        

if __name__ == '__main__':
    main()
