#!/usr/bin/env bash
# Roda os pedidos do cofre (repositório privado) e devolve o resultado para lá.
# REGRA: nada de pedido, nome de arquivo ou erro vai para a tela (o registro deste repositório é público).
# Cofre:  video/fila/<id>.json  = pedidos esperando      video/assets/ = marca, sons e música
#         video/feitos/ e video/erros/ = pedidos já rodados
# Entrega: uma "release" no cofre por pedido, com o vídeo, a legenda, o relatório e o registro.
set -u
: "${COFRE_REPO:?}" "${COFRE_TOKEN:?}"
git clone -q --depth 1 "https://x-access-token:${COFRE_TOKEN}@github.com/${COFRE_REPO}.git" cofre > /dev/null 2>&1 || { echo "não abri o cofre"; exit 1; }
export EDITOR_ASSETS="$PWD/cofre/video/assets"
export GH_TOKEN="$COFRE_TOKEN"
n=0; ok=0
for p in cofre/video/fila/*.json; do
  [ -e "$p" ] || continue
  n=$((n + 1)); id=$(basename "$p" .json); out="saida/$n"; mkdir -p "$out"
  if python editor/rodar.py "$p" "$out" > "$out/registro.txt" 2>&1; then ok=$((ok + 1)); st=feitos; else st=erros; fi
  rm -f "$out"/fonte.* "$out"/transc_*.json
  gh release create "video-$id-$(date +%m%d-%H%M)" "$out"/* --repo "$COFRE_REPO" --title "Vídeo $id ($st)" --notes "Pedido $id: $st" > /dev/null 2>&1 || st=erros
  mkdir -p "cofre/video/$st"; git -C cofre mv -f "video/fila/$id.json" "video/$st/$id.json" > /dev/null 2>&1
  echo "pedido $n: $st"
done
if [ "$n" -gt 0 ]; then
  git -C cofre -c user.name="editor-nuvem" -c user.email="editor-nuvem@users.noreply.github.com" commit -q -m "vídeos da fila: $ok de $n prontos" > /dev/null 2>&1
  for i in 1 2 3; do git -C cofre pull -q --rebase > /dev/null 2>&1; git -C cofre push -q > /dev/null 2>&1 && break; sleep 5; done
fi
echo "pedidos: $n, prontos: $ok"
