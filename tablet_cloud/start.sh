#!/data/data/com.termux/files/usr/bin/sh
# Roda sozinho a cada boot (Termux:Boot). Mantém o painel da nuvem do Jarvis sempre no ar.
termux-wake-lock
cd ~/tablet_cloud
curl -sL -o server.py https://raw.githubusercontent.com/jonathaarty-source/editor-cortes-verticais/main/tablet_cloud/server.py
curl -sL -o dashboard.html https://raw.githubusercontent.com/jonathaarty-source/editor-cortes-verticais/main/tablet_cloud/dashboard.html
nohup python server.py > server.log 2>&1 &
sleep 3
am start -a android.intent.action.VIEW -d "http://127.0.0.1:8088/" -n com.android.chrome/com.google.android.apps.chrome.Main
