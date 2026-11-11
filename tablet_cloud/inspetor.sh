#!/data/data/com.termux/files/usr/bin/sh
# Inspetor: varre o tablet sem parar. Se achar o painel ou o vigia de notificação
# caídos, reconserta sozinho. Guarda tudo em inspetor.log.
cd ~/tablet_cloud
LOG=inspetor.log

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"
}

log "inspetor ligado"

while true; do
  if ! pgrep -f "python server.py" > /dev/null; then
    log "painel caiu, subindo de novo"
    nohup python server.py > server.log 2>&1 &
  fi

  if ! pgrep -f "sh notif_watch.sh" > /dev/null; then
    log "vigia de notificacao caiu, subindo de novo"
    nohup sh notif_watch.sh > notif.log 2>&1 &
  fi

  # espaço livre baixo: limpa cache do proprio Termux (nao mexe em outro app, sem permissao pra isso)
  livre_mb=$(df -m ~ 2>/dev/null | tail -1 | awk '{print $4}')
  if [ -n "$livre_mb" ] && [ "$livre_mb" -lt 500 ]; then
    log "espaco baixo (${livre_mb}MB), limpando cache do termux"
    rm -rf ~/.cache/pip 2>/dev/null
    find ~ -name "*.log" -size +5M -delete 2>/dev/null
  fi

  # apaga logs que cresceram demais (nunca deixa acumular lixo)
  for f in server.log notif.log inspetor.log; do
    if [ -f "$f" ]; then
      sz=$(wc -c < "$f" 2>/dev/null || echo 0)
      if [ "$sz" -gt 2000000 ]; then
        tail -c 200000 "$f" > "$f.tmp" && mv "$f.tmp" "$f"
        log "log $f estava grande, cortado"
      fi
    fi
  done

  touch inspetor_ok.flag
  sleep 60
done
