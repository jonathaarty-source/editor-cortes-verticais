#!/data/data/com.termux/files/usr/bin/sh
# Roda sozinho a cada boot (Termux:Boot). Mantém o painel da nuvem do Jarvis sempre no ar.
termux-wake-lock
cd ~/tablet_cloud
curl -sL -o server.py https://raw.githubusercontent.com/jonathaarty-source/editor-cortes-verticais/main/tablet_cloud/server.py
curl -sL -o dashboard.html https://raw.githubusercontent.com/jonathaarty-source/editor-cortes-verticais/main/tablet_cloud/dashboard.html
curl -sL -o notif_watch.sh https://raw.githubusercontent.com/jonathaarty-source/editor-cortes-verticais/main/tablet_cloud/notif_watch.sh
curl -sL -o inspetor.sh https://raw.githubusercontent.com/jonathaarty-source/editor-cortes-verticais/main/tablet_cloud/inspetor.sh
chmod +x notif_watch.sh inspetor.sh
nohup python server.py > server.log 2>&1 &
nohup sh notif_watch.sh > notif.log 2>&1 &
nohup sh inspetor.sh > /dev/null 2>&1 &
# A tela inicial já é o painel (Webview Kiosk virou o launcher padrão), não precisa abrir nada.

# OBS: o Wi-Fi-sempre-ligado (deviceidle/wifi_sleep_policy) NÃO pode ser feito aqui.
# Termux roda como app comum e essas chamadas exigem android.permission.DEVICE_POWER,
# que só o usuário "shell" do adb (ou root) possui. Sem isso, reaplicar exige
# `adb shell` depois de cada reboot (ver tablet_wifi_sempre.sh no PC).
