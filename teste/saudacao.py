"""Confere o filtro de saudação da ponte do Telegram: saudação responde na hora, pedido de verdade vai para a fila."""
import importlib.util, os, sys

spec = importlib.util.spec_from_file_location('ponte', os.path.join(os.path.dirname(__file__), '..', 'nuvem', 'telegram.py'))
ponte = importlib.util.module_from_spec(spec); spec.loader.exec_module(ponte)
CASOS = {'oi': True, 'Oi!': True, 'bom dia': True, 'boa noite jarvis': True, 'teste': True, 'e aí': True,
         'faz um vídeo do cliente': False, 'oi, me manda os leads de hoje': False, 'bom dia, quero o plano': False}
ruim = [t for t, esperado in CASOS.items() if bool(ponte.SAUDACAO.match(t)) != esperado]
print('falhou em: ' + ', '.join(ruim) if ruim else f'{len(CASOS)} casos certos')
sys.exit(1 if ruim else 0)
