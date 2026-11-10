#!/usr/bin/env bash
# Fonte de prova: 20 s de imagem de teste 1920x1080 com uma fala sintética em português.
set -e
mkdir -p saida
edge-tts --voice pt-BR-AntonioNeural --text "Olha só, esse é um vídeo de prova do editor. Ele corta o silêncio, coloca a legenda palavra por palavra e fecha no fim da frase. Se você está lendo isso na tela, nossa, funcionou." --write-media saida/voz.mp3
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 saida/voz.mp3)
ffmpeg -v error -y -f lavfi -i "testsrc2=size=1920x1080:rate=30:duration=$D" -i saida/voz.mp3 -c:v libx264 -preset veryfast -pix_fmt yuv420p -c:a aac -shortest saida/fonte_prova.mp4
