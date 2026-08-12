# Documento de Decisões - Trabalho 1

**Equipe:** Pablo Santiago de Araujo Rodrigues e Gustavo Monteiro Lopes

---

## 1. Decisões assumidas

**1.** O pedido não especifica se o controle é por tipo de equipamento ou por item físico único. Assumimos que cada equipamento possui um identificador patrimonial único e exclusivo. Se o cliente esperasse um controle genérico por tipo (ex: "emprestar 3 multímetros"), o impacto seria: a tabela de banco de dados `emprestimos` precisaria de uma nova coluna `quantidade`, a tabela `equipamentos` passaria a controlar `estoque_disponivel` em vez de um status booleano `disponivel`, e a interface de devolução exigiria refatoração para processar devoluções parciais.

**2.** O pedido não especifica o que caracteriza exatamente uma "pendência". Assumimos que pendência significa possuir qualquer equipamento com a data de devolução vencida. Se o cliente esperasse que qualquer equipamento em posse do aluno (mesmo dentro do prazo) já configurasse pendência, o impacto seria: a query SQL de validação em `_aluno_tem_pendencia` precisaria ser alterada para remover a condição `data_devolucao_prevista < data_atual`, bloqueando o `INSERT` de um novo empréstimo sempre que o `COUNT` de itens não devolvidos do aluno fosse maior que zero.

**3.** O pedido não especifica o prazo para a devolução (o que significa "devolve depois"). Assumimos um prazo fixo e global de 48 horas para todos os empréstimos (constante `PRAZO_HORAS_DEVOLUCAO`). Se o cliente esperasse prazos variáveis dependendo do item, o impacto seria: a criação obrigatória de uma tabela `categorias_equipamento` com a coluna `prazo_horas`, a adição de uma chave estrangeira `categoria_id` na tabela `equipamentos`, e a reescrita de `criar_emprestimo` para buscar este valor ao invés de usar a constante de 48 horas.

**4.** O pedido não especifica o comportamento do sistema diante da tentativa de devolver um item já devolvido (segunda ocorrência da operação). Assumimos que o sistema rejeita a transação e retorna erro (`409 JA_DEVOLVIDO`). Se o cliente esperasse que o sistema atualizasse silenciosamente a devolução, o impacto seria: a remoção da checagem `if emprestimo["data_devolucao"] is not None` em `devolver_emprestimo`, permitindo que um novo `UPDATE` sobrescrevesse o *timestamp* original, o que corromperia permanentemente as métricas históricas de tempo real de uso.

**5.** O pedido não especifica o tratamento de concorrência se o mesmo equipamento for emprestado simultaneamente. Assumimos um `UPDATE` condicional (`WHERE disponivel = 1`) dentro de uma transação `BEGIN IMMEDIATE`, falhando a segunda requisição com `409 EQUIPAMENTO_INDISPONIVEL`. Se o cliente esperasse um sistema de "fila de espera", o impacto seria: a criação de uma nova entidade `fila_espera` (`aluno_id`, `equipamento_id`, `posicao`), e a implementação de um serviço assíncrono (worker) rodando em background para disparar notificações e realocar automaticamente o status do equipamento assim que o usuário anterior finalizasse a devolução.

**6.** O pedido não especifica quem interage com o sistema. Assumimos que apenas os técnicos manipulam a interface para registrar todas as movimentações — por isso o sistema não tem login/autenticação. Se o cliente esperasse um autoatendimento operado pelos próprios alunos, o impacto seria: a exigência de desenvolver um módulo de autenticação (JWT/sessões), a criação de controle de acesso baseado em papéis (RBAC — `ROLE_ALUNO` e `ROLE_TECNICO`) para blindar o acesso ao relatório de atrasos, e a limitação das queries de empréstimo apenas ao `ID` do usuário autenticado.

**7.** O pedido não especifica a quantidade de equipamentos permitida por transação. Assumimos que cada registro de empréstimo relaciona um aluno a exatamente um equipamento (1:1). Se o cliente esperasse um modelo de "carrinho" com múltiplos itens em um único empréstimo, o impacto seria: a normalização do banco de dados para dividir a estrutura em `emprestimo_cabecalho` e `itens_emprestimo`, o que forçaria a reescrita completa dos contratos de API (JSONs de request e response) para aceitarem arrays de patrimônios.

**8.** O pedido não especifica como o aluno é buscado para o registro. Assumimos que a identificação exige a digitação de uma matrícula única (`UNIQUE` no banco). Se o cliente esperasse busca por nome parcial, o impacto seria: o banco de dados precisaria remover a restrição `UNIQUE` da coluna `nome` (que hoje nem existe), e o frontend exigiria um componente de *autocomplete* assíncrono exibindo dados compostos (ex: "Nome - CPF") para que o operador resolvesse manualmente conflitos de homônimos antes de confirmar o `POST` de empréstimo.

**9.** O pedido não especifica como as pendências são resolvidas. Assumimos que registrar a devolução atrasada extingue a pendência instantaneamente (a query de pendência só olha empréstimos com `data_devolucao IS NULL`). Se o cliente esperasse a aplicação de uma suspensão punitiva pós-atraso, o impacto seria: adicionar a coluna `data_fim_suspensao` na tabela `alunos`. O método `devolver_emprestimo` precisaria de uma nova lógica matemática para calcular dias de atraso e somá-los à data atual, enquanto `criar_emprestimo` precisaria incluir a validação `data_atual > data_fim_suspensao`.

**10.** O pedido não detalha o escopo do relatório de atrasos. Assumimos que ele lista exclusivamente os empréstimos ativos em atraso no momento da consulta (`listar_atrasados`). Se o cliente esperasse um histórico analítico de todas as infrações já cometidas, o impacto seria: modificar a consulta SQL do relatório para remover o filtro `data_devolucao IS NULL`, e forçar a inserção de parâmetros de paginação e filtros de data na interface e na API, caso contrário, o crescimento do banco esgotaria a memória do servidor ao gerar o relatório.

**11.** O pedido não especifica procedimentos de baixa para equipamentos que "sumam" permanentemente. Assumimos que eles figuram eternamente no relatório de atrasos (não implementamos baixa por extravio). Se o cliente esperasse um recurso de baixa por extravio, o impacto seria: a criação do status `EXTRAVIADO` na tabela `equipamentos` e de uma rota `PATCH /api/emprestimos/{id}/extravio`, que forçaria o fechamento lógico do empréstimo em aberto e excluiria o item das queries de equipamentos disponíveis, gerando também um registro obrigatório em uma nova tabela de auditoria.

**12.** O pedido não especifica a origem dos cadastros básicos. Assumimos que o próprio sistema incluirá endpoints e telas de cadastro local para inserir alunos e equipamentos (`/alunos`, `/equipamentos`). Se o cliente esperasse integração com o ERP ou sistema acadêmico da universidade, o impacto seria: esvaziar a tabela `alunos` local (mantendo apenas o ID externo), e substituir as consultas ao banco local por chamadas HTTP assíncronas para as APIs da universidade, exigindo a implementação de estratégias de *retry* e tratamento de falhas de rede antes de autorizar qualquer empréstimo.

---

## 2. Perguntas ao cliente

**1.** O aluno pode fazer reserva de um equipamento para uma data futura, ou o empréstimo é apenas por ordem de chegada no momento da retirada?
*   **Respostas e impactos:** Se a resposta for "ordem de chegada", o sistema não muda e apenas registra a saída no momento do balcão (é o que implementamos). Se a resposta for "pode reservar", o impacto seria a criação de uma tabela `reservas`, a alteração da query de disponibilidade para cruzar o intervalo solicitado com as reservas já existentes, e a criação de uma rotina automática (*cron job*) para cancelar reservas se o aluno não comparecer em X horas.

**2.** Qual a política exata em caso de devolução de um equipamento danificado pelo aluno?
*   **Respostas e impactos:** Se a resposta for "o sistema não controla isso, o técnico resolve administrativamente", o sistema foca apenas na data (é o que implementamos). Se a resposta for "precisamos bloquear o aluno e marcar o equipamento para manutenção", o impacto seria a adição de uma etapa de checklist/estado na devolução, a criação de um status `EM_MANUTENCAO` no equipamento, e um novo tipo de bloqueio `DANO_PATRIMONIO` no cadastro do aluno que exigiria uma intervenção manual de um perfil administrador para ser removido.

**3.** O laboratório é centralizado, ou os alunos e equipamentos pertencem a diferentes departamentos (ex: Elétrica vs. Mecânica) com restrições cruzadas de acesso?
*   **Respostas e impactos:** Se for "laboratório unificado", qualquer aluno pega qualquer item livremente (é o que implementamos). Se for "dividido por departamento", o impacto seria a inclusão de uma coluna `departamento_id` nas tabelas de `alunos` e `equipamentos`. O sistema precisaria ser reestruturado para que as validações de empréstimo comparassem o departamento do aluno com o do equipamento, bloqueando transações caso fossem incompatíveis.

---

## 3. Critérios de aceite

1. **Entrada:** `POST /api/emprestimos` com a matrícula do Aluno B (sem pendências) e o patrimônio do Equipamento A (disponível).
   **Resultado esperado:** HTTP `201`; o registro é salvo; `GET /api/equipamentos` passa a mostrar o Equipamento A com `disponivel = false`; a resposta contém `data_devolucao_prevista` igual à data/hora atual + 48 horas.

2. **Entrada:** `POST /api/emprestimos` para o Aluno C e o Equipamento B, sendo que o Aluno C já possui o Equipamento D com `data_devolucao_prevista` vencida há 1 dia (e ainda não devolvido).
   **Resultado esperado:** HTTP `409` com corpo `{"codigo": "PENDENCIA", ...}`; nenhum novo registro de empréstimo é criado (`GET /api/emprestimos/ativos` não muda de tamanho).

3. **Entrada:** `GET /api/emprestimos/atrasados`, havendo no banco 1 empréstimo devolvido no prazo, 1 emprestado dentro do prazo e 1 emprestado com `data_devolucao_prevista` vencida (e não devolvido).
   **Resultado esperado:** A resposta contém uma lista com exatamente 1 item — o empréstimo com prazo vencido — ignorando os devolvidos e os que ainda estão no prazo.

---

## 4. Decisões da ferramenta de IA

**Decisão identificada:** O assistente de IA sugeriu adicionar automaticamente colunas de auditoria (`created_at`, `updated_at`, `deleted_at`) em todas as entidades do banco de dados, assumindo o uso de *soft delete* (exclusão lógica).
*   **Por que é plausível:** É um padrão consolidado na indústria de software para garantir segurança, rastreabilidade de dados e recuperação de informações excluídas acidentalmente.
*   **Por que pode estar inadequada:** O cliente solicitou explicitamente que o sistema seja "simples de usar". A introdução de *soft deletes* aumenta a complexidade das consultas SQL básicas (obrigando a inclusão de `WHERE deleted_at IS NULL` em todos os `SELECT`s e relatórios) e consome espaço de armazenamento desnecessário para um controle interno de laboratório escolar que pode não exigir auditoria formal. Optamos por **não** seguir essa sugestão: o schema final (`app/db.py`) não tem essas colunas.

---

## Registro de tempo

Horas escrevendo ou gerando código: 5
Horas decidindo o que o sistema deveria fazer: 8

---

## 5. Declaração de uso de IA

*   **Ferramentas:** Gemini (Google) e Claude (Anthropic)
*   **Para quê:** Levantamento inicial de ambiguidades no pedido de 5 linhas do cliente, formatação textual dos requisitos em padrão Markdown, estruturação das tabelas de impactos arquiteturais, ideação de cenários extremos (concorrência e repetição de operações), e implementação do sistema (FastAPI + SQLite) a partir das decisões já tomadas pela dupla.
*   **O que foi verificado manualmente:** Todas as decisões sugeridas e geradas pela IA foram lidas, filtradas, discutidas pela dupla e adaptadas para garantir conformidade estrita com o formato exigido pelo enunciado ("O pedido não especifica X. Assumimos Y. Se esperasse Z, mudaria..."). Os impactos sistêmicos, as queries SQL e o código de validação (pendência, concorrência, dupla devolução) foram lidos e testados manualmente contra os três critérios de aceite antes da entrega final.
