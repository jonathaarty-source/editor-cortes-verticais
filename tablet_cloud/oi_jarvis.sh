#!/data/data/com.termux/files/usr/bin/sh
# Oi Jarvis: usa o reconhecimento de voz do proprio Android (via o app Jarvis Mao,
# em 127.0.0.1:8099) para ouvir o pedido, e manda pro PC (se estiver na rede) ou
# pelo Telegram (funciona de qualquer lugar).
cd ~/tablet_cloud

RESP=$(curl -s -m 15 -X POST http://127.0.0.1:8099/ -d '{"action":"listen","segundos":8}')
echo "$(date '+%Y-%m-%d %H:%M:%S') ouvi: $RESP" >> oi_jarvis.log

python - "$RESP" <<'PY'
import sys, json, urllib.request

resp = json.loads(sys.argv[1])
if not resp.get('ok'):
    sys.exit(0)
texto = resp.get('texto', '')
if not texto:
    sys.exit(0)

def chamar8099(payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request('http://127.0.0.1:8099/', data=data)
    return urllib.request.urlopen(req, timeout=15).read().decode()

pc_ok = False
try:
    urllib.request.urlopen('http://192.168.0.8:4747/', timeout=3)
    pc_ok = True
except Exception:
    pc_ok = False

if pc_ok:
    data = json.dumps({"texto": texto}).encode()
    req = urllib.request.Request('http://192.168.0.8:4747/pedido', data=data, headers={'Content-Type': 'application/json; charset=utf-8'})
    urllib.request.urlopen(req, timeout=10)
    print('mandado pro PC:', texto)
else:
    r = chamar8099({"action": "telegram_send", "bot": "Jarvis_boraic_bot", "text": texto})
    print('mandado pro Telegram (PC fora do ar):', texto, r)
PY
