"""
Configurações do sistema.
"""

from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Twilio
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None
    # API Key (alternativa ao Auth Token; ver AnotacoesPessoais/Beto/spike_twilio/STATUS.md)
    TWILIO_API_KEY_SID: Optional[str] = None
    TWILIO_API_KEY_SECRET: Optional[str] = None

    # Canal de saída (REQ-008, Fase 10): por onde a resposta chega ao cliente.
    # Eixo INDEPENDENTE do `ModoExecucao` (`models/parametro.py`), que decide *se* a
    # resposta precisa de aprovação humana antes de sair. Este decide *por onde* sai
    # depois que já pode sair. Fica no `.env` de propósito: é trava de ambiente, não
    # configuração de operação — trocar o modo de execução pela UI nunca deve, sozinho,
    # começar a mandar mensagem de verdade para o cliente.
    #   simulado: grava a mensagem no banco e não entrega nada (default)
    #   twilio:   entrega de fato pelo WhatsApp
    CANAL_SAIDA: str = "simulado"

    # Como o canal Twilio entrega a resposta *síncrona* do webhook:
    #   twiml: responde o próprio POST do webhook com <Message>. Único caminho que
    #          funciona em conta trial/Sandbox (a API recusa texto livre, erro 21654).
    #          Não devolve o SID na hora — ele chega depois pelo `statusCallback`.
    #   rest:  webhook devolve TwiML vazio e a mensagem sai pela API. SID na hora,
    #          um caminho de envio só, mas exige conta paga.
    # Aprovação e resposta manual usam SEMPRE REST: não há webhook aberto para responder.
    TWILIO_MODO_ENVIO: str = "twiml"

    # Base pública desta aplicação (túnel Cloudflare), usada para montar a URL de
    # `statusCallback`. Sem ela o modo `twiml` envia normalmente, mas nunca descobrimos
    # o SID de saída e o reply-to do WhatsApp fica sem como resolver.
    APP_URL_PUBLICA: Optional[str] = None

    # Valida a assinatura `X-Twilio-Signature` nos endpoints públicos `/webhook` e
    # `/webhook/status`. Default `False` porque em `simulado` o webhook é chamado pelo
    # testador de conversas, que não assina nada. Ligar junto com `CANAL_SAIDA=twilio`.
    TWILIO_VALIDAR_ASSINATURA: bool = False

    # Grava em arquivo o formulário CRU que a Twilio manda para `/webhook` e
    # `/webhook/status`. Existe por uma janela específica: a conta trial expira e, com ela,
    # a única fonte de payloads reais. Todo teste de webhook deste projeto usa formulário
    # que nós mesmos inventamos, então nenhum deles prova que o campo existe, se chama assim
    # e vem nesse formato. Capturar uma vez transforma isso em fixture permanente.
    # Default `False`: não é instrumentação para ficar ligada em produção.
    TWILIO_CAPTURAR_PAYLOADS: bool = False
    TWILIO_CAPTURA_ARQUIVO: str = "logs/payloads_twilio.jsonl"
    # Com a captura ligada, os anexos (`MediaUrl{i}`) também são baixados para esta pasta,
    # com um `indice.jsonl` do que deu certo e do que falhou. Fica em `logs/`, que é
    # ignorado pelo git: são fotos e áudios reais de quem testou.
    TWILIO_CAPTURA_MIDIAS_PASTA: str = "logs/midias_twilio"

    # Database
    DATABASE_URL: str = "postgresql+psycopg://inforrel:inforrel_dev@192.168.0.34:5433/assistente_vendas"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    LOG_LEVEL: str = "WARNING"
    SQL_ECHO: bool = False

    # Autenticação (REQ-010, Fase 4) — assina o cookie de sessão. Default só serve
    # para dev local; sobrescrever via .env em qualquer ambiente compartilhado/produção.
    SESSION_SECRET_KEY: str = "dev-secret-key-troque-em-producao"
    SESSION_MAX_AGE_SEGUNDOS: int = 8 * 60 * 60

    # Liga/desliga o gate de sessão em `/api/*`. `false` libera TUDO sem login —
    # é escape hatch de dev/QA para destravar o painel, não configuração de
    # produção: nunca usar em ambiente com dado real de cliente (ADR-006).
    # O default fica `True` de propósito: quem quiser abrir tem que declarar.
    AUTH_ENABLED: bool = True
    # Com `AUTH_ENABLED=false` não há sessão, mas os endpoints de aprovação
    # continuam registrando *quem* aprovou. Este é o login assumido nesse caso.
    # Vazio = primeiro usuário com login cadastrado (menor id).
    AUTH_USUARIO_PADRAO: Optional[str] = None

    # LLM
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "llama-3.1-8b-instant"
    LLM_API_KEY: Optional[str] = None
    LLM_TEMPERATURE: float = 0.3

    # Embeddings (RAG)
    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_API_KEY: Optional[str] = None

    # RAG / Retrieval
    RAG_ENABLED: bool = True
    RAG_TOP_K: int = 4
    RAG_SCORE_MINIMO: float = 0.70
    RAG_SUGERIR_PRODUTOS: bool = False
    RAG_EXIBIR_FONTES_PAINEL: bool = True

    # Q&A Pairs
    QA_ENABLED: bool = True
    QA_SCORE_MINIMO: float = 0.80
    QA_SCORE_MINIMO_FULLTEXT: float = 0.25
    QA_TOP_K: int = 3
    QA_APENAS_APROVADOS: bool = True

    # Ajuda contextual do painel (FAQ por tela) — base independente de QA/RAG,
    # atende o operador interno, nunca o cliente. Ver backend/services/ajuda/.
    AJUDA_ENABLED: bool = True
    AJUDA_TOP_K: int = 5
    # Bem mais baixo que QA_SCORE_MINIMO_FULLTEXT (0.25) de proposito: perguntas
    # de ajuda sao curtas, e ts_rank cai com documentos curtos — medido em base
    # real, acertos legitimos ficam na casa de 0.06 a 0.10. O filtro de verdade e
    # o operador `@@` (os termos precisam casar); este limiar so barra ruido.
    AJUDA_FULLTEXT_MIN: float = 0.03
    # Calibrado medindo similaridade real (text-embedding-3-small) contra a pergunta
    # "Como altero o valor de um parametro?":
    #   0.94 "como altero o valor de um parametro"   <- quase identica
    #   0.76 "alterar parametro"
    #   0.74 "como mudo o parametro"                 <- sinonimo: o caso que justifica
    #                                                   esta camada, e que o full-text
    #                                                   nao pega (radical diferente)
    #   0.45 "trocar configuracao do sistema"        <- generico demais
    #   0.33 "como aprovo uma mensagem"              <- outra tela
    #   0.22 "qual a cor do ceu"
    # Verdadeiros positivos ficaram >= 0.74 e falsos <= 0.45; 0.65 cai no meio do vao,
    # com margem dos dois lados. Mais baixo que o 0.80 de `pares_qa` de proposito: la um
    # falso positivo vai para o cliente, aqui so mostra ajuda errada a um operador.
    AJUDA_EMBEDDING_MIN: float = 0.65

    # Consulta CNPJ
    RECEITAWS_BASE_URL: str = "https://www.receitaws.com.br/v1/cnpj"

    # Consulta CPF / crédito (REQ-015) — provedor a definir (serasa, spc, boavista, quod)
    CPF_CONSULTA_CREDITO_ENABLED: bool = False
    CPF_CONSULTA_CREDITO_PROVIDER: Optional[str] = None
    CPF_CONSULTA_CREDITO_API_KEY: Optional[str] = None
    CPF_CONSULTA_CREDITO_BASE_URL: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
