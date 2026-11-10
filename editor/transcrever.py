"""Transcreve um áudio com faster-whisper (CPU), palavras com tempo.
uso: python transcrever.py audio.wav saida.json [modelo] [threads]
Saída: lista de frases {"s", "e", "t", "lp", "w": [[ini, fim, palavra, confiança], ...]}"""
import json, sys


def transcrever(audio, out, modelo='small', threads=4, idioma='pt'):
    from faster_whisper import WhisperModel
    m = WhisperModel(modelo, device='cpu', compute_type='int8', cpu_threads=threads)
    segs, _ = m.transcribe(audio, language=idioma, vad_filter=True, vad_parameters={'min_silence_duration_ms': 400},
                           word_timestamps=True, beam_size=1, condition_on_previous_text=False)
    res = [{'s': round(s.start, 2), 'e': round(s.end, 2), 't': s.text.strip(), 'lp': round(s.avg_logprob, 2),
            'w': [[round(w.start, 2), round(w.end, 2), w.word, round(w.probability, 2)] for w in (s.words or [])]} for s in segs]
    json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
    return res


if __name__ == '__main__':
    r = transcrever(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 'small', int(sys.argv[4]) if len(sys.argv) > 4 else 4)
    print(len(r), 'frases')
