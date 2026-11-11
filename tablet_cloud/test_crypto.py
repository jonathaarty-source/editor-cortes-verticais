try:
    import cryptography
    print('OK', cryptography.__version__)
except Exception as e:
    print('FALHOU', type(e).__name__, e)
