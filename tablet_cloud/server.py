#!/usr/bin/env python3
"""Painel da Nuvem do Jarvis no tablet. v1: roda local, sem segredo nenhum.
Uso: python server.py   (abre em http://127.0.0.1:8088 e http://<ip-do-tablet>:8088)"""
import http.server, json, os, shutil, subprocess, time

PORTA = 8088
INICIO = time.time()


def bateria():
    try:
        out = subprocess.run(['termux-battery-status'], capture_output=True, text=True, timeout=3)
        return json.loads(out.stdout).get('percentage')
    except Exception:
        try:
            for linha in open('/sys/class/power_supply/battery/capacity'):
                return int(linha.strip())
        except Exception:
            return None


def status():
    disco = shutil.disk_usage(os.path.expanduser('~'))
    uptime_s = int(time.time() - INICIO)
    h, m = divmod(uptime_s // 60, 60)
    return {
        'bateria': bateria(),
        'uptime': f'{h}h{m:02d}m (deste painel)',
        'disco_livre': f'{disco.free // (1024*1024)} MB livres',
        'python': subprocess.run(['python', '--version'], capture_output=True, text=True).stdout.strip() or '—',
        'git': subprocess.run(['git', '--version'], capture_output=True, text=True).stdout.strip() or '—',
        'telegram_ativo': os.path.exists(os.path.expanduser('~/tablet_cloud/telegram_ativo.flag')),
    }


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
