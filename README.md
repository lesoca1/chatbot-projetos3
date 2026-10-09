# Assistente sobre apostas esportivas

Projetos III, FGV EESP, 2º semestre de 2026. Grupo Apostas esportivas: Leonardo Sorensen, Leonardo Kim, Leonardo Cesar, Rodrigo Thibes e Gustavo Gherson.

Assistente educativo que responde perguntas sobre apostas esportivas usando **apenas** a base de conhecimento do grupo (`base/base_conhecimento.json`). Não consulta a internet, não usa modelo de linguagem externo e não dá palpites.

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
app.py                      interface (chat + prévia do simulador)
base/base_conhecimento.json base de conhecimento: registros, fontes e respostas de segurança
assistente/texto.py         normalização do português (acentos, sinônimos, radicais)
assistente/seguranca.py     sinais de risco, verificados antes da busca
assistente/busca.py         busca BM25 com limiar; abaixo dele, o assistente não responde
assistente/assistente.py    orquestra segurança, busca e resposta
assistente/simulador.py     cálculos do simulador (Conteúdo IV, Parte II)
tests/                      testes de perguntas previstas, neutralidade, segurança e cálculos
docs/evidencias/            capturas de tela e fluxograma
```

## Como funciona a restrição à base

1. A pergunta passa primeiro pelos gatilhos de segurança (crise, dívida, recuperar perdas, perda de controle). Se algum casar, a resposta vem de `respostas_seguranca` e o simulador não é oferecido.
2. Sem sinal de risco, a busca compara a pergunta com as formas alternativas de cada registro.
3. Se a nota do melhor registro ficar abaixo do limiar, o assistente diz que a base não cobre a pergunta. Ele nunca gera texto novo: todo texto exibido está no JSON.

## Como editar a base

Cada registro tem: `id`, `tema`, `perguntas` (formas alternativas), `palavras_chave`, `resposta` (camada curta), `aprofundamento` (camada "Quer entender melhor?"), `fontes` (chaves da lista `fontes`), `limite`, `acao` e `seguranca`. Depois de editar, rode `pytest`: o teste `test_pergunta_cadastrada_acha_o_proprio_registro` avisa se uma pergunta nova cair no registro errado.
