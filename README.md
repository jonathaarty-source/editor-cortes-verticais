# Editor de cortes verticais

Transforma um trecho de vídeo longo (live, gameplay, podcast) em um corte vertical 1080x1920:

- tira o silêncio e corta sempre no ponto mais baixo do áudio;
- legenda palavra por palavra, com consenso entre dois modelos de transcrição;
- palavrão vira bip leve no áudio e asterisco na legenda;
- manchete de duas linhas nos primeiros segundos;
- zoom em reação e risada, empurrão lento dentro da fala;
- opcional: cor da legenda por voz e janela 9:16 que segue quem fala.

## Uso

```bash
pip install -r requirements.txt
python editor/rodar.py pedido.json saida
```

O formato do pedido está no começo de `editor/rodar.py`. Há um exemplo em `teste/pedido.json`.

Marca, sons e música não fazem parte do repositório: a pasta deles é passada em `EDITOR_ASSETS`.

No Windows com placa AMD o render usa a placa (`h264_amf`); nos outros sistemas usa `libx264`.

## Fontes

Montserrat, Nunito e Poppins, todas sob a SIL Open Font License.
