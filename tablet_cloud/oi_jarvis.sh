#!/data/data/com.termux/files/usr/bin/sh
# Oi Jarvis: grava a voz, transcreve local (whisper) e manda pro Jarvis Mao
# (o app de acessibilidade, que toca a tela sozinho) abrir o Telegram e enviar.
# Uso: sh oi_jarvis.sh   (grava 6s; ajuste o tempo se precisar)
cd ~/tablet_cloud
AUDIO=/data/data/com.termux/files/home/tablet_cloud/oi_jarvis.wav

termux-microphone-record -f "$AUDIO" -l 6 -e wav
sleep 7
termux-microphone-record -q > /dev/null 2>&1

python transcrever_pedido.py "$AUDIO" > pedido_texto.txt
TEXTO=$(cat pedido_texto.txt)
echo "$(date '+%Y-%m-%d %H:%M:%S') ouvi: $TEXTO" >> oi_jarvis.log

if [ -z "$TEXTO" ]; then
  exit 0
fi

# 1) tenta o PC do escritorio primeiro
PC_OK=$(curl -s -m 3 -o /dev/null -w "%{http_code}" http://192.168.0.8:4747/ 2>/dev/null)
if [ "$PC_OK" = "200" ]; then
  curl -s -m 10 -X POST http://192.168.0.8:4747/pedido -H "Content-Type: application/json; charset=utf-8" --data-binary @- <<JSON >> oi_jarvis.log
{"texto": "$TEXTO"}
JSON
  echo "$(date '+%Y-%m-%d %H:%M:%S') mandado pro PC" >> oi_jarvis.log
  exit 0
fi

# 2) PC fora do ar: manda pelo Telegram (funciona de qualquer lugar), via o Jarvis Mao
python - "$TEXTO" <<'PY' >> oi_jarvis.log
import sys, json, urllib.request
texto = sys.argv[1]
data = json.dumps({"action": "telegram_send", "bot": "Jarvis_boraic_bot", "text": texto}).encode()
req = urllib.request.Request('http://127.0.0.1:8099/', data=data)
print(urllib.request.urlopen(req, timeout=15).read().decode())
PY
echo "$(date '+%Y-%m-%d %H:%M:%S') tentativa de mandar pro Telegram (PC fora do ar)" >> oi_jarvis.log
