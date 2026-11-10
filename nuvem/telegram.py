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
        for f in sorted(os.listdir(os.path.join(TG, 'respostas'))):
            if not f.endswith('.md') or not dono: continue
            falar(dono, open(os.path.join(TG, 'respostas', f), encoding='utf-8').read().strip())
            git('mv', '-f', f'telegram/respostas/{f}', f'telegram/enviadas/{f}'); enviadas += 1
        guardar('telegram: respostas enviadas')
        # 2) mensagens novas (espera longa de 25 s: quase na hora, sem ficar martelando)
        espera = 25 if fim - time.time() > 30 else 0
        u = api('getUpdates', timeout=espera, **({'offset': prox} if prox else {}))
        for x in (u.get('result') or []):
            prox = x['update_id'] + 1
            m = x.get('message') or {}; texto = (m.get('text') or m.get('caption') or '').strip(); chat = str((m.get('chat') or {}).get('id', ''))
            if not chat: continue
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
