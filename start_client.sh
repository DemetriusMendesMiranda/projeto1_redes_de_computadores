#!/bin/bash
# ==========================================
# Script: start_client.sh
# Projeto: Chat Cliente-Servidor (Protocolo Próprio)
# Função: Inicia um cliente com nome e IP do servidor
# Uso: ./start_client.sh <IP_SERVIDOR> <NOME_USUARIO>
# ==========================================

# Verifica parâmetros
if [ "$#" -ne 2 ]; then
  echo "Uso: $0 <IP_SERVIDOR> <NOME_USUARIO>"
  echo "Exemplo: $0 192.168.0.10 Alice"
  exit 1
fi

SERVER_IP=$1
NAME=$2
PORT=50000

echo "=========================================="
echo " Iniciando Cliente do Chat"
echo " Servidor: $SERVER_IP"
echo " Porta: $PORT"
echo " Nome: $NAME"
echo "=========================================="

# Executa o cliente com os parâmetros informados
python3 client.py --server "$SERVER_IP" --port "$PORT" --name "$NAME"
