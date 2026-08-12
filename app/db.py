"""
Camada de acesso ao banco de dados (SQLite puro, sem ORM).

Decisões relevantes (ver DECISOES.md para o detalhamento completo):
- Sem soft delete: nada de created_at/updated_at/deleted_at. O laboratório
  pediu simplicidade; auditoria formal não foi solicitada.
- Concorrência: o "empréstimo" de um equipamento é feito por um UPDATE
  condicional (WHERE disponivel = 1). Se duas requisições disputarem o
  mesmo equipamento, apenas uma altera uma linha; a outra recebe 0 linhas
  afetadas e é rejeitada. Isso, combinado com BEGIN IMMEDIATE (que serializa
  escritas no SQLite), evita que dois empréstimos simultâneos "vençam" o
  mesmo equipamento.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "laboratorio.db"

PRAZO_HORAS_DEVOLUCAO = 48


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, isolation_level=None, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS alunos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matricula TEXT NOT NULL UNIQUE,
                nome TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS equipamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patrimonio TEXT NOT NULL UNIQUE,
                nome TEXT NOT NULL,
                disponivel INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS emprestimos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aluno_id INTEGER NOT NULL REFERENCES alunos(id),
                equipamento_id INTEGER NOT NULL REFERENCES equipamentos(id),
                data_emprestimo TEXT NOT NULL,
                data_devolucao_prevista TEXT NOT NULL,
                data_devolucao TEXT
            );
            """
        )
    finally:
        conn.close()
