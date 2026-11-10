# ENQUADRAMENTO POR QUEM FALA: no recorte 9:16 de um quadro 16:9, a janela vai para quem está falando.
# O principal (quem grava) fica centralizado quando fala; quando outro fala, a janela vai para essa pessoa,
# mas o principal nunca fica pela metade no canto (ou entra inteiro perto do centro, ou sai do quadro).
#  - quem fala: nível da voz por frase (o microfone de quem grava chega mais forte que a voz do jogo),
#    separado em 2 grupos por vídeo; diferença menor que 4 dB = tudo é do principal.
#  - onde estão: YOLO (yolo11n, só "pessoa", CPU) em 2 quadros por segundo; o principal é a pessoa maior e mais
#    baixa no quadro (câmera em terceira pessoa atrás dele).
#  - a janela só muda em troca de quem fala (corte seco, nunca panorâmica no meio da fala).
import json, os, subprocess, wave, tempfile
import numpy as np

MOD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modelos', 'yolo11n.pt')
if not os.path.exists(MOD): MOD = 'yolo11n.pt'   # a biblioteca baixa sozinha na primeira vez
_yolo = None

def _modelo():
    global _yolo
    if _yolo is None:
        import torch; torch.set_num_threads(2)
        from ultralytics import YOLO
        _yolo = YOLO(MOD)
    return _yolo

def pessoas(src, tempos, larg=1920):
    """caixas de pessoa (x0, y0, x1, y1, conf) no tempo t, coordenadas do quadro original."""
    m = _modelo(); out = {}
    for t in tempos:
        tmp = tempfile.mktemp(suffix='.jpg')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.2f}', '-i', src, '-frames:v', '1', '-q:v', '4', tmp])
        if not os.path.exists(tmp): out[t] = []; continue
        r = m.predict(tmp, classes=[0], conf=0.35, verbose=False, device='cpu', imgsz=640)[0]
        out[t] = [tuple(float(v) for v in b) + (float(c),) for b, c in zip(r.boxes.xyxy, r.boxes.conf)]
        os.remove(tmp)
    return out

def nivel_frases(wav, frases):
    w = wave.open(wav); sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    niv = []
    for f in frases:
        ws = [np.sqrt(np.mean(x[int(a * sr):int(b * sr)] ** 2)) for a, b, *_ in f['w'] if b > a]
        niv.append(20 * np.log10(np.percentile(ws, 75) + 1e-9) if ws else -99)
    return np.array(niv)

def quem_fala(wav, frases):
    """True = streamer, por frase."""
    v = nivel_frases(wav, frases); ok = v > -90
    if ok.sum() < 3: return [True] * len(frases), None
    lo, hi = np.percentile(v[ok], 20), np.percentile(v[ok], 80)
    for _ in range(20):
        lim = (lo + hi) / 2; a = v[ok & (v >= lim)]; b = v[ok & (v < lim)]
        if len(a) == 0 or len(b) == 0: break
        hi, lo = a.mean(), b.mean()
    if hi - lo < 4: return [True] * len(frases), None
    lim = (lo + hi) / 2
    return [bool(n >= lim or n <= -90) for n in v], float(lim)

def principal(caixas, W=1920, H=1080):
    """personagem do streamer: a pessoa com a base mais baixa e maior área, perto do meio."""
    if not caixas: return None
    def nota(b): return (b[3] / H) * 2 + ((b[2] - b[0]) * (b[3] - b[1])) / (W * H) * 4 - abs((b[0] + b[2]) / 2 - W / 2) / W
    return max(caixas, key=nota)

def janela_x(caixas, fala_streamer, cw, W=1920):
    """centro x da janela (largura cw no quadro original)."""
    p = principal(caixas)
    if p is None: return W / 2
    pc = (p[0] + p[2]) / 2
    if fala_streamer or len(caixas) < 2: return pc
    # pessoa pequena (foto na parede, gente lá no fundo) ou com pouca certeza não conta como interlocutor
    outros = [b for b in caixas if b is not p and (b[3] - b[1]) >= 0.3 * 1080 and b[4] >= 0.5]
    if not outros: return pc
    # quem conversa com o streamer costuma ser a pessoa mais perto dele (não a maior do quadro)
    o = min(outros, key=lambda b: abs((b[0] + b[2]) / 2 - (p[0] + p[2]) / 2))
    oc = (o[0] + o[2]) / 2; meia = cw / 2; pw = (p[2] - p[0]) / 2
    # cabem os dois com o streamer perto do centro? enquadra o meio dos dois
    if abs(oc - pc) <= meia * 0.55: return (oc + pc) / 2
    # senão, centra em quem fala e empurra até o streamer sair inteiro (nunca pela metade no canto)
    c = oc
    if abs(pc - c) < meia + pw:
        c = pc + (meia + pw) * (1 if oc > pc else -1)
        if abs(c - oc) > meia * 0.8: c = oc   # não dá para tirar o streamer sem cortar quem fala: fica em quem fala
    return c

def turnos(src, wav, frases, ini, fim, cw, W=1920):
    """[(t0, t1, cx)] no tempo do trecho: uma janela por troca de quem fala."""
    fr = [f for f in frases if f['e'] > ini and f['s'] < fim and f.get('w')]
    if not fr: return [(ini, fim, W / 2)], None, []
    quem, lim = quem_fala(wav, fr)
    # junta frases seguidas da mesma pessoa
    blocos = []
    for f, q in zip(fr, quem):
        if blocos and blocos[-1][2] == q: blocos[-1][1] = f['e']
        else: blocos.append([f['s'], f['e'], q])
    tempos = sorted({round(min(fim, max(ini, t)), 2) for a, b, _ in blocos for t in np.arange(a + 0.3, max(a + 0.31, b), 0.5)})
    cx = pessoas(src, tempos)
    out = []
    # fala curta de outra pessoa (menos de 1,5 s, tipo "não") não troca a janela: evita pisca-pisca
    for k in range(len(blocos)):
        if not blocos[k][2] and blocos[k][1] - blocos[k][0] < 1.5: blocos[k][2] = True
    for k, (a, b, q) in enumerate(blocos):
        ts_b = [t for t in tempos if a - 0.01 <= t <= b + 0.31]
        # outra pessoa só ganha a janela se aparecer em pelo menos metade dos quadros do bloco
        if not q and sum(sum((b[3] - b[1]) >= 0.3 * 1080 and b[4] >= 0.5 for b in cx[t]) >= 2 for t in ts_b) < max(1, len(ts_b)) / 2: q = True
        vals = [(t, min(max(janela_x(cx[t], q, cw, W), cw / 2), W - cw / 2)) for t in ts_b] or [(a, W / 2)]
        t0 = ini if k == 0 else (blocos[k - 1][1] + a) / 2
        t1 = fim if k == len(blocos) - 1 else (b + blocos[k + 1][0]) / 2
        # a câmera do jogo pode girar no meio do bloco: cada trecho estável vira uma janela (corte seco onde ela pulou)
        runs = [[vals[0][0], [vals[0][1]]]]
        for t, v in vals[1:]:
            if abs(v - np.median(runs[-1][1])) < cw * 0.25: runs[-1][1].append(v)
            else: runs.append([t, [v]])
        for r_i, (rt, rv) in enumerate(runs):
            r0 = t0 if r_i == 0 else rt - 0.25
            r1 = t1 if r_i == len(runs) - 1 else runs[r_i + 1][0] - 0.25
            c = float(np.median(rv))
            if out and abs(out[-1][2] - c) < cw * 0.12: out[-1] = (out[-1][0], r1, out[-1][2])   # mudança pequena não vira corte
            else: out.append((r0, r1, c))
    # limpeza: sem sobreposição e nenhuma janela menor que 1,2 s (pisca-pisca); a curta herda a janela de antes
    lim_t = []
    for t0, t1, c in sorted(out):
        if lim_t: t0 = max(t0, lim_t[-1][1])
        if t1 - t0 <= 0.01: continue
        lim_t.append([t0, t1, c])
    k = 0
    while k < len(lim_t):
        if lim_t[k][1] - lim_t[k][0] < 1.2 and len(lim_t) > 1:
            if k > 0: lim_t[k - 1][1] = lim_t[k][1]
            else: lim_t[k + 1][0] = lim_t[k][0]
            lim_t.pop(k)
        else: k += 1
    j = []
    for t0, t1, c in lim_t:
        if j and abs(j[-1][2] - c) < cw * 0.12: j[-1][1] = t1
        else: j.append([t0, t1, c])
    if j: j[0][0] = ini; j[-1][1] = fim
    return [tuple(x) for x in j], lim, [(a, b, q) for a, b, q in blocos]
