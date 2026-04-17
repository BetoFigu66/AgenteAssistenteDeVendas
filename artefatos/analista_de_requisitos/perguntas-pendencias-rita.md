# Pendências para Definir com a Rita (POC)

**Data**: 2026-04-16  

---

## 1) Escalonamento / Human takeover (REQ-004)

1. **Quando você considera “cliente grande/projeto complexo” por quantidade de equipamentos?**
   - A partir de quantas **catracas**? `>= _4__`
   - A partir de quantos **relógios**? `>= _4__`

2. **Por quantidade de funcionários, qual é o limiar que te faz querer assumir?**
   - Funcionários `>= _não interfere__`

3. **Qual número/WhatsApp você quer receber as notificações do handoff no POC?**
   - (confirmar o número e se é WhatsApp Business) vamos criar um sandbox para testes, mas Rita passou o número 19 99664-6832, que poderemos usar depois. Confirmado que se trata de WhatsApp business.

4. **Quais frases reais os clientes usam para pedir humano?**
   - Me diga 5 a 10 exemplos (do jeito que eles escrevem).
ATENDENTE
QUERO FALAR COM VENDEDOR
QUERO FALAR COM ATENDENTE
VENDEDOR

5. **Quais frases/padrões mais comuns de reclamação/insatisfação?**
   - Me diga 5 a 10 exemplos.

---

## 2) Respostas automáticas / Base de conhecimento (REQ-003)

6. **Você consegue me enviar o arquivo/texto das suas “respostas rápidas” completas?**
   - (todas as macros/atalhos que você usa hoje)

7. **Você pode enviar os 2 catálogos atualizados (catracas e relógios)?**
   - Em PDF/arquivo, como você tiver.

8. **Para responder “valor”: você prefere que o sistema responda como?**
   - ( ) sempre pedir **quantidade** antes
   - ( ) pode dar **faixa de preço** sem quantidade
   - ( ) nunca falar preço sem você ver

9. **Quais são as 10 perguntas mais frequentes que você mais quer que a IA responda no POC?**
   - (valor, modelos, instalação, prazo, etc.)

---

## 3) Orçamentos e conversão (REQ-006)

10. **Como você prefere marcar se um orçamento virou compra ou não? (manual no POC)**
   - ( ) uma tela/admin simples (você seleciona o cliente e marca “convertido/perdido”)
   - ( ) outro formato (me diga qual)

11. **Quando for “perdido”, quais motivos você quer registrar?**
   - (ex: preço, prazo, sumiu/não respondeu, comprou de outro, sem verba etc.)

---

## 4) Registro / privacidade (REQ-005)

12. **Tem algum dado que você NÃO quer que o sistema registre no histórico?**
   - ex: e-mail, endereço completo, CNPJ, etc. (ou pode registrar tudo?)

---

## 5) Twilio / WhatsApp (REQ-008)

13. **Você topa testar primeiro no Twilio Sandbox (dev)?**
   - (sim/não)

14. **Se o envio falhar, você prefere:**
   - ( ) o sistema tentar de novo 1 vez e depois escalar
   - ( ) escalar imediatamente
   - ( ) outro comportamento: ___
