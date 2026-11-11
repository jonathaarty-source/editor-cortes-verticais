#!/data/data/com.termux/files/usr/bin/sh
# Oi Jarvis: usa a mesma logica do app Jarvis Mao (127.0.0.1:8099) que a escuta
# continua ("oi Jarvis" sem apertar nada) ja usa. "listen_and_send" ouve, decide
# sozinho se e pedido de camera (liga a gravacao e fala) ou pedido comum (manda
# pro Telegram), e fala a resposta em voz. Antes esse script reimplementava essa
# decisao em Python e nunca sabia de camera nem falava nada de volta (11/11).
cd ~/tablet_cloud

RESP=$(curl -s -m 60 -X POST http://127.0.0.1:8099/ -d '{"action":"listen_and_send","segundos":8,"bot":"Jarvis_boraic_bot"}')
echo "$(date '+%Y-%m-%d %H:%M:%S') resultado: $RESP" >> oi_jarvis.log
