# EDITOR 4: editor3 mais limpo e com fechamento.
#  1. zoom só troca onde já existe corte; dentro de cada fala a câmera faz um empurrão lento e contínuo.
#  2. todo corte cai no ponto mais baixo de áudio (RMS em janelas de 10 ms) na folga antes e depois da fala.
#  3. marca d'água opcional (PNG) sempre na tela.
#  4. fechamento: a frase final congela e entra o card da marca com a chamada.
import os, re, subprocess, tempfile, wave
import numpy as np
from editor3 import legenda_ass, falas, FONTES_DIR, FONTE, FONTE_ARQ, FONTES_ARQ, ASSETS, ENTRADA, VCODEC

def legenda_branca(palavras, trechos, arq, y=1300):
    # branco, caixa alta, contorno e sombra pretos, sem palavra colorida
    return legenda_ass(palavras, trechos, arq, y, cor_ativa='&H00FFFFFF')

CARD = None   # card de fecho: vem no pedido (arquivo dentro de EDITOR_ASSETS)

# ---------- MODO PAUSE ----------
# zoom com estalo só em reação/risada (nunca em todo corte), whoosh no zoom, bonk na risada,
# música baixa que abaixa sozinha quando alguém fala, legenda palavra por palavra (Nunito Black, contorno grosso, pop).
SFX = os.path.join(ASSETS, 'sons')
SONS = {k: os.path.join(SFX, k + '.mp3') for k in ('whoosh', 'bonk', 'shocked')}
MUSICA = os.path.join(SFX, 'musica.mp3')
RISO = re.compile(r'^(k{3,}|(ha){2,}h?|(he){2,}|(rs){2,}|kkk\w*)$', re.I)
REACAO = re.compile(r'^(caralho|c\*ralho|porra|p\*rra|nossa|meu deus|que isso|eita|vixi|ixi|caramba|olha|toma|morreu|explodiu|mano)$', re.I)

def _ts(t): return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"

ACENTO = {'ta': 'tá', 'to': 'tô', 'ne': 'né', 'vei': 'véi', 'ja': 'já', 'so': 'só', 'la': 'lá', 'nao': 'não', 'voce': 'você',
          'entao': 'então', 'tao': 'tão', 'tambem': 'também', 'ce': 'cê', 'pe': 'pé', 'ate': 'até', 'mae': 'mãe', 'irmao': 'irmão'}

def acentua(w):
    """o Whisper escreve sem acento ('ta', 'vei'): corrige só palavra sem ambiguidade ('ai' fica: pode ser 'ai ai' ou 'aí')."""
    m = re.match(r'^(\W*)(\w+)(\W*)$', w)
    if not m or m[2].lower() not in ACENTO: return w
    c = ACENTO[m[2].lower()]
    c = c.upper() if m[2].isupper() and len(m[2]) > 1 else (c[0].upper() + c[1:] if m[2][0].isupper() else c)
    return m[1] + c + m[3]

def legenda_pause(palavras, trechos, arq, y=1250, estilo='pause'):
    # estilo 'pause' = Nunito Black com pop; 'dj' = caixa alta, palavra falada em azul, sem pulo
    # cor por personagem: palavra (a, b, w, cor) leva a cor da pessoa (quem_fala.CORES_ASS); mudou a pessoa, muda o bloco
    # palavra na divisa de duas frases entrava duas vezes ("tá tá", "foi foi"): uma vez só, pelo começo e pelo texto
    vistos, unicas = set(), []
    for p in sorted(palavras, key=lambda x: x[0]):
        k = (round(p[0], 2), p[2].strip().lower())
        if k not in vistos: vistos.add(k); unicas.append(p)
    palavras = unicas
    novo, acc = [], 0.0
    for a, b in trechos:
        for p in palavras:
            pa, pb, w = p[0], p[1], acentua(p[2].strip()); cor = p[3] if len(p) > 3 else '&H00FFFFFF'
            if a <= pa < b: novo.append((acc + pa - a, acc + min(pb, b) - a, w.upper().strip('.,!?') if estilo == 'dj' else w.strip(), cor))
        acc += b - a
    grupos, cur = [], []
    for p in novo:
        if cur and (len(cur) >= 3 or p[1] - cur[0][0] > 0.9 or p[0] - cur[-1][1] > 0.35 or cur[-1][2][-1:] in '.?!,' or p[3] != cur[-1][3]): grupos.append(cur); cur = []
        cur.append(p)
    if cur: grupos.append(cur)
    estilo_ass = (f'Style: P,Montserrat Black,70,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,3,0,1,5,2,2,90,90,{1920 - y},1\n\n' if estilo == 'dj' else
                  f'Style: P,Nunito Black,92,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,100,100,0,0,1,7,4,2,60,60,{1920 - y},1\n\n')
    cab = ('[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\n'
           'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n'
           + estilo_ass + '[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')
    lin = []
    for k, g in enumerate(grupos):
        s = g[0][0]; e = max(g[-1][1], s + 0.35)
        if k + 1 < len(grupos): e = min(e, grupos[k + 1][0][0])
        base = '{\\c&H' + g[0][3][-6:] + '&}'
        if estilo == 'dj':   # um evento por palavra: bloco na cor da pessoa, palavra falada em azul
            for j, x in enumerate(g):
                fp = g[j + 1][0] if j + 1 < len(g) else e
                t = base + ' '.join(('{\\c&HFF9A1E&}' + y_[2] + base) if i == j else y_[2] for i, y_ in enumerate(g))
                if fp - x[0] > 0.04: lin.append(f'Dialogue: 0,{_ts(x[0])},{_ts(fp)},P,,0,0,0,,{t}')
            continue
        txt = ' '.join(x[2] for x in g).strip(' ,.')
        if e - s > 0.04 and txt:
            lin.append(f'Dialogue: 0,{_ts(s)},{_ts(e)},P,,0,0,0,,{{\\fscx70\\fscy70\\t(0,90,\\fscx106\\fscy106)\\t(90,150,\\fscx100\\fscy100)}}{base}{txt}')
    open(arq, 'w', encoding='utf-8').write(cab + '\n'.join(lin) + '\n')

def marcas_pause(palavras, trechos, total):
    """zooms e SFX no tempo do vídeo editado: reação/risada = zoom 1,22 com estalo; buraco > 9 s = empurrão leve 1,1."""
    def ed(t):
        acc = 0.0
        for a, b in trechos:
            if a <= t <= b: return acc + t - a
            acc += b - a
    zooms, sfx, ult = [], [], -99
    for p in palavras:
        pa, pb, w = p[0], p[1], p[2]
        lw = re.sub(r'[^\w*]', '', w.lower()); t = ed(pa)
        if t is None: continue
        if RISO.match(lw):
            if all(abs(t - s['t']) > 3 for s in sfx if s['som'] == 'bonk'): sfx.append({'t': ed(pb) or t, 'som': 'bonk', 'db': -10})
            if t - ult > 5: zooms.append((t, 1.4, 0.22)); ult = t
        elif REACAO.match(lw) and t - ult > 5:
            zooms.append((t, 1.3, 0.18)); ult = t
    marcos = [0] + [z[0] for z in zooms] + [total]
    for a, b in zip(marcos, marcos[1:]):
        while b - a > 9: a += 6; zooms.append((a, 1.6, 0.10))
    zooms.sort()
    for t, d, amp in zooms: sfx.append({'t': max(0, t - 0.12), 'som': 'whoosh', 'db': -15 if amp > 0.15 else -19})
    return zooms, sorted(sfx, key=lambda s: s['t'])

def expr_zoom(zooms):
    """1 + soma de pulsos: entra num estalo (0,12 s, ease-out cúbico), segura, sai em 0,18 s."""
    p = []
    for a, d, amp in zooms:
        b = a + d
        p.append(f"{amp}*if(between(t,{a:.3f},{a + 0.12:.3f}),1-pow(1-(t-{a:.3f})/0.12,3),if(between(t,{a + 0.12:.3f},{b:.3f}),1,"
                 f"if(between(t,{b:.3f},{b + 0.18:.3f}),pow(1-(t-{b:.3f})/0.18,3),0)))")
    return '(1+' + '+'.join(p) + ')' if p else '1'

def ajusta_volume(arq, alvo=-14.0):
    """alvo: -16 a -12 LUFS e pico abaixo de -1: mede o vídeo pronto e corrige só o áudio (imagem copiada)."""
    o = subprocess.run(['ffmpeg', '-i', arq, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    I = re.findall(r'I:\s+(-?[\d.]+) LUFS', o); TP = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', o)
    if not I or (-16 <= float(I[-1]) <= -12 and (not TP or float(TP[-1]) <= -1.0)): return float(I[-1]) if I else None
    ganho = alvo - float(I[-1]) if not -16 <= float(I[-1]) <= -12 else 0.0; tmp = arq[:-4] + '_vol.mp4'
    r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', arq, '-c:v', 'copy', '-af', f'volume={ganho:.2f}dB,alimiter=limit=0.7:level=false',
                        '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', tmp])
    if r.returncode == 0: os.replace(tmp, arq)
    return alvo

def rms_10ms(src):
    """RMS em dB por janela de 10 ms do áudio do trecho (mono 16 kHz)."""
    tmp = tempfile.mktemp(suffix='.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vn', '-ac', '1', '-ar', '16000', tmp], check=True)
    with wave.open(tmp) as w: x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    os.remove(tmp)
    n = len(x) // 160
    return 20 * np.log10(np.sqrt((x[:n * 160].reshape(n, 160) ** 2).mean(1)) + 1e-6)

def vale(r, t0, t1):
    """ponto de menor volume entre t0 e t1 (segundos)."""
    i0, i1 = max(0, int(t0 * 100)), min(len(r), max(int(t0 * 100) + 1, int(t1 * 100)))
    return (i0 + int(np.argmin(r[i0:i1]))) / 100 if i1 > i0 else t0

def manchete_png(l1, l2, saida, larg_max=1000, track=-0.035):
    """faixa vermelha #E3101A do tamanho do texto; linha 1 branca, linha 2 amarela; letras apertadas."""
    from PIL import Image, ImageDraw, ImageFont
    fonte_arq = FONTE_ARQ
    def larg(f, t, tr): return sum(f.getlength(c) for c in t) + tr * (len(t) - 1)
    tam = 78
    while tam > 30:
        f = ImageFont.truetype(fonte_arq, tam); tr = track * tam
        if max(larg(f, l1, tr), larg(f, l2, tr)) + 2 * 26 <= larg_max: break
        tam -= 2
    sw = max(3, round(tam * 0.06)); px, py = 26, 12
    asc, desc = f.getmetrics(); alt_letra = f.getbbox('A')[3] - f.getbbox('A')[1]
    entre = round(alt_letra * 1.12)  # topo da linha 2 colado na linha 1
    W = int(max(larg(f, l1, tr), larg(f, l2, tr)) + 2 * px + 2 * sw); H = int(py * 2 + alt_letra + entre + 2 * sw)
    im = Image.new('RGBA', (W, H), (0xE3, 0x10, 0x1A, 255)); d = ImageDraw.Draw(im)
    topo = f.getbbox('A')[1]
    for i, (t, cor) in enumerate(((l1, (255, 255, 255)), (l2, (255, 230, 0)))):
        x = (W - larg(f, t, tr)) / 2; y = py + sw + i * entre - topo
        for c in t:
            d.text((x + 3, y + 3), c, font=f, fill=(0, 0, 0, 190))
            d.text((x, y), c, font=f, fill=cor, stroke_width=sw, stroke_fill=(0, 0, 0))
            x += f.getlength(c) + tr
    im.save(saida); return W, H

def editar(src, palavras, saida, base_vf, manchete=None, y_leg=1250, y_box=330, inicio=0.0, fim=None, max_dur=80,
           cor_ativa='&H0000E6FF', junta=0.45, zooms=(1.0, 1.12), leg_palavras=None, bips=(), tag=None,
           tag_box=(57, 954, 966), tag_alpha=0.44, congela=0.8, card=CARD, card_dur=2.0, chamada=('', ''), cx_turnos=None, crop_pad='(iw-ih*0.92*9/16)/2', meia=1080 * 0.92 * 9 / 32, leg_estilo='branca', pause=False, serif=None, musica=MUSICA, zoom_estalo=True, sons_cinema=False):
    # serif: texto serifado limpo no começo; card=None: sem fecho de marca; musica=None: sem música;
    # zoom_estalo=False: só o empurrão lento (clipe de história); sons_cinema: só whoosh grave, nada de som de meme
    # cx_turnos: [(t0, t1, cx)] no tempo do src (enquadra.turnos): a janela 9:16 segue quem fala; troca = corte seco
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout.strip() or 0)
    fim = min(fim or dur, dur)
    # marca e card vêm pelo nome: o arquivo mora na pasta de assets do cliente
    if card and not os.path.isabs(card): card = os.path.join(ASSETS, card)
    if tag and not os.path.isabs(tag): tag = os.path.join(ASSETS, tag)
    pal = [p for p in palavras if inicio <= p[0] and p[1] <= fim + 0.05]  # palavra que passa do fim não entra pela metade
    trechos = [[max(t[0], inicio), t[1]] for t in falas(pal, fim, junta=junta)]  # a folga antes da 1ª palavra não derruba o trecho
    total = sum(b - a for a, b in trechos)
    while total > max_dur and len(trechos) > 2: trechos.pop(len(trechos) // 2); total = sum(b - a for a, b in trechos)
    # corte no vale: a borda anda até o ponto mais baixo da folga (nunca entra na palavra)
    r = rms_10ms(src); relat = []
    for t in trechos:
        w_in = [p for p in pal if t[0] <= p[0] < t[1]]
        p0 = w_in[0][0] if w_in else t[0]; p1 = w_in[-1][1] if w_in else t[1]
        # janela do vale: do fim da palavra vizinha (fora do trecho) até a palavra do trecho, com no máximo 0,4 s
        ant = max([p[1] for p in palavras if p[1] <= p0 + 0.01] or [p0 - 0.4])
        prox = min([p[0] for p in palavras if p[0] >= p1 - 0.01] or [p1 + 0.4])
        # o Whisper marca início e fim de palavra com até 0,2 s de erro: a busca entra 0,15 a 0,2 s na palavra marcada
        t[0] = vale(r, max(ant - 0.05, p0 - 0.4, 0), p0 + 0.15)
        t[1] = vale(r, p1 - 0.2, max(p1 - 0.1, min(prox + 0.05, p1 + 0.4)))
        relat.append((t[0], float(r[min(len(r) - 1, int(t[0] * 100))]), t[1], float(r[min(len(r) - 1, int(t[1] * 100))])))
    lp = [p for p in (leg_palavras if leg_palavras is not None else pal) if inicio <= p[0] < fim]
    tmp = tempfile.mkdtemp(prefix='ed4_'); ass = os.path.join(tmp, 'leg.ass'); (legenda_pause(lp, trechos, ass, y_leg, 'dj' if leg_estilo == 'dj' else 'pause') if pause else legenda_branca(lp, trechos, ass, y_leg) if leg_estilo == 'branca' else legenda_ass(lp, trechos, ass, y_leg, cor_ativa))
    import shutil; shutil.copy(ass, saida[:-4] + '.ass')   # a legenda vai junto do vídeo
    rot, acc, bipo, vlab, alab = [], 0.0, [], [], []
    for i, (a, b) in enumerate(trechos):
        d = b - a; z0 = zooms[i % len(zooms)]
        # empurrão lento e contínuo (3% a cada 10 s, no máximo 6%), sempre no centro: nada de salto dentro da fala
        zf = f"{z0}*(1+min(0.06,0.003*t))"
        mut = [(max(a, x0 - 0.02) - a, min(b, x1 + 0.02) - a) for x0, x1 in bips if x1 > a and x0 < b]
        mute = (",volume=0:enable='" + '+'.join(f'between(t,{m0:.3f},{m1:.3f})' for m0, m1 in mut) + "'") if mut else ''
        for x0, x1 in bips:
            if a <= x0 < b: bipo.append((acc + x0 - a, max(0.12, x1 - x0 + 0.04)))
        # pedaços de vídeo: um por janela de quem fala dentro do trecho
        sub = [(max(a, t0), min(b, t1), cx) for t0, t1, cx in (cx_turnos or [(a, b, None)]) if t1 > a and t0 < b] or [(a, b, None)]
        sub[0] = (a, sub[0][1], sub[0][2]); sub[-1] = (sub[-1][0], b, sub[-1][2])
        for j, (s0, s1, cx) in enumerate(sub):
            if s1 - s0 < 0.04: continue
            bv = base_vf if cx is None else base_vf.replace(crop_pad, f"{max(0, cx - meia):.0f}")
            # o empurrão continua do ponto em que estava (tempo do trecho, não do pedaço)
            bv = bv.replace('#', f'{i}_{j}')   # rótulos únicos quando o layout tem split (câmera + jogo)
            zj = zf.replace('*t)', f'*(t+{s0 - a:.3f}))')
            rot.append(f"[0:v]trim={s0:.3f}:{s1:.3f},setpts=PTS-STARTPTS,{bv},scale=w='trunc(1080*{zj}/2)*2':h='trunc(1920*{zj}/2)*2':eval=frame,"
                       f"crop=1080:1920:(iw-1080)/2:(ih-1920)/2,setsar=1,fps=30[v{i}_{j}];")
            vlab.append(f'[v{i}_{j}]')
        rot.append(f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st={max(0, d - 0.03):.3f}:d=0.03{mute}[a{i}];")
        alab.append(f'[a{i}]')
        acc += d
    n = len(trechos)
    fg = ''.join(rot) + ''.join(vlab) + f'concat=n={len(vlab)}:v=1:a=0[vc];' + ''.join(alab) + f'concat=n={n}:v=0:a=1[ac];'
    vf = "[vc]eq=contrast=1.05,unsharp=5:5:0.5"
    zp, sp = marcas_pause(pal, trechos, acc) if pause else ([], [])
    sp = [x for x in sp if os.path.exists(SONS[x['som']])]   # som que não veio no pacote do cliente fica de fora
    if musica and not os.path.exists(musica): musica = None
    if not zoom_estalo: zp = []; sp = [x for x in sp if x['som'] == 'bonk']
    if sons_cinema: sp = []
    if zp:
        Z = expr_zoom(zp)
        vf = f"[vc]scale=w='trunc(1080*{Z}/2)*2':h='trunc(1920*{Z}/2)*2':eval=frame,crop=1080:1920:(iw-1080)/2:(ih-1920)/2,setsar=1,eq=contrast=1.05,unsharp=5:5:0.5"
    if manchete:
        # capa: faixa vermelha na largura do texto, letra pesada colada,
        # duas linhas quase encostadas, traço preto (PNG feito no PIL: o drawtext não aperta o espaçamento)
        png = os.path.join(tmp, 'manchete.png'); mw, mh = manchete_png(manchete[0], manchete[1], png)
        vf += ("[vm];movie='" + png.replace(chr(92), '/').replace(':', chr(92) + ':') + "'[mc];"
               f"[vm][mc]overlay=(W-{mw})/2:{y_box}:enable='lt(t,3.2)'")
    if tag:
        # PNG quadrado inteiro, escalado e posicionado (base do PNG = base do vídeo)
        tx, ty, tw = tag_box
        vf += ("[vt];movie='" + tag.replace(chr(92), '/').replace(':', chr(92) + ':') + f"',scale={tw}:{tw},format=rgba,"
               f"colorchannelmixer=aa={tag_alpha}[tg];[vt][tg]overlay={tx}:{ty}")
    if serif:
        sf = next((p for p in (os.environ.get('EDITOR_SERIF'), 'C:/Windows/Fonts/georgiab.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf') if p and os.path.exists(p)), FONTE_ARQ).replace(chr(92), '/').replace(':', chr(92) + ':')
        vf += f",drawtext=fontfile='{sf}':text='{serif}':fontcolor=white:fontsize=58:x=80:y=380:shadowcolor=black@0.6:shadowx=3:shadowy=3:enable='lt(t,3.2)':alpha='if(lt(t,0.3),t/0.3,if(gt(t,2.9),(3.2-t)/0.3,1))'"
    vf += f",subtitles='{ass.replace(chr(92), '/').replace(':', chr(92) + ':')}':fontsdir='{FONTES_DIR}'"
    # respiro: a última imagem segura parada enquanto o som abaixa
    if not card: card_dur = 0.25
    vf += f",tpad=stop_mode=clone:stop_duration={congela},fps=30,settb=1/30,format=yuv420p" + ('[vmain];' if card else '[vo];')
    ins = ['-i', src] + (['-loop', '1', '-framerate', '30', '-t', f'{card_dur + 0.3:.2f}', '-i', card] if card else [])
    c1, c2 = [(x or ' ').replace("'", '').replace(':', ' ') for x in chamada]
    if card: vf += (f"[1:v]scale=1080:1920,setsar=1,fps=30,scale=w='trunc(1080*(1+0.02*t)/2)*2':h='trunc(1920*(1+0.02*t)/2)*2':eval=frame,crop=1080:1920,"
           f"drawtext=fontfile='{FONTE}':text='{c1}':fontcolor=white:fontsize=64:expansion=none:x=(w-text_w)/2:y=1230:borderw=8:bordercolor=black,"
           f"drawtext=fontfile='{FONTE}':text='{c2}':fontcolor=0xFFE600:fontsize=72:expansion=none:x=(w-text_w)/2:y=1320:borderw=8:bordercolor=black,fps=30,settb=1/30,format=yuv420p[vcard];"
           f"[vmain][vcard]xfade=transition=fade:duration=0.25:offset={acc + congela - 0.25:.3f},trim=0:{acc + congela - 0.25 + card_dur:.3f}[vo];")
    afx = f"[ac]loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.75:attack=0.1:release=30:level=false,afade=t=out:st={max(0, acc - 0.25):.3f}:d=0.25[voz]"
    if bipo:
        bs = ''.join(f"sine=frequency=1000:sample_rate=48000:duration={d:.3f},volume=-26dB,afade=t=in:d=0.01,afade=t=out:st={d - 0.01:.3f}:d=0.01,aformat=channel_layouts=stereo,adelay={int(t * 1000)}|{int(t * 1000)}[bp{j}];" for j, (t, d) in enumerate(bipo))
        afx = afx.replace('[voz]', '[voz0]', 1) + ';' + bs + '[voz0]' + ''.join(f'[bp{j}]' for j in range(len(bipo))) + f'amix=inputs={len(bipo) + 1}:normalize=0:duration=first[voz]'
    if pause:
        esc = lambda p: p.replace(chr(92), '/').replace(':', chr(92) + ':')
        fmt = 'aresample=48000,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo'
        ps = ''.join(f"amovie='{esc(SONS[x['som']])}',{fmt},volume={x['db']}dB,adelay={int(x['t'] * 1000)}|{int(x['t'] * 1000)}[sx{j}];" for j, x in enumerate(sp))
        if musica:
            ps += f"amovie='{esc(musica)}',{fmt},atrim=0:{acc + congela:.3f},volume=-24dB,afade=t=out:st={max(0, acc - 0.5):.3f}:d=0.6[mu0];"
            afx += ';' + ps + f'[voz]{fmt},asplit=2[vz1][vz2];[mu0][vz2]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[mu];' + '[vz1]' + ''.join(f'[sx{j}]' for j in range(len(sp))) + f'[mu]amix=inputs={len(sp) + 2}:normalize=0:duration=first[vozp]'
        else:
            afx += ';' + ps + f'[voz]{fmt}[vz1];' + '[vz1]' + ''.join(f'[sx{j}]' for j in range(len(sp))) + f'amix=inputs={len(sp) + 1}:normalize=0:duration=first[vozp]'
        afx += f";[vozp]apad=whole_dur={acc + congela - 0.25 + card_dur:.3f}[ao]"
    else:
        afx += f";[voz]apad=whole_dur={acc + congela - 0.25 + card_dur:.3f}[ao]"
    cmd = ['ffmpeg', '-v', 'error', '-y', *ENTRADA, *ins, '-filter_complex', fg + vf + afx, '-map', '[vo]', '-map', '[ao]',
           *VCODEC, '-r', '30',
           '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', '-shortest', saida]
    open(os.path.join(tmp, 'cmd.txt'), 'w', encoding='utf-8').write(chr(10).join(cmd))
    rr = subprocess.run(cmd, capture_output=True, text=True)
    if rr.returncode: print('comando em', os.path.join(tmp, 'cmd.txt'))
    else: ajusta_volume(saida)
    return rr.returncode == 0, (rr.stderr[-3000:] if rr.returncode else f'{n} cortes, {acc:.1f} s de fala + {congela} s congelado + card {card_dur} s' + (f' | pause: {len(zp)} zooms, {len(sp)} sfx' if pause else '')), relat, trechos
