# EDITOR 3: corte dinâmico de vídeo longo para curto vertical.
#  1. tira o silêncio: mantém só onde há fala, emenda seca;
#  2. legenda palavra por palavra (karaokê), 1 a 3 palavras;
#  3. manchete de 2 linhas nos 3 primeiros segundos;
#  4. filtro leve (contraste e nitidez, sem saturar), áudio normalizado.
import os, subprocess, tempfile

# fontes instaladas só no usuário: o ffmpeg não acha sozinho, então ficam numa pasta própria (fontsdir)
AQUI = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.environ.get('EDITOR_ASSETS') or os.path.join(AQUI, 'assets')   # marca, sons e música de cada cliente ficam FORA do repositório
def esc(p): return p.replace(chr(92), '/').replace(':', chr(92) + ':')   # caminho dentro de filtro do ffmpeg
FONTES_ARQ = os.environ.get('EDITOR_FONTES') or os.path.join(AQUI, 'fontes')
FONTES_DIR = esc(FONTES_ARQ)
# placa de vídeo no Windows (AMD), CPU no resto (servidor)
GPU = os.name == 'nt' and not os.environ.get('EDITOR_CPU')
ENTRADA = ['-hwaccel', 'd3d11va'] if GPU else []
VCODEC = (['-c:v', 'h264_amf', '-profile:v', 'high', '-rc', 'cbr', '-b:v', '12M', '-maxrate', '12M', '-bufsize', '24M'] if GPU else
          ['-c:v', 'libx264', '-preset', os.environ.get('EDITOR_PRESET', 'veryfast'), '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-b:v', '12M', '-maxrate', '12M', '-bufsize', '24M'])
FONTE = FONTES_DIR + '/Montserrat-Black.ttf'
FONTE_ARQ = os.path.join(FONTES_ARQ, 'Montserrat-Black.ttf')
FONTE_ASS = 'Montserrat Black'
SFX_CORTE = os.path.join(ASSETS, 'sons', 'corte.mp3')

def ts(s): return f'0:{int(s // 60):02d}:{s % 60:05.2f}'

def falas(palavras, dur, folga=0.15, junta=0.45):
    """palavras: [(ini, fim, texto)] no tempo do vídeo -> trechos com fala [(ini, fim)]"""
    tr = []
    for a, b, _ in palavras:
        a, b = max(0, a - folga), min(dur, b + folga)
        if tr and a - tr[-1][1] <= junta: tr[-1][1] = max(tr[-1][1], b)
        else: tr.append([a, b])
    return [t for t in tr if t[1] - t[0] >= 0.35]

def legenda_ass(palavras, trechos, arq, y=1300, cor_ativa='&H0000E6FF', maiuscula=True, fonte=None, tam=70, largura=112):
    # remapeia o tempo de cada palavra para o vídeo já cortado
    novo, acc = [], 0.0
    for a, b in trechos:
        for pa, pb, w in palavras:
            if a <= pa < b: novo.append((acc + pa - a, acc + min(pb, b) - a, (w.upper() if maiuscula else w.lower()).strip('.,!?')))
        acc += b - a
    blocos, atual = [], []
    for p in novo:
        if atual and (len(atual) >= 3 or p[0] - atual[-1][1] > 0.5 or len(' '.join(x[2] for x in atual)) + len(p[2]) > 16): blocos.append(atual); atual = []
        atual.append(p)
    if atual: blocos.append(atual)
    # bloco relâmpago (menos de 0,4 s na tela) junta com o próximo: nada pisca ilegível
    k = 0
    while k < len(blocos) - 1:
        if blocos[k + 1][0][0] - blocos[k][0][0] < 0.4 and len(blocos[k]) + len(blocos[k + 1]) <= 4:
            blocos[k] = blocos[k] + blocos.pop(k + 1)
        else: k += 1
    cab = ('[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\n'
           'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n'
           f'Style: P,{fonte or FONTE_ASS},{tam},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,{largura},100,1,0,1,8,4,2,80,80,{1920 - y},1\n\n'
           '[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')
    lin = []
    for k, b in enumerate(blocos):
        fimb = min(blocos[k + 1][0][0] if k + 1 < len(blocos) else b[-1][1] + 0.3, b[-1][1] + 0.5)
        for j, (a, e, w) in enumerate(b):
            fp = b[j + 1][0] if j + 1 < len(b) else fimb
            txt = ' '.join((f'{{\\c{cor_ativa}}}' + x[2] + '{\\c&HFFFFFF&}') if i == j else x[2] for i, x in enumerate(b))
            if fp - a > 0.04: lin.append(f'Dialogue: 0,{ts(a)},{ts(fp)},P,,0,0,0,,{txt}')
    open(arq, 'w', encoding='utf-8').write(cab + '\n'.join(lin) + '\n')
    return acc

def editar(src, palavras, saida, base_vf, manchete=None, cartao=None, y_leg=1300, y_box=330, inicio=0.0, fim=None, max_dur=80, cor_ativa='&H0000E6FF',
           junta=0.45, zooms=(1.0, 1.22, 1.1, 1.3), leg=None, lay_janelas=None, leg_palavras=None, bips=(), respiro=1.0, tag=None):
    # base_vf pode ser uma lista de layouts (alterna a cada pedaço); '#' no filtro vira o número do pedaço (rótulos únicos)
    # junta: pausa máxima que fica dentro do trecho (gameplay usa maior: pausa com ação fica); leg: opções da legenda
    """src: vídeo; palavras no tempo do src; base_vf: filtro que leva o quadro a 1080x1920 (layout do cliente)."""
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout.strip() or 0)
    fim = min(fim or dur, dur)
    pal = [p for p in palavras if inicio <= p[0] < fim]
    trechos = [t for t in falas(pal, fim, junta=junta) if t[0] >= inicio]
    # corta para caber no máximo, mantendo o começo (gancho) e o final (desfecho)
    total = sum(b - a for a, b in trechos)
    while total > max_dur and len(trechos) > 2: trechos.pop(len(trechos) // 2); total = sum(b - a for a, b in trechos)
    if trechos and respiro: trechos[-1][1] = min(fim, trechos[-1][1] + respiro)  # segura depois da última frase
    lp = [p for p in (leg_palavras if leg_palavras is not None else pal) if inicio <= p[0] < fim]
    tmp = tempfile.mkdtemp(prefix='ed3_'); ass = os.path.join(tmp, 'leg.ass'); legenda_ass(lp, trechos, ass, y_leg, cor_ativa, **(leg or {}))
    # fala longa vira pedaços de ~2,8 s com enquadramento trocado (mudar algo a cada 2 a 3 s);
    # os pedaços são contínuos, então o áudio não pula
    pedacos = []
    for a, b in trechos:
        n_p = max(1, round((b - a) / 2.8))
        passo = (b - a) / n_p
        pedacos += [(a + k * passo, a + (k + 1) * passo, k == 0) for k in range(n_p)]
    ZOOMS = zooms
    LAY = base_vf if isinstance(base_vf, (list, tuple)) else [base_vf]
    rot, acc, cortes, prev_b, bipo = [], 0.0, [], None, []
    for i, (a, b, novo) in enumerate(pedacos):
        z = ZOOMS[i % len(ZOOMS)]; bv = LAY[i % len(LAY)]
        for j0, j1, lj in lay_janelas or []:  # layout fixo num trecho (ex.: webcam grande na risada)
            if j0 <= a < j1: bv = lj
        bv = bv.replace('#', str(i))
        fade = ',afade=t=in:d=0.02' if novo else ''
        fx, fy = ((0.5, 0.5), (0.35, 0.4), (0.65, 0.45), (0.5, 0.3))[i % 4]
        mut = [(max(a, x0 - 0.02) - a, min(b, x1 + 0.02) - a) for x0, x1 in bips if x1 > a and x0 < b]
        mute = (",volume=0:enable='" + '+'.join(f'between(t,{m0:.3f},{m1:.3f})' for m0, m1 in mut) + "'") if mut else ''
        for x0, x1 in bips:
            if a <= x0 < b: bipo.append((acc + x0 - a, max(0.12, x1 - x0 + 0.04)))
        rot.append(f"[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS,{bv},scale=iw*{z}:ih*{z},crop=1080:1920:(iw-1080)*{fx}:(ih-1920)*{fy},setsar=1[v{i}];[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS{fade}{mute}[a{i}];")
        if novo and prev_b is not None and a - prev_b > 1.2: cortes.append(acc)
        acc += b - a; prev_b = b
    n = len(pedacos)
    fg = ''.join(rot) + ''.join(f'[v{i}][a{i}]' for i in range(n)) + f'concat=n={n}:v=1:a=1[vc][ac];'
    vf = "[vc]eq=contrast=1.05,unsharp=5:5:0.5"
    if manchete:
        l1, l2 = manchete
        fs = min(60, int(940 / (0.78 * max(len(l1), len(l2), 1))))  # encolhe para caber na faixa
        vf += (f",drawbox=x=40:y={y_box}:w=1000:h=176:color=0xE3101A@1:t=fill:enable='lt(t,3.2)'"
               f",drawtext=fontfile='{FONTE}':text='{l1}':fontcolor=white:fontsize={fs}:x=(w-text_w)/2:y={y_box + 16}:shadowcolor=black@0.76:shadowx=3:shadowy=3:enable='lt(t,3.2)'"
               f",drawtext=fontfile='{FONTE}':text='{l2}':fontcolor=0xFFE600:fontsize={fs}:x=(w-text_w)/2:y={y_box + 92}:shadowcolor=black@0.76:shadowx=3:shadowy=3:enable='lt(t,3.2)'")
    if tag:
        vf = vf + "[vt];movie='" + tag.replace(chr(92), '/').replace(':', chr(92) + ':') + "',scale=520:-1,format=rgba,colorchannelmixer=aa=0.44[tg];[vt][tg]overlay=(W-w)/2:1440"
    vf += f",subtitles='{ass.replace(chr(92), '/').replace(':', chr(92) + ':')}':fontsdir='{FONTES_DIR}',format=yuv420p[vo];"
    ins = ['-i', src]
    if cartao and cortes:
        ins += ['-i', cartao]
        vf = vf.replace('[vo];', '[vm];') + "[1:v]scale=1080:1920,setsar=1,loop=loop=-1:size=8,setpts=N/30/TB[ct];[vm][ct]overlay=0:0:enable='" + '+'.join(f'between(t,{c:.2f},{c + 0.12:.2f})' for c in cortes) + "':shortest=1[vo];"
    # whoosh nas emendas maiores, por baixo da voz
    k = len(ins) // 2
    afx = f"[ac]loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.75:attack=0.1:release=30:level=false[voz]"
    if bipo:
        bs = ''.join(f"sine=frequency=1000:sample_rate=48000:duration={d:.3f},volume=-26dB,afade=t=in:d=0.01,afade=t=out:st={d - 0.01:.3f}:d=0.01,aformat=channel_layouts=stereo,adelay={int(t * 1000)}|{int(t * 1000)}[bp{j}];" for j, (t, d) in enumerate(bipo))
        afx = afx.replace('[voz]', '[voz0]', 1) + ';' + bs + '[voz0]' + ''.join(f'[bp{j}]' for j in range(len(bipo))) + f'amix=inputs={len(bipo) + 1}:normalize=0:duration=first[voz]'
    if cortes and os.path.exists(SFX_CORTE):
        ins += ['-i', SFX_CORTE]
        spl = f"[{k}:a]asplit={len(cortes)}" + ''.join(f'[r{j}]' for j in range(len(cortes))) + ';'
        sx = spl + ''.join(f"[r{j}]atrim=0:1.2,volume=0.35,adelay={int(c * 1000)}|{int(c * 1000)}[s{j}];" for j, c in enumerate(cortes))
        afx = afx + ';' + f"{sx}[voz]" + ''.join(f'[s{j}]' for j in range(len(cortes))) + f"amix=inputs={len(cortes) + 1}:normalize=0:duration=first[ao]"
    else:
        afx = afx.replace('[voz]', '[ao]')
    cmd = ['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', fg + vf + afx, '-map', '[vo]', '-map', '[ao]', *VCODEC, '-r', '30',
           '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', saida]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: open(os.path.join(tmp, 'cmd.txt'), 'w', encoding='utf-8').write(chr(10).join(cmd)); print('comando em', os.path.join(tmp, 'cmd.txt'), 'saída', r.returncode)
    return r.returncode == 0, (r.stderr[-3000:] if r.returncode else f'{len(trechos)} cortes, {n} planos, {acc:.0f} s, {len(cortes)} transições')
