#!/data/data/com.termux/files/usr/bin/sh
# Roda sozinho a cada boot (Termux:Boot). Mantém o painel da nuvem do Jarvis sempre no ar.
termux-wake-lock
cd ~/tablet_cloud
curl -sL -o server.py https://raw.githubusercontent.com/jonathaarty-source/editor-cortes-verticais/main/tablet_cloud/server.py
curl -sL -o dashboard.html https://raw.githubusercontent.com/jonathaarty-source/editor-cortes-verticais/main/tablet_cloud/dashboard.html
nohup python server.py > server.log 2>&1 &
nohup sh notif_watch.sh > notif.log 2>&1 &
# A tela inicial já é o painel (Webview Kiosk virou o launcher padrão), não precisa abrir nada.
