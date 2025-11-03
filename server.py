#!/usr/bin/env python3
"""
server.py
Servidor do chat com protocolo custom (TCP).
Uso: python3 server.py --host 0.0.0.0 --port 50000
"""

import socket
import threading
import struct
import argparse
import time
import os
import logging

# Protocolo constants
VERSION = 1
TYPE_CONNECT = 1
TYPE_MSG = 2
TYPE_LIST = 3
TYPE_FILE = 4
TYPE_ACK = 5
TYPE_DISCONNECT = 6

HEADER_FMT = '!BBHI'  # version:uint8, type:uint8, seq:uint16, length:uint32
HEADER_SIZE = struct.calcsize(HEADER_FMT)

# Globals
clients_lock = threading.Lock()
clients = {}  # socket -> {'name': str, 'addr': (ip,port)}

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def build_header(version, type_, seq, length):
    return struct.pack(HEADER_FMT, version, type_, seq, length)

def parse_header(data):
    if len(data) < HEADER_SIZE:
        raise ValueError("Header incompleto")
    version, type_, seq, length = struct.unpack(HEADER_FMT, data[:HEADER_SIZE])
    return version, type_, seq, length

def recv_all(sock, n):
    """Ler exatamente n bytes do socket."""
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            # Conexão fechada
            return None
        data += chunk
    return data

def send_ack(sock, seq, message=b'OK'):
    hdr = build_header(VERSION, TYPE_ACK, seq, len(message))
    try:
        sock.sendall(hdr + message)
    except Exception as e:
        logging.warning(f"Erro ao enviar ACK: {e}")

def broadcast(sender_sock, header, payload):
    """Enviar payload para todos os clientes exceto o sender."""
    with clients_lock:
        recipients = [s for s in clients.keys() if s != sender_sock]
    for s in recipients:
        try:
            s.sendall(header + payload)
        except Exception as e:
            logging.warning(f"Erro ao enviar para {clients.get(s)}: {e}")

def handle_client(conn, addr):
    logging.info(f"Conexão aceita de {addr}")
    name = None
    try:
        while True:
            hdr_bytes = recv_all(conn, HEADER_SIZE)
            if hdr_bytes is None:
                logging.info(f"Conexão perdida de {addr}")
                break
            version, type_, seq, length = parse_header(hdr_bytes)
            payload = b''
            if length > 0:
                payload = recv_all(conn, length)
                if payload is None:
                    logging.info(f"Conexão perdida durante payload de {addr}")
                    break

            logging.info(f"Recv from {addr} — ver: v{version} type:{type_} seq:{seq} len:{length}")

            if type_ == TYPE_CONNECT:
                try:
                    name = payload.decode('utf-8', errors='ignore')
                except:
                    name = str(addr)
                with clients_lock:
                    clients[conn] = {'name': name, 'addr': addr}
                logging.info(f"Usuário conectado: {name} @ {addr}")
                send_ack(conn, seq, b'CONNECTED')
            elif type_ == TYPE_MSG:
                # broadcast message to others
                logging.info(f"MSG from {name or addr}: {payload[:50]}")
                # re-use header: version,type,seq,length
                header = build_header(version, TYPE_MSG, seq, length)
                broadcast(conn, header, payload)
                send_ack(conn, seq, b'MSG_RECEIVED')
            elif type_ == TYPE_LIST:
                # respond with semicolon-separated names
                with clients_lock:
                    names = [info['name'] for info in clients.values() if 'name' in info and info['name']]
                list_payload = ';'.join(names).encode('utf-8')
                resp_hdr = build_header(VERSION, TYPE_LIST, seq, len(list_payload))
                conn.sendall(resp_hdr + list_payload)
            elif type_ == TYPE_FILE:
                # payload contains file bytes; save it
                # to make it simple: save as file_{timestamp}_{seq}.bin
                fname = f"recv_file_{int(time.time())}_{seq}.bin"
                with open(fname, 'ab') as f:
                    f.write(payload)
                logging.info(f"Arquivo salvo: {fname} ({len(payload)} bytes)")
                send_ack(conn, seq, f'FILE_SAVED:{fname}'.encode('utf-8'))
            elif type_ == TYPE_DISCONNECT:
                logging.info(f"DISCONNECT from {name or addr}")
                send_ack(conn, seq, b'BYE')
                break
            elif type_ == TYPE_ACK:
                # server typically doesn't need to handle ACKs from clients here
                logging.debug(f"ACK recebido: {payload}")
            else:
                logging.warning(f"Tipo desconhecido recebido: {type_}")
    except Exception as e:
        logging.exception(f"Erro no handler do cliente {addr}: {e}")
    finally:
        with clients_lock:
            if conn in clients:
                logging.info(f"Removendo cliente {clients[conn]}")
                del clients[conn]
        try:
            conn.close()
        except:
            pass
        logging.info(f"Conexão com {addr} encerrada")

def accept_loop(server_sock):
    while True:
        conn, addr = server_sock.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        t.start()

def main():
    parser = argparse.ArgumentParser(description="Servidor Chat - Protocolo Próprio")
    parser.add_argument('--host', default='0.0.0.0', help='IP para bind')
    parser.add_argument('--port', type=int, default=50000, help='Porta TCP')
    args = parser.parse_args()

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((args.host, args.port))
    server_sock.listen(100)
    logging.info(f"Servidor rodando em {args.host}:{args.port}")
    try:
        accept_loop(server_sock)
    except KeyboardInterrupt:
        logging.info("Servidor interrompido por teclado")
    finally:
        server_sock.close()

if __name__ == '__main__':
    main()
