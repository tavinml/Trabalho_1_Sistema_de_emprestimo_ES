# Controle de Empréstimo de Equipamentos do Laboratório

Sistema simples para o técnico registrar empréstimos e devoluções de
equipamentos, ver o que está emprestado e para quem, e consultar o
relatório de atrasos. As decisões de projeto e suas justificativas estão
em [`DECISOES.md`](./DECISOES.md).

## Stack

- Python 3.10+
- FastAPI + Uvicorn (API e servidor web)
- SQLite (arquivo local `app/laboratorio.db`, criado automaticamente)
- Jinja2 (telas HTML simples para o técnico)

Sem dependências externas de banco de dados: o arquivo `.db` é criado
sozinho na primeira execução.

## Como executar

```bash
# 1. Criar e ativar um ambiente virtual
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Rodar o servidor
uvicorn app.main:app --reload
```

Abra **http://localhost:8000** no navegador. É a interface do técnico
(cadastrar aluno, cadastrar equipamento, registrar empréstimo, registrar
devolução, ver relatório de atrasos).

Não é necessário nenhum passo extra de configuração de banco — o SQLite
já vem embutido no Python.

## API (usada para os critérios de aceite)

Todas as telas HTML acima são só uma casca sobre esta API JSON:

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/alunos` (form: `matricula`, `nome`) | Cadastra aluno |
| `GET`  | `/api/alunos` | Lista alunos |
| `POST` | `/api/equipamentos` (form: `patrimonio`, `nome`) | Cadastra equipamento |
| `GET`  | `/api/equipamentos` | Lista equipamentos |
| `POST` | `/api/emprestimos` (form: `matricula`, `patrimonio`) | Registra empréstimo — `201` em caso de sucesso |
| `POST` | `/api/emprestimos/{id}/devolucao` | Registra devolução |
| `GET`  | `/api/emprestimos/atrasados` | Relatório de atrasos (só ativos e vencidos) |
| `GET`  | `/api/emprestimos/ativos` | O que está emprestado agora e para quem |

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

## Equipe

Pablo Santiago de Araujo Rodrigues e Gustavo Monteiro Lopes
