#!/data/data/com.termux/files/usr/bin/sh
# Vigia de notificação: se tiver mais de 2 notificações de app ao mesmo tempo, limpa todas.
# Ignora as notificações de sistema do Android (uid 1000) e do próprio Termux (wake-lock).
MAX=2
while true; do
  linhas=$(cmd notification list 2>/dev/null | grep -v '^-1|android|' | grep -v '|com.termux|')
  n=$(echo "$linhas" | grep -c '|')
  if [ "$n" -gt "$MAX" ]; then
    echo "$linhas" | while IFS= read -r chave; do
      [ -n "$chave" ] && cmd notification snooze --for 315360000000 "$chave" >/dev/null 2>&1
    done
  fi
  sleep 4
done
