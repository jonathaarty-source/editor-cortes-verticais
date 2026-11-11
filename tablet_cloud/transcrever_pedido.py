#!/usr/bin/env python3
"""Transcreve um audio curto (pedido de voz pro Jarvis) com faster-whisper local.
Uso: python transcrever_pedido.py audio.wav   -> escreve o texto no stdout."""
import sys

def main():
    caminho = sys.argv[1]
    from faster_whisper import WhisperModel
    modelo = WhisperModel('small', device='cpu', compute_type='int8')
    segs, _ = modelo.transcribe(caminho, language='pt', vad_filter=True)
    texto = ' '.join(s.text.strip() for s in segs).strip()
    print(texto)

if __name__ == '__main__':
    main()
