# ContasPagar 2.0 — publicar a base da equipe

Este pacote contém a versão desktop e uma API Python. Ele **não está publicado** somente por baixar o ZIP. O endereço real será gerado pelo Render após o deploy.

## 1. Preparar o repositório

1. Crie um repositório **privado** no GitHub, por exemplo `contaspagar`.
2. Na página do repositório, use **Add file → Upload files**.
3. Envie o conteúdo da pasta `ContasPagar` extraída: `app`, `server`, `main.py`, `render.yaml` e demais arquivos do projeto. Não envie a pasta externa do ZIP como outro nível.
4. Confirme em **Commit changes**. O arquivo `render.yaml` precisa aparecer na raiz do repositório.
5. Não envie bancos `.sqlite3`, `.env`, backups, senhas ou a pasta `.venv`. O pacote entregue não contém dados reais nem credenciais.

## 2. Publicar no Render

O caminho mais simples usa o arquivo `render.yaml` já preparado:

1. No Render, escolha **New → Blueprint** e conecte o repositório privado.
2. Revise o serviço `contaspagar-api` e o disco persistente. A configuração utiliza plano **Starter e disco de 1 GB**, que têm cobrança. Confira o valor exibido pelo provedor antes de confirmar. Nenhum serviço pago foi contratado por este projeto.
3. Preencha os dois segredos solicitados:
   - `CONTASPAGAR_ADMIN_EMAIL`: seu e-mail de acesso ao aplicativo.
   - `CONTASPAGAR_ADMIN_PASSWORD`: senha exclusiva com no mínimo 12 caracteres.
4. Confirme o deploy quando concordar com o custo. Esses valores ficam no painel do Render, nunca no GitHub ou enviados pelo chat.
5. Aguarde **Live**. Copie a URL `https://...onrender.com` mostrada pelo serviço.
6. A URL acrescida de `/health` deve responder `status: ok`. A página principal pode mostrar `Not Found`: este servidor fornece uma API, não uma interface web.

Se já estiver na tela **New Web Service**, use os mesmos campos manualmente:

| Campo | Valor |
|---|---|
| Language | Python 3 |
| Root Directory | vazio, se `server` e `app` estão na raiz |
| Build Command | `pip install -r server/requirements.txt` |
| Start Command | `python -m uvicorn server.api:app --host 0.0.0.0 --port $PORT --workers 1` |
| Health Check Path | `/health` |
| Instance Type | Starter ou outro plano que aceite disco persistente |
| Disk mount path | `/var/data` |
| Disk size | 1 GB inicial; monitorar e ampliar conforme necessário |
| `CONTASPAGAR_SERVER_DIR` | `/var/data/contaspagar` |
| `PYTHON_VERSION` | `3.13.12` |
| `TZ` | `America/Sao_Paulo` |

Adicione também os dois segredos de administrador indicados acima. **Configure o disco antes do primeiro cadastro.** Não use filesystem temporário nem o plano gratuito para guardar o SQLite.

## 3. Instalar em cada computador

1. Feche versões antigas pelo menu **Sair** da bandeja.
2. Extraia todo o ZIP e execute **INSTALAR.bat** com dois cliques.
3. Use o atalho **ContasPagar** criado na área de trabalho.
4. Na entrada, escolha **Equipe online**, cole a mesma URL HTTPS, informe e-mail e senha.
5. O administrador cadastra as demais pessoas em **Equipe e backup**. Cada pessoa usa seu próprio acesso; todos visualizam os mesmos condomínios e contas desta empresa.

O instalador continua automático e inclui as novas telas. A URL e o e-mail ficam salvos no computador; a senha e a sessão não são persistidas. O login é solicitado ao reabrir. Sessões duram até 12 horas. Para continuar recebendo notificações, mantenha o aplicativo aberto e autenticado. Após expiração, saia e entre novamente.

## 4. Levar os dados antigos

1. No aplicativo, entre em **Somente neste computador** e gere um backup pela tela **Backup**.
2. Saia pelo menu da bandeja. Entre novamente em **Equipe online** como administrador.
3. Abra **Equipe e backup → Importar backup local para a base online vazia**.
4. Selecione o backup SQLite. Limite: 25 MB. O servidor recusa importação se já houver condomínios, fornecedores ou contas. Não é uma mesclagem de bancos.
5. Confirme os totais e pagamentos no Dashboard e no Histórico antes de iniciar o uso da equipe.

A base local original permanece no computador. Ela não recebe as futuras alterações online e não é uma cópia sincronizada. O modo local é independente: não registre contas nele esperando enviá-las depois.

## 5. Operação, segurança e backups

- O SQLite e o SQLAlchemy ficam no servidor. Somente a API autenticada acessa o arquivo; nenhum PC abre o SQLite pela rede.
- Uma única empresa por servidor. Operadores podem criar, editar, pagar e excluir registros financeiros conforme as regras existentes. Administradores também gerenciam acessos, exportam backups e importam a base inicial. Não há isolamento de condomínios por usuário nesta versão.
- Atualização a cada 30 segundos fora dos formulários; botão **Atualizar** para consultar imediatamente. Durante edição, o formulário preserva os dados de abertura. Se a base mudou, o servidor rejeita o salvamento e solicita voltar à lista e reabrir. Não sobrescreve silenciosamente outra edição.
- Todas as gravações passam por transação, revisão e identificador de operação. Repetir a mesma solicitação após uma resposta perdida não duplica o lançamento. Quando não houver certeza de conclusão, confira a lista antes de criar outra conta.
- Senhas com hash scrypt e salt; tokens aleatórios armazenados como hash no servidor; HTTPS obrigatório no desktop. Não há registro público de usuários. O e-mail é um identificador de acesso: não há envio de e-mail nem recuperação automática por e-mail.
- As rotinas do servidor verificam recorrências e backup diariamente, inclusive com os PCs desligados. Notificações Windows só aparecem com o cliente aberto/autenticado e conectado.
- Backup financeiro diário em `/var/data/contaspagar/backups`. A pasta cresce: monitore espaço, baixe cópias externas regularmente e estabeleça retenção adequada. Cópias no mesmo disco não protegem contra perda do disco inteiro.
- **Baixar backup da base online** salva uma cópia financeira no PC. Essa exportação não inclui senhas nem sessões. O arquivo separado `acessos.sqlite3` também deve integrar a política de backup do servidor, por cópia SQLite consistente ou snapshot do volume, nunca uma cópia crua enquanto há gravações.
- Desativar usuário ou redefinir senha revoga suas sessões. O administrador não pode desativar o próprio acesso pela tela.
- A senha de administrador das variáveis de ambiente só é usada na primeira inicialização. Mudá-la no Render depois não redefine um usuário existente. Após o primeiro login, pode remover o segredo de senha do ambiente; o servidor com base existente não precisa dele.
- O aplicativo continua oferecendo relatórios PDF/Excel a partir do último conjunto de dados carregado. Atualize antes de exportar; sem conexão, os dados exibidos podem estar desatualizados.

## 6. Recuperação administrada

Restauração de uma base online em uso exige manutenção coordenada. Não há botão que permita a um usuário substituir acidentalmente o banco da equipe.

Pare o processo da API, mantenha o disco montado e execute no ambiente Linux do servidor:

```bash
python -m server.maintenance restore /caminho/backup.sqlite3
```

O comando exige confirmação `RESTAURAR`, valida o backup, preserva uma cópia anterior e renova a revisão. O arquivo de acessos é preservado. Reinicie a API e peça que os usuários entrem novamente. Se o provedor não permitir shell com o serviço parado, use um procedimento de manutenção com o suporte/administrador do provedor; não tente copiar por cima do banco em uso.

Para recuperar uma senha de usuário existente, também em manutenção:

```bash
python -m server.maintenance reset-password pessoa@empresa.com.br
```

A senha é solicitada sem aparecer no terminal. Não a coloque como argumento ou em arquivos de código.

## Limites desta entrega

O servidor está preparado para **uma instância e um worker**. O processo aplica um bloqueio exclusivo do arquivo no Linux para impedir múltiplos workers. Não aumente workers/réplicas nem use SQLite em pasta compartilhada. Para escala maior, a evolução é um banco de servidor e controle transacional adequado.

O pacote foi testado localmente com clientes HTTP de teste e interface Qt sem monitor. Ainda faltam o deploy real no Render, teste entre dois PCs Windows, notificações nativas e execução do instalador no Windows. Não há migração automática ao publicar, hospedagem contratada nem credenciais embutidas.

Referências oficiais de hospedagem: https://render.com/docs/blueprint-spec e https://render.com/docs/disks .
