import sys

if "--janela" in sys.argv:
    from .interface import iniciar

    iniciar()
    sys.exit(0)

from .main import main

sys.exit(main())
