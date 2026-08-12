"""
Ponto de entrada alternativo para rodar o servidor.

Existe porque, no Windows, chamar `uvicorn app.main:app` (ou mesmo
`python -m uvicorn app.main:app`) às vezes falha com
`ModuleNotFoundError: No module named 'app'` — o processo do uvicorn não
adiciona a pasta do projeto ao sys.path do jeito esperado. Rodando este
arquivo com `python run.py`, o Python já garante que a pasta do projeto
(onde este arquivo está) entra no sys.path, então o import de `app.main`
funciona sem problema.
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
