# Complemento da versão 2.0

Modo local preservado. Modo online usa server/api.py (FastAPI), SQLite + SQLAlchemy em disco persistente e app/services/remote.py no desktop. O snapshot autenticado alimenta as mesmas telas. Gravações são serializadas e transacionais; uma revisão global impede conflitos. Formulários prendem a revisão de abertura. Recibos idempotentes são gravados na mesma transação da operação. Tokens e usuários ficam em banco separado dos dados financeiros. Backup exportado não inclui credenciais. Uma única instância e worker no servidor.

Instalação Windows continua via INSTALAR.bat. Publicação e recuperação estão em HOSPEDAR_RENDER.md.

## Documentação original do modo local

# Arquitetura e regras de persistência

## Fluxo

As views PySide6 chamam serviços que trabalham em transações SQLAlchemy. Cada operação abre uma sessão, efetua commit em caso de sucesso e rollback em caso de erro. A interface recebe dicionários já materializados, sem dependência de sessões abertas.

`FinanceService` centraliza regras, filtros, status, recorrências e auditoria. `AccountActions` liga menus aos formulários. `ReportService`, `BackupService`, `NotificationService` e `startup.py` cuidam dos seus respectivos domínios.

## Banco

- `condominios`, `fornecedores`, `categorias`: cadastros.
- `contas`: despesa, datas, referências, valor e cancelamento.
- `pagamentos`: registros permanentes, snapshot cadastral, comprovante e eventual data de estorno.
- `recorrencias`: modelo, intervalo, dia original, próximo vencimento e ativação.
- `notificacoes`: registro por conta e dia, tipo e leitura.
- `configuracoes`: preferências e versão do esquema.
- `auditoria`: eventos de cadastro, conta, pagamento e recorrência.

Valores monetários são **inteiros em centavos**, evitando imprecisão de ponto flutuante. O status dependente do tempo é calculado, não gravado como texto sujeito a ficar desatualizado. A recorrência é um vínculo com uma série, não somente um booleano.

As chaves estrangeiras estão ativas. A exclusão de contas remove notificações associadas; pagamentos impedem exclusão da conta. O índice parcial `uq_pagamento_ativo` garante no máximo um pagamento não estornado por conta. Existe unicidade entre série e vencimento e entre conta e dia de notificação.

O modo WAL permite cópias consistentes via API `sqlite3.backup`. Não são realizadas cópias simples apenas do arquivo principal enquanto ele está aberto.

## Processamento periódico

Um `QTimer` dispara a verificação a cada minuto no processo da interface. Ele gera recorrências faltantes, verifica backup automático e calcula alertas. Outro timer executa a primeira verificação após a janela ter sido inicializada. O resumo diário é deduplicado no banco, inclusive entre reinícios.

O programa permanece na bandeja quando configurado. O registro `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` inicia o programa com `--tray` após login. A configuração não exige privilégios administrativos.

Uma conexão local Qt (`QLocalServer`/`QLocalSocket`), identificada pela pasta de dados, evita duas instâncias da mesma instalação. Uma segunda abertura traz a janela existente para frente.

## Evolução

A versão inicial do esquema é `1`. Versões diferentes são rejeitadas, em vez de modificadas implicitamente. Antes de alterar o esquema em futuras versões, criar migração explícita com backup e testes de dados existentes. `create_all` inicializa tabelas novas, mas não substitui um mecanismo de migração.

A camada de consulta carrega registros locais e aplica parte dos filtros em Python. Para bases com dezenas de milhares de contas, evoluir para paginação SQL e processamento de relatórios/backup em workers. Nesta versão, essas tarefas são síncronas e podem ocupar a interface em bases muito grandes.

Não há integração bancária, envio de e-mails, acesso multiusuário, anexos de comprovantes, criptografia própria nem atualização automática do programa. O comprovante solicitado é armazenado como número/texto.

## Navegação 1.1

`FormPage` é um QWidget com sinal de conclusão, validação inline e monitoramento de alterações. `MainWindow.open_form` adiciona o formulário ao QStackedWidget; uma pilha guarda a página anterior e permite cadastros auxiliares sem perder os campos da conta. Ao salvar, a view volta à anterior e atualiza os registros. Nenhum formulário cadastral usa QDialog.exec.

`apply_light_theme` define estilo Fusion e todos os papéis da paleta; `load_stylesheet` resolve caminhos dos ícones a partir da pasta de assets, incluindo o ambiente empacotado. O banco e sua versão de esquema permanecem iguais à versão 1.0.
