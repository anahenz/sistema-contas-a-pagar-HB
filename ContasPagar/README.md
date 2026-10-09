# ContasPagar — Gestão de condomínios

Aplicativo **desktop real**, em Python + PySide6, com SQLite e SQLAlchemy. A interface não usa navegador. Oferece modo local e modo de equipe online com servidor Python autenticado. Os cadastros começam vazios; as 16 categorias iniciais são criadas automaticamente.

## Versão 2.0 — equipe online e instalador automático

Execute **INSTALAR.bat** com dois cliques para configurar e criar o atalho. Na entrada, escolha **Equipe online** ou **Somente neste computador**. Para compartilhar dados, publique primeiro o servidor conforme **docs/HOSPEDAR_RENDER.md**. O pacote inclui `render.yaml`; ainda não há servidor publicado.

Os cadastros locais existentes são preservados. A migração para a base online é explícita via backup e só pode ocorrer com a base remota vazia. O modo online exige internet e login. O instalador continua no mesmo formato da versão anterior.

## Navegação dentro do aplicativo

Cadastros, edição, detalhes e pagamentos agora abrem **na área central da mesma janela**, com menu lateral e botão Voltar. Os formulários têm seções e duas colunas. O tema claro é aplicado também ao calendário, histórico, campos de data e listas, inclusive quando o Windows usa modo escuro.

Se já instalou a versão anterior, siga **ATUALIZAR.txt**: encerre pelo menu Sair da bandeja e copie o conteúdo da nova pasta ContasPagar sobre a pasta antiga, substituindo os arquivos. Sua `.venv` continua no lugar e o banco externo à pasta do projeto continua sendo utilizado. Não há mudança no esquema do banco nesta atualização.

Ao criar um condomínio, fornecedor ou categoria durante o preenchimento de uma conta, o sistema volta ao formulário original e seleciona o cadastro recém-criado. Campos já preenchidos são mantidos. Validações aparecem no próprio formulário; confirmações de exclusão/descarte e o seletor de arquivos continuam como diálogos do sistema.

## Começar no Windows

1. Extraia **toda** a pasta deste ZIP. Não execute os arquivos de dentro do ZIP.
2. Instale o **Python 3.11 ou superior, 64 bits**, pelo site https://www.python.org/downloads/windows/ . Mantenha o Python Launcher (`py`) instalado.
3. Dê dois cliques em **`instalar_dependencias.bat`**. A primeira instalação precisa de internet e pode demorar alguns minutos.
4. Ao terminar, dê dois cliques em **`iniciar.bat`**.
5. Cadastre o primeiro condomínio em **Condomínios → Adicionar**.
6. Cadastre fornecedores, se desejar, e use **Contas a Pagar → Nova conta**.

No modo local, depois da instalação inicial, o aplicativo funciona offline. No modo online é necessário acessar o servidor. Não precisa abrir VS Code. Para diagnosticar um problema de abertura, execute no terminal da pasta:

```powershell
.venv\Scripts\python.exe main.py
```

## Gerar ContasPagar.exe

No **Windows**, após instalar as dependências:

1. Dê dois cliques em **`gerar_exe.bat`**.
2. Aguarde o PyInstaller concluir.
3. O resultado será **`dist\ContasPagar.exe`**.
4. Copie esse executável para uma pasta fixa no computador. Ele contém Python e as dependências e pode ser aberto com dois cliques, **sem Python instalado no computador de destino**.
5. Para instalar uma cópia na pasta de programas do seu usuário e criar atalhos, execute **`instalar_exe.bat`** depois de gerar o executável.

O ZIP contém o código-fonte e a configuração de compilação. **Não contém um `.exe` de Windows já compilado.** O PyInstaller precisa executar no Windows para gerar o aplicativo de Windows; a compilação e as notificações devem ser verificadas nessa plataforma.

A instalação com atalhos não exige administrador. Os dados ficam separados do executável. Instale/mova o executável para o destino definitivo **antes** de ativar “Iniciar com o Windows”. Se trocar o local posteriormente, desative e reative essa opção no novo local.

## Uso diário

### Dashboard

- **Contas com vencimento no mês:** quantidade no mês atual, excluindo canceladas.
- **A pagar no mês:** saldo das contas ainda não pagas, com vencimento no mês atual.
- **Pago neste mês:** pagamentos confirmados pela data em que foram realizados, excluindo estornos.
- **Pendentes:** todas as contas não pagas e não canceladas, inclusive atrasadas, em todos os períodos.
- **Vencidas / hoje / até 7 dias:** contagens de contas abertas. “Até 7 dias” inclui hoje.
- **Próximos vencimentos:** contas abertas em atraso ou com vencimento até 30 dias à frente.

Os rótulos diferenciam o período dos valores para evitar confundir pagamentos realizados no mês com contas que vencem no mês.

### Cadastros e contas

- Condomínios, fornecedores e categorias possuem pesquisa, criação, edição e exclusão.
- Dê dois cliques em um condomínio para abrir os dados, contas e histórico financeiro.
- Novos fornecedores, categorias e condomínios também podem ser criados dentro do formulário da conta.
- O menu **⋯** da conta permite visualizar, editar, duplicar, pagar, cancelar, reativar e excluir, conforme a situação.
- Códigos de barras e números de documentos são textos: os zeros à esquerda são preservados.
- Duplicar copia os dados, mas limpa o boleto, número do documento e a recorrência. Confira valor e datas antes de salvar.
- Arraste a borda das colunas para ajustar a largura; pare o mouse sobre um texto cortado para ler o conteúdo completo.

### Situação e alertas

| Distância do vencimento | Situação |
|---|---|
| Mais de 7 dias | Pendente |
| De 7 a 1 dia | Próxima do vencimento |
| Hoje | Vence hoje |
| Data anterior a hoje | Vencida |
| Pagamento confirmado | Paga |
| Cancelamento manual | Cancelada |

A situação é calculada a partir da data atual do computador; não fica congelada no banco. A tabela mostra o prazo de cada conta. Contas pagas e canceladas saem dos alertas.

O sino mostra a quantidade de **contas abertas em alerta**, não a quantidade de notificações não lidas. A central reúne contas próximas, de hoje e vencidas. Visualizar a central registra os alertas como vistos, mas não remove a obrigação financeira.

### Notificações nativas do Windows

Em **Configurações**, habilite:

- **Receber resumo diário de vencimentos**;
- **Ao fechar a janela, continuar na área de notificações**;
- **Iniciar com o Windows, em segundo plano**, para abrir automaticamente após entrar na sua conta do Windows.

O sistema verifica os dados ao abrir e a cada minuto enquanto estiver em execução. A janela pode ficar oculta na bandeja do Windows. O resumo é solicitado ao Windows **no máximo uma vez por dia**, incluindo as quantidades próximas, de hoje e vencidas. Clicar nele abre a central de alertas.

Se não havia nenhuma conta elegível e uma for cadastrada depois, o resumo pode ser enviado nesse momento. Depois que o resumo do dia já foi enviado, novas contas aparecem no sino sem disparar mais notificações naquele dia.

Não há execução com o computador desligado. Ao voltar a abrir, o sistema atualiza os vencimentos. Se você escolher **Sair** no menu da bandeja, as verificações param até a próxima abertura ou login do Windows. O modo “Não perturbe” e as preferências do Windows podem suprimir a exibição; a central interna continua disponível. O registro de envio significa que a mensagem foi solicitada ao Windows, não uma confirmação de leitura.

### Pagamentos e histórico

Use **Marcar como pago** e preencha data, valor, forma, comprovante e observações. O sistema não realiza transferências bancárias; ele registra pagamentos realizados.

O valor pago pode incluir desconto ou juros. Se diferir do valor lançado, o sistema pede confirmação de **quitação integral**. Não há parcelamento parcial do saldo nessa versão: lance parcelas como contas separadas.

**Desfazer pagamento** reabre a conta e preserva o registro anterior como estornado. Um novo pagamento gera outro registro. Nome da conta, condomínio, categoria, fornecedor e vencimento são guardados como estavam no momento do pagamento, para manter o histórico mesmo após edições posteriores.

Para preservar o histórico financeiro:

- Contas com qualquer pagamento, inclusive estornado, não podem ser apagadas. Desfaça o pagamento ativo e cancele a conta quando necessário.
- Cadastros referenciados por contas ou séries recorrentes não podem ser apagados enquanto os vínculos existirem.
- Contas sem histórico podem ser excluídas após confirmação. O evento de exclusão permanece no registro de alterações.

### Recorrências

Escolha mensal, bimestral, trimestral, semestral ou anual no formulário. Ao criar a série, o próximo lançamento é gerado imediatamente. As verificações seguintes geram lançamentos até **31 dias à frente**, inclusive recuperando períodos em que o programa esteve fechado.

Cada combinação de série e vencimento é única no banco. Rodar a verificação várias vezes não duplica lançamentos.

- Dia 31 em fevereiro passa para o último dia do mês, mas retorna ao dia 31 nos meses que o possuem.
- Valor, descrição, fornecedor, categoria e forma de pagamento são copiados.
- Código de barras e documento não são reaproveitados automaticamente.
- O intervalo entre emissão e vencimento é preservado.
- Editar um lançamento muda esse lançamento e o modelo usado em gerações futuras. **Lançamentos que já existem não são alterados em lote.**
- Alterar o intervalo/dia reposiciona a próxima geração após o vencimento mais distante já lançado.
- **Encerrar recorrência**, no menu ⋯, impede novas gerações. As contas já criadas permanecem e podem ser canceladas individualmente.
- Excluir ou cancelar uma única conta não encerra a série.

### Pesquisa, filtros e calendário

A busca do topo pesquisa contas por condomínio, fornecedor, despesa, categoria e documento. A tela de contas também oferece filtros combináveis por situação, condomínio, categoria, fornecedor, mês e ano.

O filtro **Pendentes** corresponde ao status “Pendente” (mais de 7 dias). Para todas as obrigações abertas de curto prazo, use o sino; para todas as situações, selecione **Todas**.

O calendário marca datas com lançamentos reais. Clicar em um dia lista suas contas. Os botões do cabeçalho permitem navegar entre os meses.

### Relatórios

Selecione início e fim e clique em **Gerar relatório**, **Exportar Excel** ou **Exportar PDF**.

Os relatórios incluem resumo, gastos por condomínio/categoria/fornecedor, histórico mensal, contas e pagamentos. Nas comparações:

- **Lançado** usa a data de vencimento e exclui contas canceladas.
- **Pago** usa a data do pagamento e exclui pagamentos estornados.
- **Pendente e vencido** usam os vencimentos dentro do período escolhido e a situação atual.

Por isso, o valor pago e o valor lançado de um mesmo período podem ser diferentes. O Excel contém valores monetários numéricos, com formatação, e proteção contra interpretação de textos cadastrais como fórmulas. O PDF contém tabelas e paginação.

### Backup e restauração

Em **Backup**, selecione uma pasta e frequência: manual, diária ou semanal. Salve a configuração. **Fazer backup agora** cria uma cópia consistente do SQLite, incluindo dados que ainda estejam no journal WAL.

O backup automático é verificado enquanto o aplicativo está em execução; se uma execução foi perdida, é retomado na próxima abertura. Backups manuais também atualizam a data da última cópia. A pasta não sofre limpeza automática: as cópias permanecem até serem excluídas pelo usuário.

Para restaurar, escolha um arquivo `.sqlite3` ou `.db` produzido por este aplicativo e confirme. O sistema verifica integridade, versão, tabelas, colunas e referências antes de substituir o banco. Uma cópia do estado anterior é salva em `backups\antes_restauracao` dentro da pasta de dados.

A restauração inclui as configurações do backup. A opção de início com o Windows é uma configuração externa do sistema operacional: confira e salve a opção novamente depois de restaurar/mudar de computador.

## Onde ficam os dados

No Windows:

```text
%LOCALAPPDATA%\ContasPagar\contas_pagar.sqlite3
%LOCALAPPDATA%\ContasPagar\contaspagar.log
```

Os dados sobrevivem ao fechamento, à troca do executável e à atualização do código. Não ficam dentro do `.exe` nem na pasta temporária do PyInstaller.

Este projeto é **local, de um usuário do Windows por banco**, sem sincronização ou acesso simultâneo por rede. Não coloque o banco ativo em pasta de rede ou sincronização. Para transportar dados entre computadores, use backup/restauração. O banco não usa criptografia nem autenticação própria; a proteção de acesso é a da conta e das pastas do Windows.

## Instalação por comandos

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

Compilar:

```powershell
.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm ContasPagar.spec
```

Testes:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
```

Para desenvolvimento Linux/macOS, use um ambiente virtual, instale `requirements.txt` e execute `python main.py`. O início automático é específico do Windows. Os testes usam `QT_QPA_PLATFORM=offscreen` quando essa variável não está definida.

## Estrutura

```text
main.py                      inicialização, instância única e tratamento de erros
app/
  assets/                    estilo visual e ícone
  controllers/               ações das contas
  database/                  conexão, sessão e primeira execução
  models/                    entidades SQLAlchemy
  services/                  finanças, recorrências, backup, relatórios e alertas
  views/                     janela principal, telas e formulários
  widgets/                   tabelas, campos e ícones reutilizáveis
  utils/                     valores, datas e status
  __init__.py
tests/                       testes de regras e interface
docs/                        arquitetura e roteiro de verificação no Windows
requirements.txt
requirements-dev.txt
ContasPagar.spec
instalar_dependencias.bat
iniciar.bat
gerar_exe.bat
instalar_exe.bat
instalar_exe.ps1
```

## Validação e limites da entrega

A suíte automatizada testa gravação SQLite, edição e exclusão, consultas, pagamentos e estornos, histórico, valores monetários, limites de status/alertas, recorrência e fim de mês, backup/restauração, exportações e abertura das dez telas. Também preenche formulários PySide6 e confirma a gravação.

Os testes foram executados em Linux com Qt em modo offscreen. O envio de resumo foi testado com substituto da bandeja do sistema; **a exibição real da notificação, o clique no Windows, o início automático e o `.exe` ainda precisam de validação em Windows**. Use o roteiro em `docs/VALIDACAO_WINDOWS.md`.

Documentação técnica utilizada:

- Qt/PySide6 e notificações nativas: https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QSystemTrayIcon.html
- PyInstaller e compilação por plataforma: https://pyinstaller.org/en/stable/
