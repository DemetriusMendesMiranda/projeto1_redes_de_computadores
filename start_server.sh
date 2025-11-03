#!/bin/bash
# ==========================================
# Script: start_server.sh
# Projeto: Chat Cliente-Servidor (Protocolo Próprio)
# Função: Inicia o servidor Python em modo TCP
# ==========================================

# Porta padrão do servidor
PORT=50000

echo "=========================================="
echo " Iniciando Servidor do Chat"
echo " Porta: $PORT"
echo "=========================================="

# Executa o servidor
python3 server.py --host 0.0.0.0 --port $PORT
