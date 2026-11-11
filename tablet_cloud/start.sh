#!/data/data/com.termux/files/usr/bin/sh
# Roda sozinho a cada boot (Termux:Boot). Mantém o painel da nuvem do Jarvis sempre no ar.
termux-wake-lock
cd ~/tablet_cloud

# espera o Wi-Fi conectar antes de baixar (no boot ele pode ainda nao estar pronto;
# sem isso os curls abaixo falham silenciosamente e ficam com a versao antiga em disco)
i=0
while [ $i -lt 20 ] && ! curl -s -m 3 -o /dev/null https://raw.githubusercontent.com; do
  sleep 2
  i=$((i+1))
done

curl -sL -o server.py https://raw.githubusercontent.com/jonathaarty-source/editor-cortes-verticais/main/tablet_cloud/server.py
curl -sL -o dashboard.html https://raw.githubusercontent.com/jonathaarty-source/editor-cortes-verticais/main/tablet_cloud/dashboard.html
curl -sL -o notif_watch.sh https://raw.githubusercontent.com/jonathaarty-source/editor-cortes-verticais/main/tablet_cloud/notif_watch.sh
curl -sL -o inspetor.sh https://raw.githubusercontent.com/jonathaarty-source/editor-cortes-verticais/main/tablet_cloud/inspetor.sh
curl -sL -o oi_jarvis.sh https://raw.githubusercontent.com/jonathaarty-source/editor-cortes-verticais/main/tablet_cloud/oi_jarvis.sh
chmod +x notif_watch.sh inspetor.sh oi_jarvis.sh
nohup python server.py > server.log 2>&1 &
nohup sh notif_watch.sh > notif.log 2>&1 &
nohup sh inspetor.sh > /dev/null 2>&1 &
# A tela inicial já é o painel (Webview Kiosk virou o launcher padrão), não precisa abrir nada.

# liga a escuta continua ("Oi Jarvis") sozinha, depois que o Jarvis Mao tiver tempo de subir
sleep 20
curl -s -m 8 -X POST http://127.0.0.1:8099/ -d '{"action":"hotword_on"}' >> oi_jarvis.log 2>&1

# OBS: o Wi-Fi-sempre-ligado (deviceidle/wifi_sleep_policy) NÃO pode ser feito aqui.
# Termux roda como app comum e essas chamadas exigem android.permission.DEVICE_POWER,
# que só o usuário "shell" do adb (ou root) possui. Sem isso, reaplicar exige
# `adb shell` depois de cada reboot (ver tablet_wifi_sempre.sh no PC).
