# Roteiro do teste com usuários

Para as aulas de validação depois da Implementação III. Cada sessão leva cerca de 15 minutos.

## Quem

5 a 8 pessoas que apostam ou já apostaram em bets, de preferência fora do curso de Economia. Um integrante conduz e outro anota.

## Antes de começar

1. Abra o assistente em uma aba nova (conversa vazia).
2. Explique: "Queremos testar o assistente, não você. Pense em voz alta. Não há resposta errada."
3. Não ajude a pessoa durante as tarefas. Anote onde ela trava.

## Tarefas

1. Pergunte, com as suas palavras, se dá para ganhar dinheiro com bet.
2. Descubra o que é uma odd e quanto você recebe se apostar R$ 20 na odd 2,50.
3. Conte ao assistente como você aposta (ou como alguém que você conhece aposta) e veja o resultado.
4. No simulador, mude a chance de acerto para 55 de cada 100. O que mudou?
5. Pergunte algo que você sempre quis saber sobre apostas.

Em cada resposta, peça para a pessoa marcar "ajudou" ou "não ajudou" (polegar).

## Perguntas depois das tarefas

Peça uma nota de 1 a 5 para cada frase:

- Entendi as respostas sem precisar de ajuda.
- Os números do simulador foram fáceis de entender.
- Eu confio que as respostas são corretas.
- Usaria de novo ou indicaria para alguém.

E duas abertas: "O que foi mais difícil de entender?" e "O que faltou?".

Teste de compreensão (1 minuto): "Com as suas palavras, o que o simulador disse que aconteceria com o seu dinheiro?". Anote se a pessoa disse a perda média e o total apostado corretamente.

## O que guardar

- O arquivo "Baixar registro da conversa" (barra lateral): perguntas, tipo de resposta e avaliação.
- A lista "Perguntas sem resposta" da barra lateral.
- As anotações do condutor.

## Como medir

- Taxa de respostas certas: perguntas respondidas pelo registro certo, dividido pelo total.
- Taxa de "ajudou" entre as respostas avaliadas.
- Média de cada nota de 1 a 5.
- Quantas pessoas explicaram o resultado do simulador corretamente.

Cada pergunta sem resposta ou respondida errado vira uma forma alternativa nova ou um registro novo na base, conferido com `pytest` e com `python docs/avaliacao/avaliar.py`.
