#!/usr/bin/env python3
"""Painel da Nuvem do Jarvis no tablet. v2: visual glass estilo wellness, dados reais.
Uso: python server.py   (abre em http://127.0.0.1:8088)"""
import http.server, json, os, shutil, subprocess, time

PORTA = 8088
INICIO = time.time()


def bateria():
    # termux-battery-status dispara um processo-filho (termux-api) que conversa com o app
    # Termux:API por socket; se o Python so mata o processo direto no timeout, esse filho
    # fica orfao pendurado pra sempre esperando resposta (achado 11/11: dezenas acumulados,
    # consumindo memoria no tablet que so tem 2GB). Por isso cria um grupo de processos
    # novo e mata o grupo inteiro se estourar o tempo, nunca so o processo pai.
    proc = None
    try:
        proc = subprocess.Popen(['termux-battery-status'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                 text=True, start_new_session=True)
        saida, _ = proc.communicate(timeout=8)
        return json.loads(saida).get('percentage')
    except Exception:
        if proc is not None:
            try:
                os.killpg(os.getpgid(proc.pid), 9)
            except Exception:
                pass
        try:
            with open('/sys/class/power_supply/battery/capacity') as f:
                return int(f.read().strip())
        except Exception:
            return None


def propriedade(nome):
    try:
        return subprocess.run(['getprop', nome], capture_output=True, text=True, timeout=3).stdout.strip()
    except Exception:
        return ''


def ip_wifi():
    try:
        out = subprocess.run(['ip', 'addr', 'show', 'wlan0'], capture_output=True, text=True, timeout=3).stdout
        for linha in out.splitlines():
            linha = linha.strip()
            if linha.startswith('inet '):
                return linha.split()[1].split('/')[0]
    except Exception:
        pass
    return None


def ultimas_linhas_log(nome, n=8):
    caminho = os.path.expanduser(f'~/tablet_cloud/{nome}')
    try:
        with open(caminho, encoding='utf-8', errors='replace') as f:
            linhas = f.readlines()
        return [l.strip() for l in linhas[-n:]]
    except Exception:
        return []


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
        'dispositivo': {
            'modelo': propriedade('ro.product.model') or '—',
            'android': propriedade('ro.build.version.release') or '—',
            'disco_total_gb': round(disco.total / (1024**3), 1),
            'disco_usado_gb': round((disco.total - disco.free) / (1024**3), 1),
        },
        'rede_detalhe': {
            'ip': ip_wifi() or '—',
        },
        'logs': {
            'inspetor': ultimas_linhas_log('inspetor.log'),
            'oi_jarvis': ultimas_linhas_log('oi_jarvis.log'),
            'notif': ultimas_linhas_log('notif.log'),
        },
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
    def do_POST(self):
        if self.path == '/oi_jarvis':
            subprocess.Popen(['sh', os.path.expanduser('~/tablet_cloud/oi_jarvis.sh')])
            body = b'{"ok":true}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

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
