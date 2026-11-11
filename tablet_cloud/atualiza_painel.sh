#!/data/data/com.termux/files/usr/bin/sh
cd ~/tablet_cloud
curl -sL -o oi_jarvis.sh https://raw.githubusercontent.com/jonathaarty-source/editor-cortes-verticais/main/tablet_cloud/oi_jarvis.sh
curl -sL -o dashboard.html https://raw.githubusercontent.com/jonathaarty-source/editor-cortes-verticais/main/tablet_cloud/dashboard.html
chmod +x oi_jarvis.sh
echo "$(date '+%Y-%m-%d %H:%M:%S') painel atualizado" >> inspetor.log
