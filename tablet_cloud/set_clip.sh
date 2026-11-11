#!/data/data/com.termux/files/usr/bin/sh
# Gera a URI data: da página de espera e coloca na área de transferência (sem passar pelo teclado).
cd ~/tablet_cloud
curl -sL -o loading.html https://raw.githubusercontent.com/jonathaarty-source/editor-cortes-verticais/main/tablet_cloud/loading.html
python -c "
import base64
html = open('loading.html', encoding='utf-8').read()
b64 = base64.b64encode(html.encode()).decode()
print('DATA:TEXT/HTML;BASE64,' + b64, end='')
" > loading_uri.txt
termux-clipboard-set "$(cat loading_uri.txt)"
echo "copiado para a area de transferencia"
