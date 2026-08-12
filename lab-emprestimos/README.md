# Trabalho 1 - Sistema de Empréstimo de Equipamentos

**Disciplina:** Engenharia de Software
**Turma:** S6 - Engenharia da Computação

**Dupla:**
- Pablo Santiago de Araujo Rodrigues
- Gustavo Monteiro Lopes

## 📌 Sobre o Projeto

Este repositório contém a implementação do "Trabalho 1 - Construir a
partir de um pedido incompleto". O objetivo do projeto é desenvolver um
sistema para controlar o empréstimo de equipamentos de um laboratório,
partindo de um levantamento de requisitos inicial de apenas cinco
linhas, intencionalmente ambíguo e sem a possibilidade de consultar o
cliente.

Como parte central da avaliação, as lacunas do pedido original foram
resolvidas através de decisões arquiteturais e de regras de negócio
assumidas pela equipe. Toda a documentação dessas escolhas, juntamente
com os critérios de aceite e a declaração de uso de IA, encontra-se
detalhada no arquivo [`DECISOES.md`](./DECISOES.md).

O escopo mínimo implementado garante que o sistema:

- Registre empréstimos e devoluções de equipamentos.
- Controle quem está com qual equipamento.
- Bloqueie novos empréstimos para alunos com pendências.
- Gere um relatório de atrasos para o técnico do laboratório.

## 🛠️ Stack

- Python 3.10+
- FastAPI + Uvicorn (API e servidor web)
- SQLite (arquivo local `app/laboratorio.db`, criado automaticamente)
- Jinja2 (telas HTML simples para o técnico)

Sem dependências externas de banco de dados: o arquivo `.db` é criado
sozinho na primeira execução — nada para instalar ou configurar além do
Python.

## 🚀 Como Executar o Projeto

### Pré-requisitos

- Python 3.10 ou superior instalado na máquina.
  Verifique com `python3 --version` (Linux/macOS) ou `python --version`
  (Windows). Se não tiver, baixe em
  https://www.python.org/downloads/ — no instalador do Windows, marque
  a opção **"Add python.exe to PATH"**.
- Git instalado, para clonar o repositório.

Não é necessário instalar nenhum banco de dados separado.

### Passos para execução

1. Clone este repositório:
   ```bash
   git clone <url-do-seu-repositorio>
   cd lab-emprestimos
   ```
2. Crie um ambiente virtual:
   ```bash
   python3 -m venv .venv          # Windows: python -m venv .venv
   ```
3. Ative o ambiente virtual:
   ```bash
   source .venv/bin/activate      # Linux/macOS
   .venv\Scripts\Activate.ps1     # Windows (PowerShell)
   ```
4. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
5. Rode o servidor:
   ```bash
   uvicorn app.main:app --reload   # Linux/macOS
   python run.py                   # Windows (ver observação abaixo)
   ```
   O terminal deve mostrar algo como:
   ```
   Uvicorn running on http://127.0.0.1:8000
   ```
6. Abra **http://localhost:8000** no navegador. É a interface do
   técnico (cadastrar aluno, cadastrar equipamento, registrar
   empréstimo, registrar devolução, ver relatório de atrasos).
   Para parar o servidor, pressione `Ctrl+C` no terminal.

> **Por que `python run.py` no Windows, e não `uvicorn app.main:app --reload`?**
> No Windows, chamar o `uvicorn` diretamente (com ou sem `--reload`, com
> ou sem `python -m`) às vezes falha com
> `ModuleNotFoundError: No module named 'app'` — um problema conhecido
> de como o uvicorn resolve o caminho do projeto nesse sistema. O
> arquivo `run.py` (na raiz do repositório) evita isso rodando o
> servidor por dentro de um script Python comum. A diferença prática é
> que ele não recarrega sozinho quando você edita o código — depois de
> alterar algo, pare com `Ctrl+C` e rode `python run.py` de novo.

### Solução de problemas comuns

- **`python3: command not found` (Windows)** → use `python` no lugar de
  `python3`. Se nem `python` funcionar e aparecer uma mensagem sobre
  Microsoft Store, tente `py -m venv .venv`, ou instale o Python de
  verdade em https://www.python.org/downloads/.
- **`.venv\Scripts\Activate.ps1` não é reconhecido / execução de
  scripts desabilitada (PowerShell)** → rode antes:
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, depois
  tente ativar de novo.
- **`ModuleNotFoundError: No module named 'app'` ao rodar `uvicorn`
  (Windows)** → use `python run.py` no lugar de `uvicorn app.main:app`
  (ver observação acima).
- **`pip install` não encontra `requirements.txt`** → o terminal não
  está na pasta certa. Rode `dir` (Windows) ou `ls` (Linux/macOS) para
  conferir, e `cd lab-emprestimos` se precisar entrar mais um nível
  (comum quando o zip extrai uma subpasta duplicada).
- **Erro `port already in use`** → outro processo já está usando a
  porta 8000; rode `uvicorn app.main:app --reload --port 8001` (ou edite
  a porta em `run.py`) e acesse http://localhost:8001.
- **Quiser recomeçar do zero (banco limpo)** → apague o arquivo
  `app/laboratorio.db` (ele é recriado automaticamente na próxima
  execução).

## 🖥️ Telas disponíveis

| Rota | Descrição |
|---|---|
| `/` | Página inicial |
| `/alunos` | Cadastro e listagem de alunos |
| `/equipamentos` | Cadastro e listagem de equipamentos |
| `/emprestimos` | Registro de empréstimos e devoluções |
| `/atrasados` | Relatório de atrasos |

## 🔌 API (usada para os critérios de aceite)

Todas as telas acima são uma casca sobre esta API JSON:

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/alunos` (form: `matricula`, `nome`) | Cadastra aluno |
| `GET` | `/api/alunos` | Lista alunos |
| `POST` | `/api/equipamentos` (form: `patrimonio`, `nome`) | Cadastra equipamento |
| `GET` | `/api/equipamentos` | Lista equipamentos |
| `POST` | `/api/emprestimos` (form: `matricula`, `patrimonio`) | Registra empréstimo — `201` em caso de sucesso |
| `POST` | `/api/emprestimos/{id}/devolucao` | Registra devolução |
| `GET` | `/api/emprestimos/atrasados` | Relatório de atrasos (só ativos e vencidos) |
| `GET` | `/api/emprestimos/ativos` | O que está emprestado agora e para quem |

### Códigos de erro retornados no corpo (JSON `codigo`)

- `409 PENDENCIA` — aluno tem equipamento com devolução vencida
- `409 EQUIPAMENTO_INDISPONIVEL` — equipamento já está emprestado
- `409 JA_DEVOLVIDO` — tentativa de devolver um empréstimo já devolvido
- `404 ALUNO_NAO_ENCONTRADO` / `404 EQUIPAMENTO_NAO_ENCONTRADO` / `404 EMPRESTIMO_NAO_ENCONTRADO`
- `409 MATRICULA_DUPLICADA` / `409 PATRIMONIO_DUPLICADO`

### Exemplo rápido via curl

```bash
curl -X POST localhost:8000/api/alunos -F matricula=2023001 -F nome="Ana Silva"
curl -X POST localhost:8000/api/equipamentos -F patrimonio=MULT-01 -F nome="Multímetro"
curl -X POST localhost:8000/api/emprestimos -F matricula=2023001 -F patrimonio=MULT-01
curl -X POST localhost:8000/api/emprestimos/1/devolucao
curl localhost:8000/api/emprestimos/atrasados
```

### Testando a regra de pendência (sem esperar 48h)

O prazo de devolução é sempre calculado como *agora + 48h* pela própria
API, então não existe uma chamada legítima que produza um atraso
instantâneo — é a regra de negócio funcionando como esperado. Para
simular esse cenário em teste, escreva direto no banco SQLite por fora
da API (com o servidor ainda rodando, em outro terminal):

```bash
python -c "
import sqlite3
from datetime import datetime, timedelta
conn = sqlite3.connect('app/laboratorio.db')
aluno_id = conn.execute(\"SELECT id FROM alunos WHERE matricula='2023001'\").fetchone()[0]
equip_id = conn.execute(\"SELECT id FROM equipamentos WHERE patrimonio='MULT-01'\").fetchone()[0]
passado = datetime.now() - timedelta(days=1)
conn.execute('UPDATE equipamentos SET disponivel=0 WHERE id=?', (equip_id,))
conn.execute('INSERT INTO emprestimos (aluno_id, equipamento_id, data_emprestimo, data_devolucao_prevista, data_devolucao) VALUES (?, ?, ?, ?, NULL)', (aluno_id, equip_id, (passado - timedelta(hours=48)).isoformat(), passado.isoformat()))
conn.commit()
print('empréstimo vencido criado')
"
curl localhost:8000/api/emprestimos/atrasados
```

## 📂 Estrutura do projeto

```
lab-emprestimos/
├── app/
│   ├── main.py          # rotas da API e das telas HTML
│   ├── db.py             # conexão e criação das tabelas SQLite
│   ├── laboratorio.db    # banco de dados (criado automaticamente)
│   └── templates/        # telas HTML (Jinja2)
├── run.py                # ponto de entrada alternativo (Windows)
├── requirements.txt
├── README.md
└── DECISOES.md
```

## 👥 Equipe

Pablo Santiago de Araujo Rodrigues e Gustavo Monteiro Lopes
