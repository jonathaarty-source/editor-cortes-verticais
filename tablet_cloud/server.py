#!/usr/bin/env python3
"""Painel da Nuvem do Jarvis no tablet. v2: visual glass estilo wellness, dados reais.
Uso: python server.py   (abre em http://127.0.0.1:8088)"""
import http.server, json, os, shutil, subprocess, time

PORTA = 8088
INICIO = time.time()


def bateria():
    try:
        out = subprocess.run(['termux-battery-status'], capture_output=True, text=True, timeout=8)
        return json.loads(out.stdout).get('percentage')
    except Exception:
        try:
            with open('/sys/class/power_supply/battery/capacity') as f:
                return int(f.read().strip())
        except Exception:
            return None


def status():
    disco = shutil.disk_usage(os.path.expanduser('~'))
    uptime_s = int(time.time() - INICIO)
    h, m = divmod(uptime_s // 60, 60)
    livre_pct = round(disco.free / disco.total * 100)
    bat = bateria()
    # pontuação composta simples: espaço livre + bateria + rede sempre ligada (fixo 100 aqui)
    partes = [p for p in [livre_pct, bat, 100] if p is not None]
    saude = round(sum(partes) / len(partes)) if partes else None
    return {
        'bateria': bat,
        'uptime': f'{h}h{m:02d}m',
        'disco_livre_mb': disco.free // (1024 * 1024),
        'disco_livre_pct': livre_pct,
        'saude': saude,
        'python': subprocess.run(['python', '--version'], capture_output=True, text=True).stdout.strip() or '—',
        'git': subprocess.run(['git', '--version'], capture_output=True, text=True).stdout.strip() or '—',
        'telegram_ativo': os.path.exists(os.path.expanduser('~/tablet_cloud/telegram_ativo.flag')),
        'inspetor_ativo': inspetor_vivo(),
    }


def inspetor_vivo():
    f = os.path.expanduser('~/tablet_cloud/inspetor_ok.flag')
    try:
        return (time.time() - os.path.getmtime(f)) < 180
    except Exception:
        return False


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status.json':
            body = json.dumps(status()).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == '/':
            self.path = '/dashboard.html'
        return super().do_GET()

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    os.chdir(os.path.expanduser('~/tablet_cloud'))
    print(f'Painel no ar: http://0.0.0.0:{PORTA}/')
    http.server.ThreadingHTTPServer(('0.0.0.0', PORTA), Handler).serve_forever()
