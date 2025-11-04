#!/usr/bin/env python3
"""
client.py
Cliente do chat.
Uso: python3 client.py --server 192.168.0.10 --port 50000 --name Alice
"""

import socket
import struct
import threading
import argparse
import sys
import os

VERSION = 1
TYPE_CONNECT = 1
TYPE_MSG = 2
TYPE_LIST = 3
TYPE_FILE = 4
TYPE_ACK = 5
TYPE_DISCONNECT = 6

HEADER_FMT = '!BBHI'
HEADER_SIZE = struct.calcsize(HEADER_FMT)

def build_header(version, type_, seq, length):
    return struct.pack(HEADER_FMT, version, type_, seq, length)

def parse_header(data):
    return struct.unpack(HEADER_FMT, data[:HEADER_SIZE])

def recv_all(sock, n):
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            return None
        data += chunk
    return data

def recv_loop(sock):
    try:
        while True:
            hdr = recv_all(sock, HEADER_SIZE)
            if hdr is None:
                print("[*] Conexão fechada pelo servidor")
                break
            version, type_, seq, length = parse_header(hdr)
            payload = b''
            if length > 0:
                payload = recv_all(sock, length)
                if payload is None:
                    print("[*] Conexão fechada durante leitura de payload")
                    break
            # Tratamento simples
            if type_ == TYPE_MSG:
                try:
                    text = payload.decode('utf-8', errors='ignore')
                    print(f"[MSG] {text}")
                except:
                    print("[MSG] (binário)")
            elif type_ == TYPE_LIST:
                try:
                    names = payload.decode('utf-8', errors='ignore')
                    print(f"[USERS] {names}")
                except:
                    print("[USERS] (erro decoding)")
            elif type_ == TYPE_ACK:
                try:
                    msg = payload.decode('utf-8', errors='ignore')
                    print(f"[ACK seq={seq}] {msg}")
                except:
                    print(f"[ACK seq={seq}]")
            elif type_ == TYPE_FILE:
                # Server could also send files in this protocol; handle if necessary
                fname = f"received_from_server_{seq}.bin"
                with open(fname, 'ab') as f:
                    f.write(payload)
                print(f"[FILE] recebido e salvo em {fname}")
            else:
                print(f"[INFO] Tipo {type_} seq {seq} len {length}")
    except Exception as e:
        print("Erro no loop de recepção:", e)
    finally:
        try:
            sock.close()
        except:
            pass

def send_connect(sock, name, seq=1):
    payload = name.encode('utf-8')
    hdr = build_header(VERSION, TYPE_CONNECT, seq, len(payload))
    sock.sendall(hdr + payload)

def send_msg(sock, text, seq=1):
    payload = text.encode('utf-8')
    hdr = build_header(VERSION, TYPE_MSG, seq, len(payload))
    sock.sendall(hdr + payload)

def send_list(sock, seq=1):
    hdr = build_header(VERSION, TYPE_LIST, seq, 0)
    sock.sendall(hdr)

def send_file(sock, filepath, seq_start=1, chunk_size=4096):
    if not os.path.isfile(filepath):
        print("Arquivo não encontrado:", filepath)
        return
    seq = seq_start
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hdr = build_header(VERSION, TYPE_FILE, seq, len(chunk))
            sock.sendall(hdr + chunk)
            seq = (seq + 1) % 65536

def send_disconnect(sock, seq=1):
    hdr = build_header(VERSION, TYPE_DISCONNECT, seq, 0)
    sock.sendall(hdr)

def main():
    parser = argparse.ArgumentParser(description="Cliente Chat - Protocolo Próprio")
    parser.add_argument('--server', required=True, help='IP do servidor')
    parser.add_argument('--port', type=int, default=50000, help='Porta do servidor')
    parser.add_argument('--name', required=True, help='Nome do usuário')
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((args.server, args.port))

    # start recv thread
    t = threading.Thread(target=recv_loop, args=(sock,), daemon=True)
    t.start()

    seq = 1
    send_connect(sock, args.name, seq); seq = (seq + 1) % 65536

    try:
        while True:
            line = input()
            if not line:
                continue
            if line.startswith('/quit') or line.startswith('/exit'):
                send_disconnect(sock, seq); seq = (seq + 1) % 65536
                print("Desconectando...")
                break
            elif line.startswith('/who') or line.startswith('/list'):
                send_list(sock, seq); seq = (seq + 1) % 65536
            elif line.startswith('/sendfile '):
                _, path = line.split(' ', 1)
                send_file(sock, path.strip(), seq)
        
                seq = (seq + 1) % 65536
            else:
                send_msg(sock, line, seq); seq = (seq + 1) % 65536
    except KeyboardInterrupt:
        send_disconnect(sock, seq)
    finally:
        try:
            sock.close()
        except:
            pass
        print("Cliente encerrado.")

if __name__ == '__main__':
    main()
