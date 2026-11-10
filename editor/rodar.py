"""Roda UM pedido de corte vertical do começo ao fim: baixa o trecho, transcreve, monta a legenda, enquadra e renderiza.
uso: python rodar.py pedido.json pasta_de_saida

pedido.json (tudo opcional menos a fonte):
  fonte        {"arquivo": "video.mp4"}  ou  {"url": "...", "ini": 120, "fim": 200}  (segundos do vídeo original)
  saida        nome do arquivo final (padrão: <id>.mp4)
  inicio, fim  onde o corte começa e termina DENTRO do trecho baixado
  manchete     "LINHA 1|LINHA 2" (some depois de 3 s)
  base_vf      filtro ffmpeg que leva o quadro a 1080x1920 (padrão: recorte central de um 16:9)
  pause        true = legenda com pop, zoom em reação, sons (se existirem em EDITOR_ASSETS/sons)
  leg_estilo   "branca" | "dj" | "karaoke"
  tag, tag_box, card, chamada, serif, junta, musica (false desliga), zoom_estalo, sons_cinema
  modelos      ["small"] ou ["large-v3", "medium"]: com dois modelos a legenda sai por consenso
  cor_personagem, enquadrar   true liga a cor por voz e a janela em quem fala (pedem torch; desligados por padrão)
  sem_leg      [[ini, fim], ...] trechos sem legenda;  confirmadas  [ini da frase, ...] frases que entram inteiras
A marca, os sons e a música de cada cliente NÃO ficam neste repositório: a pasta vem em EDITOR_ASSETS."""
import difflib, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from editor4 import editar
from transcrever import transcrever

PESADO = re.compile(r"^(caralh\w*|porr\w*|fod\w*|fud\w*|put\w*|merd\w*|viad\w*|bucet\w*|arromb\w*|desgra\w*|cacete|pica|piroca|rola|cu|pqp|vsf|fdp|quenga\w*)$", re.I)
BASE = "crop=ih*0.92*9/16:ih*0.92:(iw-ih*0.92*9/16)/2:0,scale=1080:1920"


def norm(s): return re.sub(r"[^\wáéíóúâêôãõçà]", "", s.lower())


def ast(p):
    """palavrão: a primeira vogal depois da primeira letra vira asterisco."""
    m = re.match(r"^(\W*)(\w)(\w*?)([aeiouáéíóúâêôãõ])(\w*)(\W*)$", p, re.I)
    return f"{m[1]}{m[2]}{m[3]}*{m[5]}{m[6]}" if m else p[0] + '*' * (len(p) - 1)


def palavras_de(segs):
    return [(w[0], w[1], str(w[2]).strip(), w[3] if len(w) > 3 else 1.0) for sg in segs for w in (sg.get('w') or []) if str(w[2]).strip()]


def fonte(ped, pasta):
    f = ped['fonte']
    if f.get('arquivo'): return f['arquivo']
    out = os.path.join(pasta, 'fonte.mp4')
    if os.path.exists(out): return out
    cmd = [sys.executable, '-m', 'yt_dlp', '-q', '--no-warnings', '-f', 'bv*[height<=1080]+ba/b[height<=1080]', '--merge-output-format', 'mp4', '-o', out]
    if 'ini' in f and 'fim' in f: cmd += ['--download-sections', f"*{f['ini']}-{f['fim']}", '--force-keyframes-at-cuts']
    r = subprocess.run(cmd + [f['url']], capture_output=True, text=True)
    if r.returncode or not os.path.exists(out): raise RuntimeError('não baixou a fonte: ' + r.stderr[-600:])
    return out


def legenda(A, B, SA, c):
    """A, B: palavras de dois modelos (B pode ser vazio). Palavra cai quando o 2º modelo ouviu OUTRA coisa no mesmo ponto
    ou quando o 1º tem pouca confiança; silêncio do 2º não é voto contra. Devolve (fala, legenda, bips)."""
    A2 = []
    for x in A:   # "terça" + "-feira": o pedaço com hífen volta para a palavra de antes
        if A2 and x[2].startswith('-'): A2[-1] = (A2[-1][0], x[1], A2[-1][2] + x[2], min(A2[-1][3], x[3]))
        else: A2.append(x)
    C = []
    for a0, a1, w, p in A2:
        cand = [v for v in B if abs(v[0] - a0) < 0.7]
        ok = (p >= 0.5) if not cand else any(difflib.SequenceMatcher(None, norm(w), norm(v[2])).ratio() >= 0.75 for v in cand)
        C.append((a0, a1, w, p, ok))
    fala = [(a, b, w) for a, b, w, p, ok in C]   # presença de fala: toda palavra ouvida conta (a legenda é que filtra)
    leg, bips = [], []
    for s in SA:
        ws = [x for x in C if s['s'] - 0.05 <= x[0] <= s['e'] + 0.05]
        if not ws: continue
        forcada = round(s['s'], 1) in c.get('confirmadas', [])
        frase_ok = forcada or (sum(x[4] for x in ws) / len(ws) >= 0.7 and sum(x[3] for x in ws) / len(ws) >= 0.55)
        for a, b, w, p, ok in ws:
            if PESADO.match(norm(w)): bips.append((a, b)); w = ast(w)
            if frase_ok and not any(l0 <= a < l1 for l0, l1 in c.get('sem_leg', [])) and (ok or p >= 0.8 or forcada): leg.append((a, b, w))
    return fala, leg, bips, len(C)


def rodar(ped, pasta):
    os.makedirs(pasta, exist_ok=True)
    nome = ped.get('saida') or (ped.get('id', 'corte') + '.mp4')
    src = fonte(ped, pasta)
    wav = os.path.join(pasta, 'fonte.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vn', '-ac', '1', '-ar', '16000', wav], check=True)
    modelos = ped.get('modelos') or ['small']; thr = int(os.environ.get('EDITOR_THREADS', '4'))
    SA = transcrever(wav, os.path.join(pasta, 'transc_a.json'), modelos[0], thr)
    SB = transcrever(wav, os.path.join(pasta, 'transc_b.json'), modelos[1], thr) if len(modelos) > 1 else []
    fala, leg, bips, n_pal = legenda(palavras_de(SA), palavras_de(SB), SA, ped)
    if not fala: raise RuntimeError('nenhuma fala encontrada no trecho')
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout.strip() or 0)
    ini, fim = float(ped.get('inicio', 0)), float(ped.get('fim') or dur)
    if ped.get('cor_personagem'):
        from quem_fala import colorir
        leg = colorir(wav, SA, leg)
    tt = None
    if ped.get('enquadrar'):
        from enquadra import turnos
        tt, _, _ = turnos(src, wav, SA, ini, fim, ped.get('cw', 1080 * 0.92 * 9 / 16))
    extra = {k: ped[k] for k in ('tag', 'card', 'serif', 'junta', 'leg_estilo', 'zoom_estalo', 'sons_cinema', 'y_leg', 'y_box', 'max_dur', 'card_dur', 'congela') if k in ped}
    if 'tag_box' in ped: extra['tag_box'] = tuple(ped['tag_box'])
    if 'chamada' in ped: extra['chamada'] = tuple(ped['chamada'])
    if ped.get('musica') is False: extra['musica'] = None
    out = os.path.join(pasta, nome)
    ok, msg, cortes, _ = editar(src, fala, out, ped.get('base_vf') or BASE, manchete=ped['manchete'].split('|') if ped.get('manchete') else None,
                                inicio=ini, fim=fim, leg_palavras=leg, bips=bips, cx_turnos=tt, pause=bool(ped.get('pause', True)), **extra)
    rel = dict(ok=ok, msg=msg if ok else msg[-1500:], bips=len(bips), legenda=f'{len(leg)}/{n_pal}', modelos=modelos,
               pior_borda_db=round(max([max(x[1], x[3]) for x in cortes] or [0]), 1))
    json.dump(rel, open(out[:-4] + '.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return rel


if __name__ == '__main__':
    r = rodar(json.load(open(sys.argv[1], encoding='utf-8-sig')), sys.argv[2])
    print(json.dumps(r, ensure_ascii=False))
    sys.exit(0 if r['ok'] else 1)
