"""Ponte do Telegram: recebe mensagem do dono pelo bot, grava como pedido no cofre (repositório privado) e manda de volta
a resposta que a empresa escrever lá.
REGRA: nada de mensagem, nome ou número vai para a tela (o registro deste repositório é público).
Cofre:  telegram/dono.txt        = número da conversa do dono (o primeiro que falar com o bot vira o dono)
        telegram/fila/<id>.json  = pedidos esperando a empresa
        telegram/respostas/<id>.md = respostas prontas para mandar;  telegram/enviadas/ = já mandadas
Segredos: TELEGRAM_TOKEN, COFRE_REPO, COFRE_TOKEN.  Uso: python nuvem/telegram.py [segundos de plantão]"""
import json, os, subprocess, sys, time, urllib.parse, urllib.request

TOKEN = os.environ.get('TELEGRAM_TOKEN', '').strip()
REPO, CT = os.environ.get('COFRE_REPO', '').strip(), os.environ.get('COFRE_TOKEN', '').strip()
PLANTAO = int(sys.argv[1]) if len(sys.argv) > 1 else 270
COFRE = 'cofre'; TG = os.path.join(COFRE, 'telegram')
import re
SAUDACAO = re.compile(r'^\W*(oi+|ol[aá]|opa|e a[ií]|eai|bom dia|boa tarde|boa noite|teste|testando|al[oô]|jarvis|t[aá] a[ií]|tudo bem|blz|beleza)[\s\W]*(jarvis)?[\s\W]*$', re.I)


def api(metodo, **dados):
    req = urllib.request.Request(f'https://api.telegram.org/bot{TOKEN}/{metodo}', data=urllib.parse.urlencode(dados).encode())
    try:
        with urllib.request.urlopen(req, timeout=40) as r: return json.load(r)
    except Exception as e:
        return {'ok': False, 'erro': type(e).__name__}   # nunca mostrar o endereço: ele leva o token


def git(*a):
    return subprocess.run(['git', '-C', COFRE, *a], capture_output=True, text=True)


def guardar(msg):
    if git('status', '--porcelain').stdout.strip() == '': return
    git('add', 'telegram')
    git('-c', 'user.name=ponte-telegram', '-c', 'user.email=ponte-telegram@users.noreply.github.com', 'commit', '-q', '-m', msg)
    for _ in range(3):
        git('pull', '-q', '--rebase')
        if git('push', '-q').returncode == 0: return
        time.sleep(4)


def ouvir(m):
    """Áudio/voz do Telegram vira texto (faster-whisper, instalado só quando chega o primeiro áudio). Devolve '' se não deu."""
    v = m.get('voice') or m.get('audio') or m.get('video_note')
    if not v: return ''
    try:
        info = api('getFile', file_id=v['file_id'])
        caminho = (info.get('result') or {}).get('file_path')
        if not caminho: return ''
        ogg = '/tmp/tg_audio.oga'; wav = '/tmp/tg_audio.wav'
        urllib.request.urlretrieve(f'https://api.telegram.org/file/bot{TOKEN}/{caminho}', ogg)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', ogg, '-ar', '16000', '-ac', '1', wav], check=True)
        try: from faster_whisper import WhisperModel
        except ImportError:
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'faster-whisper'], check=True)
            from faster_whisper import WhisperModel
        mod = WhisperModel('small', device='cpu', compute_type='int8')
        segs, _ = mod.transcribe(wav, language='pt', vad_filter=True)
        return ' '.join(x.text.strip() for x in segs).strip()
    except Exception as e:
        print('áudio não transcrito:', type(e).__name__)   # nunca mostrar o endereço: ele leva o token
        return ''


def despertar(agora=None):
    """DESPERTADOR (11/11): o agendamento do GitHub atrasa horas no cofre. Este plantão roda sem parar, então ele mesmo
    acorda cada sala na hora: lê cofre/despertador/agenda.json ([{"slot": "...", "hora": "06:00"}], hora de Fortaleza) e,
    se passou 3 min da hora e a sala ainda não marcou despertador/feito/<dia>_<slot>, grava despertador/pedir/<dia>_<slot>.json
    (o cofre dispara a sala por esse arquivo). Só olha as últimas 2 horas: sala muito velha não é ressuscitada."""
    try:
        base = os.path.join(COFRE, 'despertador')
        agenda = json.load(open(os.path.join(base, 'agenda.json'), encoding='utf-8'))
        t = time.gmtime((agora or time.time()) - 3 * 3600)   # Fortaleza = UTC-3, sem horário de verão
        dia = time.strftime('%Y-%m-%d', t); minuto = t.tm_hour * 60 + t.tm_min; pediu = 0
        for a in agenda:
            h, m = str(a['hora']).split(':'); alvo = int(h) * 60 + int(m); slot = str(a['slot'])
            if not (alvo + 3 <= minuto <= alvo + 120): continue
            if os.path.exists(os.path.join(base, 'feito', f'{dia}_{slot}')): continue
            arq = os.path.join(base, 'pedir', f'{dia}_{slot}.json')
            if os.path.exists(arq): continue
            os.makedirs(os.path.dirname(arq), exist_ok=True)
            json.dump({'slot': slot, 'dia': dia, 'pedido_em_utc': time.strftime('%H:%M', time.gmtime(agora or time.time()))}, open(arq, 'w'))
            pediu += 1
        if pediu:
            git('add', 'despertador')
            git('-c', 'user.name=despertador', '-c', 'user.email=despertador@users.noreply.github.com', 'commit', '-q', '-m', 'despertador: sala na hora')
            for _ in range(3):
                git('pull', '-q', '--rebase')
                if git('push', '-q').returncode == 0: break
                time.sleep(4)
            print(f'despertador: {pediu} sala(s) acordada(s)')
        return pediu
    except FileNotFoundError:
        return 0
    except Exception as e:
        print('despertador falhou:', type(e).__name__); return 0


def falar(chat, texto):
    for i in range(0, max(1, len(texto)), 3900): api('sendMessage', chat_id=chat, text=texto[i:i + 3900] or '(vazio)')


def main():
    if not (TOKEN and REPO and CT): print('ponte sem segredos: nada a fazer'); return
    r = subprocess.run(['git', 'clone', '-q', '--depth', '1', f'https://x-access-token:{CT}@github.com/{REPO}.git', COFRE], capture_output=True, text=True)
    if r.returncode: print('não abri o cofre'); sys.exit(1)
    for p in ('fila', 'respostas', 'enviadas'): os.makedirs(os.path.join(TG, p), exist_ok=True)
    dono_arq = os.path.join(TG, 'dono.txt')
    dono = open(dono_arq).read().strip() if os.path.exists(dono_arq) else ''
    recebidas = enviadas = 0; fim = time.time() + PLANTAO; prox = None
    while True:
        # 1) respostas que a empresa deixou prontas
        git('pull', '-q', '--rebase')
        despertar()
        for f in sorted(os.listdir(os.path.join(TG, 'respostas'))):
            if not f.endswith('.md') or not dono: continue
            falar(dono, open(os.path.join(TG, 'respostas', f), encoding='utf-8').read().strip())
            git('mv', '-f', f'telegram/respostas/{f}', f'telegram/enviadas/{f}'); enviadas += 1
        guardar('telegram: respostas enviadas')
        # 2) mensagens novas (espera longa de 25 s: quase na hora, sem ficar martelando)
        espera = 25 if fim - time.time() > 30 else 0
        u = api('getUpdates', timeout=espera, **({'offset': prox} if prox else {}))
        if not u.get('ok'): time.sleep(8); u = {'result': []}
        for x in (u.get('result') or []):
            prox = x['update_id'] + 1
            m = x.get('message') or {}; texto = (m.get('text') or m.get('caption') or '').strip(); chat = str((m.get('chat') or {}).get('id', ''))
            if not chat: continue
            eh_audio = bool(m.get('voice') or m.get('audio') or m.get('video_note'))
            if eh_audio and not texto and chat == dono:
                falar(chat, 'Ouvindo o seu áudio, senhor.')
                texto = ouvir(m)
                if not texto:
                    falar(chat, 'Recebi o áudio, senhor, mas não consegui entender. Pode escrever ou mandar de novo?'); continue
                falar(chat, 'Entendi: ' + texto[:300])
            if not dono:
                dono = chat; open(dono_arq, 'w').write(dono)
                falar(chat, 'Senhor, registrei este Telegram como o do dono. A partir de agora só obedeço a esta conversa.')
            if chat != dono: continue
            if not texto or texto == '/start':
                falar(chat, 'Às ordens, senhor. Escreva o pedido aqui que eu passo para a empresa.'); continue
            # saudação ou teste não vira pedido: a empresa inteira levava ~11 min de nuvem para responder um "oi"
            if SAUDACAO.match(texto):
                falar(chat, 'Estou aqui, senhor. Diga o que o senhor precisa (um vídeo, uma legenda, uma lista de leads, um plano) e eu passo para a empresa.'); continue
            json.dump({'id': x['update_id'], 'texto': texto, 'quando': m.get('date')}, open(os.path.join(TG, 'fila', f"{x['update_id']}.json"), 'w', encoding='utf-8'), ensure_ascii=False)
            falar(chat, 'Recebi, senhor. A empresa está trabalhando e eu respondo aqui quando terminar.'); recebidas += 1
        if prox: api('getUpdates', offset=prox, timeout=0)   # confirma: o Telegram não manda de novo
        guardar('telegram: pedidos novos')
        if time.time() >= fim: break
    print(f'plantão encerrado: {recebidas} pedidos recebidos, {enviadas} respostas enviadas')


if __name__ == '__main__':
    main()
