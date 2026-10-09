# Roteiro de verificação no Windows

Execute este roteiro em uma base de teste antes de usar dados de produção.

1. Instale as dependências e abra por `iniciar.bat`. Confirme que o Dashboard abre e possui valores zerados.
2. Cadastre condomínio e fornecedor, confirme máscara de CNPJ e crie conta de R$ 1.250,00 para sete dias à frente. Feche e reabra: os dados devem permanecer.
3. Verifique pesquisa por nome/documento e filtros; confira a conta no calendário e no perfil do condomínio.
4. Cadastre vencimentos para oito dias, sete dias, hoje e ontem. O sino deve mostrar três contas em alerta. A conta com oito dias não deve disparar alerta.
5. Com notificações habilitadas no Windows, confira o resumo nativo. Clique na mensagem: a central deve abrir. Feche e reabra no mesmo dia: não deve haver segundo resumo.
6. Deixe o programa na bandeja até o dia seguinte. Confira a atualização das datas e o novo resumo diário. Também teste após suspender e retomar o computador.
7. Pague uma conta, confira histórico e relatórios, desfaça o pagamento e confirme o registro de estorno. Registre novamente e confira que só o novo pagamento compõe o total pago.
8. Crie uma conta mensal para dia 31; confira a próxima ocorrência e o ajuste para o fim de meses curtos. Encerre a recorrência e confirme que contas já existentes permanecem.
9. Faça backup, crie outro cadastro e restaure o backup. O novo cadastro deve desaparecer e a cópia de segurança anterior deve existir. Tente um arquivo inválido: os dados atuais devem permanecer.
10. Exporte Excel e PDF. Abra os arquivos, confira valores, período, nomes e páginas.
11. Gere o `.exe` com `gerar_exe.bat`. Copie-o para um Windows sem Python ou teste em ambiente limpo. Repita abertura, persistência, notificações e relatórios.
12. Execute `instalar_exe.bat`, abra pelo atalho e ative “Iniciar com o Windows”. Saia da sessão do Windows e entre novamente. Confira ícone na bandeja e abertura pelo menu. Depois, desative a opção e confirme que não volta a iniciar no login.
13. Abra o aplicativo duas vezes. A segunda abertura deve ativar a primeira janela sem iniciar outro processo principal com banco concorrente.
14. Confira a interface em escala de tela de 100%, 125% e 150%, principalmente formulários, barra lateral e tabelas.

Se uma notificação não aparecer, confira as permissões e o modo Não perturbe do Windows. O aplicativo registra a solicitação ao sistema, sem confirmação de exibição. Para repetir o teste no mesmo dia, use uma pasta de teste separada definida por `CONTASPAGAR_DATA_DIR`; não apague dados reais.
