# Inventário de Catálogo — Produtos e Modelos

**Data:** 2026-07-17  
**Status:** Aguardando validação comercial  
**Objetivo:** Consolidar os produtos e modelos identificados na documentação para preparar o preenchimento das tabelas `produtos` e `modelos`.

---

## Regras de cadastro

- `Produto` representa a categoria genérica do catálogo.
- `Modelo` representa um item comercial específico vinculado a um produto.
- A carga final requer código comercial e preço de tabela fornecidos pelo vendedor. Este inventário e a planilha associada não definem preços.
- Tecnologias de leitura, configurações e acessórios só devem virar modelos quando tiverem código comercial independente.
- As fontes deste inventário são os folders em `docs/FoldersProdutos/` e a RAG validada pelo usuário. Itens da RAG ainda não validados permanecem como candidatos.

---

## Produtos e modelos confirmados

| Produto | Modelo candidato | Situação | Fonte |
|---|---|---|---|
| Catraca | Catraca Biométrica Fit TOPDATA | Confirmado | `documentos_conhecimento` |
| Catraca | Catraca com leitor facial Fit TOPDATA | Confirmado | `documentos_conhecimento` |
| Catraca | Catraca Facial em inox Box TOPDATA | Confirmado | `documentos_conhecimento` |
| Catraca | Catraca Facial Revolution TOPDATA | Confirmado | `documentos_conhecimento` |
| Catraca | Catraca iDBlock Balcão Facial - Control iD | Confirmado | `documentos_conhecimento` |
| Catraca | Catraca iDBlock Next com Contador de Giros - Control iD | Confirmado | `documentos_conhecimento` |
| Catraca | Catraca iDBlock Next com iDFace Max - Control iD | Confirmado | `documentos_conhecimento` |
| Catraca | Catraca iDBlock PcD Facial com iDFace Max - Control iD | Confirmado | `documentos_conhecimento` |
| Relógio de Ponto | Pontto - Relógio de Ponto Cartográfico - TOPDATA | Confirmado | `documentos_conhecimento` |
| Relógio de Ponto | Relógio de Ponto Biométrico - TOPDATA | Confirmado | `documentos_conhecimento` |
| Relógio de Ponto | Relógio de Ponto REP iDClass Bio Barras - Control iD | Confirmado | `documentos_conhecimento` |
| Relógio de Ponto | Relógio de Ponto REP iDClass Bio - Control iD | Confirmado | `documentos_conhecimento` |
| Relógio de Ponto | Relógio de Ponto REP iDClass Facial - Control iD | Confirmado | `documentos_conhecimento` |
| Ponto Eletrônico | Ponto Eletrônico Inner Ponto 4 TOPDATA | Confirmado | `documentos_conhecimento` |
| Câmera | Câmera IP série 1000 com Full Color e IR - Intelbras | Confirmado | `documentos_conhecimento` |
| Câmera | Câmera IP série 1000 com Full Color e IR VIP 1430 D FC+ - Intelbras | Confirmado | `documentos_conhecimento` |
| Cancela | Barrier Jetflex Brushless – Barreira Articulada de Alumínio | Confirmado | `documentos_conhecimento` |
| Cancela | Barrier Jetflex Brushless – Barreira Linear de PVC | Confirmado | `documentos_conhecimento` |
| Cancela | Cancela K1 Jetflex | Confirmado | `documentos_conhecimento` |
| Controle de Acesso | Inner Acesso 2 Prox | Confirmado | `folder-controle-de-acesso.txt` |
| Controle de Acesso | Inner Acesso 2 LC Bio | Confirmado | `folder-controle-de-acesso.txt` |
| Controle de Acesso | Inner Acesso 2 LC Bio Prox | Confirmado | `folder-controle-de-acesso.txt` |
| Controle de Acesso | Inner Acesso 2 QR Code Prox | Confirmado | `folder-controle-de-acesso.txt` |
| Controle de Acesso | Inner Acesso 2 QR Code LC Bio | Confirmado | `folder-controle-de-acesso.txt` |
| Controle de Acesso | Inner Acesso 2 QR Code LC Bio Prox | Confirmado | `folder-controle-de-acesso.txt` |
| Controle de Acesso | Inner Acesso 2 Complementar | Confirmado | `folder-controle-de-acesso.txt` |
| Controle de Acesso | Inner Acesso 2 com Botão | Confirmado | `folder-controle-de-acesso.txt` |
| Controle de Acesso | Controle de Acesso iDFace - Control iD | Confirmado | `documentos_conhecimento` |
| Controle de Acesso | Controle de Acesso iDFace Max - Control iD | Confirmado | `documentos_conhecimento` |
| Controle de Acesso | Controle de Acesso iDFlex IP65 Prox - Control iD | Confirmado | `documentos_conhecimento` |
| Controle de Acesso | Controle de Acesso iDUHF - Control iD | Confirmado | `documentos_conhecimento` |
| Controle de Acesso | Controle de Acesso Torniquete Facial com iDFace Max - Control iD | Confirmado | `documentos_conhecimento` |
| Controle de Acesso | Coletor Inner Acesso 2 - Topdata | Confirmado | `documentos_conhecimento` |
| Controle de Acesso | Coletor Inner Acesso - Topdata | Confirmado | `documentos_conhecimento` |
| Leitor Facial | Leitor Facial F4 | Confirmado | `folder-leitor-facial.txt` |
| Leitor Facial | Leitor Facial T4-50K | Confirmado | `folder-leitor-facial.txt` |
| Leitor Facial | Terminal de Reconhecimento Facial da série Pro DS-K1T673DX - Hikvision | Confirmado | `documentos_conhecimento` |
| Leitor Facial | Leitor facial Topdata | Confirmado | `documentos_conhecimento` |
| Software de Ponto | TopPonto Web | Confirmar cadastro | `folder-ponto-web.txt` |
| Software para Controle de Acesso | Software para Controle de Acesso iDSecure Cloud - Control iD | Confirmado | `documentos_conhecimento` |
| Software para Controle de Acesso | Software para Controle de Acesso iDSecure On-Premises - Control iD | Confirmado | `documentos_conhecimento` |
| Software para Controle de Acesso | TopAcesso | Confirmado | Informação do usuário |
| Bastão de Ronda | Viggia | Confirmar cadastro | `folder-bastao-de-ronda.txt` |

---

## Itens que precisam de decisão comercial

| Item | Decisão necessária | Evidência documental |
|---|---|---|
| Catraca Fit, Box e Revolution | Definir se cada combinação de leitor tem código comercial próprio ou é apenas uma configuração de orçamento. | Os folders listam biometria, proximidade, código de barras, QR Code e módulos LFD, LC ou LM como opções. |
| Inner Ponto 4 | Definir os códigos comerciais das combinações de leitor: biometria, proximidade, QR Code ou sem leitor para facial externo. | O folder descreve combinações, mas não nomeia os códigos comerciais. |
| Leitor TopProx Adicional | Confirmar se é vendido separadamente e deve entrar como modelo/acessório. | Aparece no bloco de modelos do Inner Acesso 2. |
| Botoeira Adicional | Confirmar se é vendido separadamente e deve entrar como modelo/acessório. | Aparece no bloco de modelos do Inner Acesso 2. |
| Braço articulado, urna coletora, pedestal inox, base de evento, totem e cobertura externa | Definir se serão cadastrados como acessórios precificáveis ou registrados apenas como observação do modelo principal. | Os folders os descrevem como opcionais. |
| Catraca Pedestal, Giratória e Cancela | Validar se são categorias/modelos comercializados atualmente. | Aparecem como opções de conversa, sem folder de produto correspondente. |
| Código e unidade comercial | Fornecer o código comercial do fabricante/Inforrel e confirmar unidade de venda. | O modelo aceita código opcional e unidade; a planilha sugere `UN` como valor inicial. |

---

## Candidatos adicionais da RAG para validação

Os seguintes títulos ativos em `documentos_conhecimento` parecem itens comercializáveis, mas não foram incluídos na planilha porque a documentação local não confirmou código comercial, linha comercial vigente ou granularidade do item.

### Cancelas

- Barrier Jetflex Brushless – Barreira Linear de Alumínio
- Brasso Jetflex – Barreira Linear de Alumínio

### Controle de acesso e catracas

- Controlador de acesso facial com biometria digital SS 5542 MF W – Intelbras
- Controlador de acesso facial SS 5531 MF EX – Intelbras


### CFTV e rede

- Gravador de vídeo Multi HD com 16 canais MHDX 1316 – Intelbras
- Roteador Empresarial Wi-Fi 4 de longo alcance AP 360 – Intelbras
- Roteador Empresarial Wi-Fi 5 de alta velocidade AP 1350 AC-S – Intelbras
- Switch Gerenciável 24 portas Gigabit e 4 portas SFP S2328G-A – Intelbras


---

## Arquivos relacionados

- Planilha de validação: `artefatos/implementador/planilha_catalogo_modelos_2026-07.csv`
- Folders de origem: `docs/FoldersProdutos/`
- Fonte RAG: tabela `documentos_conhecimento`
- Glossário da modelagem: `docs/dicionario_termos.md`

---

## Próximo passo

1. Vendedor valida produtos, modelos, acessórios, código e unidade comercial na planilha.
2. Vendedor fornece preços em fonte separada, pois não fazem parte da planilha solicitada.
3. Implementação prepara carga idempotente via SQLAlchemy, incluindo o preço obrigatório no momento da persistência.
