"""
Sistema de controle de empréstimo de equipamentos do laboratório.

Uso previsto (decisão assumida #6): só o técnico opera o sistema, em um
único computador do laboratório. Não há login/autenticação.

As regras de negócio implementadas aqui refletem exatamente as decisões
registradas em DECISOES.md. Não altere o comportamento sem atualizar
aquele arquivo também.
"""
from datetime import datetime, timedelta

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from . import db

app = FastAPI(title="Controle de Empréstimo de Equipamentos")
templates = Jinja2Templates(directory=str(__import__("pathlib").Path(__file__).parent / "templates"))


@app.on_event("startup")
def _startup() -> None:
    db.init_db()


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Regras de negócio (usadas tanto pela API JSON quanto pelas telas HTML)
# ---------------------------------------------------------------------------

def _buscar_aluno_por_matricula(conn, matricula: str):
    return conn.execute(
        "SELECT * FROM alunos WHERE matricula = ?", (matricula,)
    ).fetchone()


def _buscar_equipamento_por_patrimonio(conn, patrimonio: str):
    return conn.execute(
        "SELECT * FROM equipamentos WHERE patrimonio = ?", (patrimonio,)
    ).fetchone()


def _aluno_tem_pendencia(conn, aluno_id: int) -> bool:
    # Decisão assumida #2: pendência = equipamento com devolução vencida
    # (não simplesmente "possuir algo emprestado" dentro do prazo).
    row = conn.execute(
        """
        SELECT COUNT(*) AS total FROM emprestimos
        WHERE aluno_id = ?
          AND data_devolucao IS NULL
          AND data_devolucao_prevista < ?
        """,
        (aluno_id, _now_iso()),
    ).fetchone()
    return row["total"] > 0


def criar_emprestimo(matricula: str, patrimonio: str) -> dict:
    conn = db.get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")

        aluno = _buscar_aluno_por_matricula(conn, matricula)
        if aluno is None:
            conn.execute("ROLLBACK")
            raise HTTPException(status_code=404, detail={"codigo": "ALUNO_NAO_ENCONTRADO"})

        equipamento = _buscar_equipamento_por_patrimonio(conn, patrimonio)
        if equipamento is None:
            conn.execute("ROLLBACK")
            raise HTTPException(status_code=404, detail={"codigo": "EQUIPAMENTO_NAO_ENCONTRADO"})

        # Decisão assumida #2
        if _aluno_tem_pendencia(conn, aluno["id"]):
            conn.execute("ROLLBACK")
            raise HTTPException(
                status_code=409,
                detail={"codigo": "PENDENCIA", "mensagem": "Aluno possui equipamento com devolução vencida."},
            )

        # Decisão assumida #5: update condicional evita corrida entre
        # duas requisições simultâneas pelo mesmo equipamento.
        cur = conn.execute(
            "UPDATE equipamentos SET disponivel = 0 WHERE id = ? AND disponivel = 1",
            (equipamento["id"],),
        )
        if cur.rowcount == 0:
            conn.execute("ROLLBACK")
            raise HTTPException(
                status_code=409,
                detail={"codigo": "EQUIPAMENTO_INDISPONIVEL", "mensagem": "Equipamento já está emprestado."},
            )

        agora = datetime.now()
        # Decisão assumida #3: prazo fixo global de 48h.
        prevista = agora + timedelta(hours=db.PRAZO_HORAS_DEVOLUCAO)

        cur = conn.execute(
            """
            INSERT INTO emprestimos (aluno_id, equipamento_id, data_emprestimo, data_devolucao_prevista, data_devolucao)
            VALUES (?, ?, ?, ?, NULL)
            """,
            (aluno["id"], equipamento["id"], agora.isoformat(timespec="seconds"), prevista.isoformat(timespec="seconds")),
        )
        emprestimo_id = cur.lastrowid
        conn.execute("COMMIT")

        return {
            "id": emprestimo_id,
            "aluno": aluno["nome"],
            "matricula": aluno["matricula"],
            "equipamento": equipamento["nome"],
            "patrimonio": equipamento["patrimonio"],
            "data_emprestimo": agora.isoformat(timespec="seconds"),
            "data_devolucao_prevista": prevista.isoformat(timespec="seconds"),
        }
    finally:
        conn.close()


def devolver_emprestimo(emprestimo_id: int) -> dict:
    conn = db.get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")

        emprestimo = conn.execute(
            "SELECT * FROM emprestimos WHERE id = ?", (emprestimo_id,)
        ).fetchone()
        if emprestimo is None:
            conn.execute("ROLLBACK")
            raise HTTPException(status_code=404, detail={"codigo": "EMPRESTIMO_NAO_ENCONTRADO"})

        # Decisão assumida #4: devolver duas vezes é rejeitado, não
        # sobrescreve o timestamp original.
        if emprestimo["data_devolucao"] is not None:
            conn.execute("ROLLBACK")
            raise HTTPException(
                status_code=409,
                detail={"codigo": "JA_DEVOLVIDO", "mensagem": "Este empréstimo já foi devolvido."},
            )

        agora_iso = _now_iso()
        conn.execute(
            "UPDATE emprestimos SET data_devolucao = ? WHERE id = ?",
            (agora_iso, emprestimo_id),
        )
        # Decisão assumida #9: devolver (mesmo atrasado) extingue a pendência na hora.
        conn.execute(
            "UPDATE equipamentos SET disponivel = 1 WHERE id = ?",
            (emprestimo["equipamento_id"],),
        )
        conn.execute("COMMIT")
        return {"id": emprestimo_id, "data_devolucao": agora_iso}
    finally:
        conn.close()


def listar_atrasados(conn) -> list:
    # Decisão assumida #10: relatório mostra só os atrasos ATIVOS agora,
    # não o histórico de todas as infrações já cometidas.
    rows = conn.execute(
        """
        SELECT e.id, a.nome AS aluno, a.matricula, eq.nome AS equipamento, eq.patrimonio,
               e.data_emprestimo, e.data_devolucao_prevista
        FROM emprestimos e
        JOIN alunos a ON a.id = e.aluno_id
        JOIN equipamentos eq ON eq.id = e.equipamento_id
        WHERE e.data_devolucao IS NULL
          AND e.data_devolucao_prevista < ?
        ORDER BY e.data_devolucao_prevista ASC
        """,
        (_now_iso(),),
    ).fetchall()
    return [dict(r) for r in rows]


def listar_emprestimos_ativos(conn) -> list:
    rows = conn.execute(
        """
        SELECT e.id, a.nome AS aluno, a.matricula, eq.nome AS equipamento, eq.patrimonio,
               e.data_emprestimo, e.data_devolucao_prevista
        FROM emprestimos e
        JOIN alunos a ON a.id = e.aluno_id
        JOIN equipamentos eq ON eq.id = e.equipamento_id
        WHERE e.data_devolucao IS NULL
        ORDER BY e.data_devolucao_prevista ASC
        """
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# API JSON (é contra estes endpoints que os critérios de aceite são testados)
# ---------------------------------------------------------------------------

@app.post("/api/alunos", status_code=201)
def api_criar_aluno(matricula: str = Form(...), nome: str = Form(...)):
    conn = db.get_connection()
    try:
        try:
            conn.execute("INSERT INTO alunos (matricula, nome) VALUES (?, ?)", (matricula, nome))
        except Exception:
            raise HTTPException(status_code=409, detail={"codigo": "MATRICULA_DUPLICADA"})
        return {"matricula": matricula, "nome": nome}
    finally:
        conn.close()


@app.get("/api/alunos")
def api_listar_alunos():
    conn = db.get_connection()
    try:
        rows = conn.execute("SELECT matricula, nome FROM alunos ORDER BY nome").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.post("/api/equipamentos", status_code=201)
def api_criar_equipamento(patrimonio: str = Form(...), nome: str = Form(...)):
    conn = db.get_connection()
    try:
        try:
            conn.execute(
                "INSERT INTO equipamentos (patrimonio, nome, disponivel) VALUES (?, ?, 1)",
                (patrimonio, nome),
            )
        except Exception:
            raise HTTPException(status_code=409, detail={"codigo": "PATRIMONIO_DUPLICADO"})
        return {"patrimonio": patrimonio, "nome": nome, "disponivel": True}
    finally:
        conn.close()


@app.get("/api/equipamentos")
def api_listar_equipamentos():
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT patrimonio, nome, disponivel FROM equipamentos ORDER BY nome"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.post("/api/emprestimos", status_code=201)
def api_criar_emprestimo(matricula: str = Form(...), patrimonio: str = Form(...)):
    return criar_emprestimo(matricula, patrimonio)


@app.post("/api/emprestimos/{emprestimo_id}/devolucao")
def api_devolver(emprestimo_id: int):
    return devolver_emprestimo(emprestimo_id)


@app.get("/api/emprestimos/atrasados")
def api_listar_atrasados():
    conn = db.get_connection()
    try:
        return listar_atrasados(conn)
    finally:
        conn.close()


@app.get("/api/emprestimos/ativos")
def api_listar_ativos():
    conn = db.get_connection()
    try:
        return listar_emprestimos_ativos(conn)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Telas HTML (interface do técnico)
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def tela_inicial(request: Request):
    conn = db.get_connection()
    try:
        ativos = listar_emprestimos_ativos(conn)
        atrasados = listar_atrasados(conn)
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "ativos": ativos, "atrasados": atrasados},
        )
    finally:
        conn.close()


@app.get("/alunos", response_class=HTMLResponse)
def tela_alunos(request: Request, erro: str = ""):
    conn = db.get_connection()
    try:
        alunos = conn.execute("SELECT matricula, nome FROM alunos ORDER BY nome").fetchall()
        return templates.TemplateResponse(
            "alunos.html", {"request": request, "alunos": alunos, "erro": erro}
        )
    finally:
        conn.close()


@app.post("/alunos")
def form_criar_aluno(matricula: str = Form(...), nome: str = Form(...)):
    conn = db.get_connection()
    try:
        try:
            conn.execute("INSERT INTO alunos (matricula, nome) VALUES (?, ?)", (matricula, nome))
        except Exception:
            return RedirectResponse(url="/alunos?erro=Matrícula já cadastrada", status_code=303)
        return RedirectResponse(url="/alunos", status_code=303)
    finally:
        conn.close()


@app.get("/equipamentos", response_class=HTMLResponse)
def tela_equipamentos(request: Request, erro: str = ""):
    conn = db.get_connection()
    try:
        equipamentos = conn.execute(
            "SELECT patrimonio, nome, disponivel FROM equipamentos ORDER BY nome"
        ).fetchall()
        return templates.TemplateResponse(
            "equipamentos.html", {"request": request, "equipamentos": equipamentos, "erro": erro}
        )
    finally:
        conn.close()


@app.post("/equipamentos")
def form_criar_equipamento(patrimonio: str = Form(...), nome: str = Form(...)):
    conn = db.get_connection()
    try:
        try:
            conn.execute(
                "INSERT INTO equipamentos (patrimonio, nome, disponivel) VALUES (?, ?, 1)",
                (patrimonio, nome),
            )
        except Exception:
            return RedirectResponse(url="/equipamentos?erro=Patrimônio já cadastrado", status_code=303)
        return RedirectResponse(url="/equipamentos", status_code=303)
    finally:
        conn.close()


@app.get("/emprestimos", response_class=HTMLResponse)
def tela_emprestimos(request: Request, erro: str = ""):
    conn = db.get_connection()
    try:
        ativos = listar_emprestimos_ativos(conn)
        return templates.TemplateResponse(
            "emprestimos.html", {"request": request, "ativos": ativos, "erro": erro}
        )
    finally:
        conn.close()


@app.post("/emprestimos")
def form_criar_emprestimo(matricula: str = Form(...), patrimonio: str = Form(...)):
    try:
        criar_emprestimo(matricula, patrimonio)
    except HTTPException as exc:
        detalhe = exc.detail if isinstance(exc.detail, dict) else {"mensagem": str(exc.detail)}
        msg = detalhe.get("mensagem") or detalhe.get("codigo", "Erro ao registrar empréstimo.")
        return RedirectResponse(url=f"/emprestimos?erro={msg}", status_code=303)
    return RedirectResponse(url="/emprestimos", status_code=303)


@app.post("/emprestimos/{emprestimo_id}/devolucao")
def form_devolver(emprestimo_id: int):
    try:
        devolver_emprestimo(emprestimo_id)
    except HTTPException as exc:
        detalhe = exc.detail if isinstance(exc.detail, dict) else {"mensagem": str(exc.detail)}
        msg = detalhe.get("mensagem") or detalhe.get("codigo", "Erro ao devolver.")
        return RedirectResponse(url=f"/emprestimos?erro={msg}", status_code=303)
    return RedirectResponse(url="/emprestimos", status_code=303)


@app.get("/atrasados", response_class=HTMLResponse)
def tela_atrasados(request: Request):
    conn = db.get_connection()
    try:
        atrasados = listar_atrasados(conn)
        return templates.TemplateResponse(
            "atrasados.html", {"request": request, "atrasados": atrasados}
        )
    finally:
        conn.close()
