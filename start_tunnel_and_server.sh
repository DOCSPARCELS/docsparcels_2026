#!/bin/bash

echo "🚀 AVVIO AUTOMATICO TUNNEL SSH + SERVER"
echo "======================================"

# Termina processi esistenti
echo "🔄 Terminando processi esistenti..."
lsof -ti:3307 | xargs kill -9 2>/dev/null || echo "Porta 3307 libera"
lsof -ti:5003 | xargs kill -9 2>/dev/null || echo "Porta 5003 libera"

# Avvia tunnel SSH in background
echo "🔗 Avviando tunnel SSH verso OVH..."
ssh -f -N -L 3307:127.0.0.1:3306 luca@91.134.91.229

# Aspetta che il tunnel sia attivo
sleep 2

# Verifica tunnel
if lsof -i:3307 > /dev/null; then
    echo "✅ Tunnel SSH attivo sulla porta 3307"
else
    echo "❌ Errore: Tunnel SSH non attivo"
    exit 1
fi

# Verifica connessione database
echo "🔍 Verificando connessione database..."
cd "/Users/luca/Library/CloudStorage/GoogleDrive-aveaniluca@gmail.com/Il mio Drive/SCAMBIO/programma_2026"
python3 -c "
from db_connector import cursor
try:
    with cursor() as (conn, cur):
        cur.execute('SELECT COUNT(*) FROM spedizioni;')
        count = cur.fetchone()[0]
        print(f'✅ Database OVH connesso: {count} spedizioni')
except Exception as e:
    print(f'❌ Errore database: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo "🚀 Avviando server Flask..."
    python3 api_server.py
else
    echo "❌ Errore nella connessione al database"
    exit 1
fi