# Quem fala: impressão da voz por frase com o modelo ECAPA (SpeechBrain, spkrec-ecapa-voxceleb, CPU) e agrupamento
# por semelhança (cosseno). O grupo com mais tempo de fala é o PRINCIPAL; os outros ganham cor própria,
# sempre a mesma para a mesma voz. Frase curta demais (< 0,6 s) herda a voz da frase anterior.
# Uso: falantes(wav, [(s, e), ...]) -> lista de índices (0 = principal, 1, 2, 3...)
import os, sys
import numpy as np

CORES_ASS = ['&H00FFFFFF', '&H0000E6FF', '&H0066FF66', '&H006E6EFF']   # branco, amarelo, verde, vermelho claro (BGR do ASS)
MODELO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modelos', 'ecapa')
_enc = None

def _encoder():
    global _enc
    if _enc is None:
        import torch; torch.set_num_threads(4)
        from speechbrain.inference.speaker import EncoderClassifier
        from speechbrain.utils.fetching import LocalStrategy
        _enc = EncoderClassifier.from_hparams(source='speechbrain/spkrec-ecapa-voxceleb', savedir=MODELO,
                                              run_opts={'device': 'cpu'}, local_strategy=LocalStrategy.COPY)
    return _enc

def falantes(wav, segs, max_vozes=4, limiar=0.55):
    import librosa, torch
    from sklearn.cluster import AgglomerativeClustering
    y, sr = librosa.load(wav, sr=16000, mono=True)
    enc = _encoder(); emb, ok = [], []
    for s, e in segs:
        a, b = int(max(0, s) * sr), int(e * sr)
        if b - a >= int(0.6 * sr):
            with torch.no_grad(): v = enc.encode_batch(torch.tensor(y[a:b]).unsqueeze(0)).squeeze().numpy()
            emb.append(v / (np.linalg.norm(v) + 1e-9)); ok.append(True)
        else: emb.append(None); ok.append(False)
    idx = [i for i, k in enumerate(ok) if k]
    if len(idx) < 2: return [0] * len(segs)
    X = np.array([emb[i] for i in idx])
    # medido: mesma pessoa 0,40 a 0,52 de distância, pessoas diferentes 0,8 ou mais
    lab = AgglomerativeClustering(n_clusters=None, distance_threshold=limiar if limiar <= 0.7 else 0.6, metric='cosine', linkage='average').fit_predict(X)
    dur = {}
    for j, i in enumerate(idx): dur[lab[j]] = dur.get(lab[j], 0) + segs[i][1] - segs[i][0]
    # grupo pequeno (menos de 1,5 s de fala) ou além das 4 cores vai para a voz grande mais parecida
    grandes = [k for k in sorted(dur, key=lambda k: -dur[k]) if dur[k] >= 1.5][:max_vozes] or [max(dur, key=dur.get)]
    cent = {k: X[lab == k].mean(0) for k in set(lab)}
    perto = {k: (k if k in grandes else max(grandes, key=lambda g: float(cent[k] @ cent[g]))) for k in set(lab)}
    lab = np.array([perto[k] for k in lab])
    mapa = {k: n for n, k in enumerate(grandes)}
    out, ult = [], 0
    for i, k in enumerate(ok):
        if k: ult = mapa[lab[idx.index(i)]]
        out.append(ult)
    return out

def frases_por_pausa(segs_whisper, pausa=0.35):
    """parte as frases do Whisper onde há pausa entre palavras (uma frase pode ter duas pessoas)."""
    P = []
    for s in segs_whisper:
        cur = []
        for w in (s.get('w') or []):
            if cur and w[0] - cur[-1][1] > pausa: P.append(cur); cur = []
            cur.append(w)
        if cur: P.append(cur)
    return P

def vozes_wav(wav):
    """só as vozes (demucs htdemucs, 2 trilhas): música e barulho do jogo atrapalham a impressão da voz. Fica em cache."""
    import subprocess, shutil, tempfile
    out = wav[:-4] + '.vozes.wav'
    if os.path.exists(out): return out
    tmp = tempfile.mkdtemp(prefix='dmx_')
    try: import demucs  # noqa
    except ImportError: return wav                              # sem demucs instalado: usa o áudio cheio
    r = subprocess.run([sys.executable, '-m', 'demucs', '-n', 'htdemucs', '--two-stems', 'vocals', '-j', '1', '-o', tmp, wav], capture_output=True, text=True)
    achou = [os.path.join(d, f) for d, _, fs in os.walk(tmp) for f in fs if f == 'vocals.wav']
    if r.returncode or not achou: return wav                    # sem demucs: usa o áudio cheio
    shutil.move(achou[0], out); shutil.rmtree(tmp, ignore_errors=True); return out

def colorir(wav, segs_whisper, palavras):
    """palavras (a, b, w[, ...]) -> (a, b, w, cor) com a cor de quem falou. segs_whisper: frases com 'w' = [[s, e, palavra, p], ...]."""
    P = frases_por_pausa(segs_whisper)
    if not P: return [(p[0], p[1], p[2], CORES_ASS[0]) for p in palavras]
    lab = falantes(vozes_wav(wav), [(f[0][0], f[-1][1]) for f in P])
    spans = [(f[0][0] - 0.05, f[-1][1] + 0.05, l) for f, l in zip(P, lab)]
    out = []
    for p in palavras:
        l = next((x[2] for x in spans if x[0] <= p[0] <= x[1]), None)
        if l is None: l = min(spans, key=lambda x: abs(x[0] - p[0]))[2]
        out.append((p[0], p[1], p[2], CORES_ASS[min(l, len(CORES_ASS) - 1)]))
    return out
