# Assistente sobre apostas esportivas

Projetos III, FGV EESP, 2º semestre de 2026. Grupo Apostas esportivas: Leonardo Sorensen, Leonardo Kim, Leonardo Cesar, Rodrigo Thibes e Gustavo Gherson.

Assistente educativo que responde perguntas sobre apostas esportivas usando **apenas** a base de conhecimento do grupo (`base/base_conhecimento.json`). Não consulta a internet, não usa modelo de linguagem externo e não dá palpites.

As respostas vêm em camadas, da mais simples à mais detalhada: um resumo em uma frase, a resposta curta, a definição das palavras difíceis que aparecem nela (glossário com 32 termos) e, só se o usuário quiser, o aprofundamento com fontes. As chances aparecem como "X de cada 100" e os valores em reais sem centavos.

Inclui um simulador financeiro integrado à conversa: o usuário pode escrever o cenário no chat ("aposto R$ 50 por semana há 5 anos, odd 1,80, 50% de chance, 8% ao ano") ou preencher o formulário da página Simulador. O simulador calcula total em risco, valor esperado, faixa de resultados por 10.000 simulações (Monte Carlo), sensibilidade à chance suposta, comparação com guardar o dinheiro e margem da casa.

## Como rodar

```bash
pip install -r requirements.txt
streamlit run app.py
```

Testes:

```bash
pip install pytest
pytest
```

## Como publicar (Streamlit Community Cloud, gratuito)

1. Entre em share.streamlit.io com a conta do GitHub.
2. Clique em Create app, escolha este repositório, branch `main` e arquivo `app.py`.
3. O link gerado vai no campo "Link da solução" do documento de entrega.

## Estrutura

```
app.py                      interface (conversa, página do simulador, gráficos e tabelas)
base/base_conhecimento.json base de conhecimento: registros, fontes e respostas de segurança
assistente/texto.py         normalização do português (acentos, sinônimos, radicais)
assistente/seguranca.py     sinais de risco, verificados antes da busca
assistente/busca.py         busca BM25 com limiar; abaixo dele, o assistente não responde
assistente/cenario.py       leitura dos números de um cenário escrito na conversa
assistente/simulador.py     cálculos do simulador (Conteúdo IV, Parte II), Monte Carlo e margem
assistente/explicacao.py    frases que explicam o resultado em linguagem simples (modelos fixos, sem IA)
assistente/legibilidade.py  índice de Flesch adaptado ao português, usado nos testes
assistente/assistente.py    orquestra segurança, busca, simulador e resposta
tests/                      testes de perguntas, neutralidade, segurança, simulador, integração e linguagem
docs/avaliacao/             perguntas escritas como apostador e script que mede a taxa de acerto
docs/roteiro_teste_usuarios.md  roteiro dos testes com usuários
docs/evidencias/            capturas de tela e diagramas (Implementações I, II e III)
```

## Como funciona a restrição à base

1. A pergunta passa primeiro pelos gatilhos de segurança (crise, dívida, recuperar perdas, perda de controle). Se algum casar, a resposta vem de `respostas_seguranca` e o simulador não é oferecido.
2. Sem sinal de risco, a busca compara a pergunta com as formas alternativas de cada registro.
3. Se a frase traz valor e frequência de apostas, os números vão para o simulador. As frases que explicam o resultado são modelos fixos preenchidos com os números calculados.
4. Se a nota do melhor registro ficar abaixo do limiar e não houver cenário, o assistente diz que a base não cobre a pergunta. Ele nunca gera texto novo: todo texto exibido está no JSON ou é um modelo fixo com números calculados.

## Como o simulador calcula

- Número de apostas = apostas por período × períodos; total em risco = valor × número de apostas.
- Valor esperado por aposta = valor × (chance suposta × odd − 1).
- Faixa de resultados: 10.000 trajetórias sorteadas com semente fixa. Entre dois pontos do gráfico, as vitórias seguem uma binomial, o que equivale a sortear aposta por aposta.
- Chance de terminar no prejuízo na tabela de sensibilidade: conta exata pela binomial. Os testes conferem o Monte Carlo com essa conta.
- Investimento: depósitos iguais ao valor apostado em cada período, com a taxa anual convertida para o período.

## Como editar a base

Cada registro tem: `id`, `tema`, `perguntas` (formas alternativas), `palavras_chave`, `resumo` (uma frase, até 22 palavras), `resposta` (camada curta), `aprofundamento` (camada "Quer entender melhor?"), `fontes` (chaves da lista `fontes`), `limite`, `acao` e `seguranca`. A lista `glossario` tem `termo`, `formas` (como a palavra pode aparecer no texto) e `definicao`. Depois de editar, rode `pytest`: o teste `test_pergunta_cadastrada_acha_o_proprio_registro` avisa se uma pergunta nova cair no registro errado, e `tests/test_linguagem.py` avisa se uma resposta ficou difícil de ler (Flesch abaixo de 50) ou se o resumo passou de 22 palavras. Para medir a taxa de acerto em perguntas escritas como apostador: `python docs/avaliacao/avaliar.py`.
