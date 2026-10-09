# Validação da versão 2.0

Data: 09/10/2026.

Comando executado na pasta ContasPagar:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

Resultado: **41 testes aprovados**, código de saída 0. Um aviso de depreciação do adaptador HTTPX do Starlette, sem falhas.

Cobertura: regras financeiras e datas; CRUD; pagamentos e estornos; recorrências; relatórios; backup/restauração local; formulários embutidos e tema claro; autenticação; permissões de operador; bloqueio de sessões desativadas; revisão de edições; duas gravações concorrentes (uma aceita, outra recusada); repetição idempotente; rollback; importação inicial; persistência após reiniciar; backup diário do servidor; serialização de datas; HTTPS no cliente; composição das telas online.

Interface de login e tela de equipe renderizadas e inspecionadas em Qt offscreen. Capturas com dados de exemplo em interface_login.png e interface_equipe_online.png.

Scripts BAT conferidos com CRLF e ASCII. O instalador foi preservado; não foi executado em Windows neste ambiente.

Ainda não validado: deploy no Render, rede entre dois PCs reais, TLS no domínio definitivo, notificações nativas do Windows e compilação EXE. Os testes HTTP do servidor usam TestClient ASGI; não equivalem a publicar o serviço.
