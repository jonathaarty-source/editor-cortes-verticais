#!/data/data/com.termux/files/usr/bin/sh
# Atualiza e reinicia o painel e o vigia de notificação, sempre em segundo plano de verdade.
cd ~/tablet_cloud
curl -sL -o dashboard.html https://raw.githubusercontent.com/jonathaarty-source/editor-cortes-verticais/main/tablet_cloud/dashboard.html
curl -sL -o server.py https://raw.githubusercontent.com/jonathaarty-source/editor-cortes-verticais/main/tablet_cloud/server.py
curl -sL -o notif_watch.sh https://raw.githubusercontent.com/jonathaarty-source/editor-cortes-verticais/main/tablet_cloud/notif_watch.sh
chmod +x notif_watch.sh
pkill -f server.py
pkill -f notif_watch.sh
sleep 1
nohup python server.py > server.log 2>&1 &
nohup sh notif_watch.sh > notif.log 2>&1 &
disown -a
echo "reiniciado"
