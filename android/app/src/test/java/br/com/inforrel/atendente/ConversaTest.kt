package br.com.inforrel.atendente

import br.com.inforrel.atendente.conversas.DesfechoEnvio
import br.com.inforrel.atendente.conversas.ItemConversa
import br.com.inforrel.atendente.conversas.MODO_AGENTE
import br.com.inforrel.atendente.conversas.MODO_HUMANO
import br.com.inforrel.atendente.conversas.ModeloConversa
import br.com.inforrel.atendente.conversas.SituacaoMensagem
import br.com.inforrel.atendente.conversas.autor
import br.com.inforrel.atendente.conversas.avisoCanal
import br.com.inforrel.atendente.conversas.canalSaida
import br.com.inforrel.atendente.conversas.desfecho
import br.com.inforrel.atendente.conversas.horaMensagem
import br.com.inforrel.atendente.conversas.mesclar
import br.com.inforrel.atendente.conversas.montarItens
import br.com.inforrel.atendente.conversas.rotuloDia
import br.com.inforrel.atendente.conversas.situacao
import br.com.inforrel.atendente.conversas.tituloCabecalho
import br.com.inforrel.atendente.conversas.trechoCitacao
import br.com.inforrel.atendente.rede.ArmazemCookies
import br.com.inforrel.atendente.rede.ConfiguracoesSistema
import br.com.inforrel.atendente.rede.CookieJarPersistente
import br.com.inforrel.atendente.rede.Mensagem
import br.com.inforrel.atendente.rede.MensagemManualEnviada
import br.com.inforrel.atendente.rede.Rede
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.time.LocalDate

/** Tela da conversa: leitura do histórico, mescla das atualizações, dias, citação e situação. */
class ConversaTest {
    private lateinit var servidor: MockWebServer

    // Recorte de `GET /api/historico/{telefone}` do backend (Mensagem.to_dict() + reprovada).
    private val corpoHistorico = """
        {"telefone":"+5519998986565","mensagens":[
          {"id":10,"telefone":"+5519998986565","conteudo":"Bom dia","origem":"user",
           "timestamp":"2026-11-23T12:00:00.123456Z","atendimento_id":5,"processamento_id":77,
           "resposta_a_mensagem_id":null,"timestamp_envio":null,"erro_envio":null,"aprovador_id":null,
           "pendente_aprovacao":false,"manual":false,"reprovada":false,"segundos_pendente":null},
          {"id":11,"telefone":"+5519998986565","conteudo":"Quantas catracas?","origem":"system",
           "timestamp":"2026-11-23T12:00:05Z","atendimento_id":5,"aprovador_id":3,
           "pendente_aprovacao":false,"manual":false,"reprovada":false},
          {"id":12,"telefone":"+5519998986565","conteudo":"Duas","origem":"user",
           "timestamp":"2026-11-24T13:00:00Z","resposta_a_mensagem_id":11,"pendente_aprovacao":false}
        ]}
    """.trimIndent()

    private val corpoDados = """
        {"telefone":"+5519998986565","status_identificacao":"sem_empresa",
         "contato":{"id":1,"nome":"Cris","email":null,"cargo":null},"empresa":null,"pessoa":null,
         "atendimento":{"id":5,"numero_atendimento_cliente":2,"modo_operacao":"humano","fase":"esclarecendo"}}
    """.trimIndent()

    // Recorte de `GET /api/config/sistema` (valores de tipos variados, como o backend devolve).
    private val corpoConfig = """
        {"configuracoes":[
          {"nome":"API_PORT","grupo":"Servidor","valor":8000,"sensivel":false},
          {"nome":"RAG_ENABLED","grupo":"Base de conhecimento","valor":true},
          {"nome":"TWILIO_AUTH_TOKEN","grupo":"Canal WhatsApp","valor":"definido","sensivel":true},
          {"nome":"CANAL_SAIDA","grupo":"Canal WhatsApp","valor":"simulado","sensivel":false}
        ]}
    """.trimIndent()

    @Before
    fun subir() {
        servidor = MockWebServer().apply { start() }
    }

    @After
    fun derrubar() = servidor.shutdown()

    private fun modelo(atendimentoIdLista: Int? = null): ModeloConversa {
        val armazem = object : ArmazemCookies {
            override fun ler() = emptyMap<String, String>()
            override fun gravar(cookies: Map<String, String>) {}
        }
        val api = Rede.criarApi(servidor.url("/").toString(), CookieJarPersistente(armazem), {}, timeoutSegundos = 3)
        return ModeloConversa(api, "+5519998986565", atendimentoIdLista)
    }

    private fun msg(
        id: Int,
        ts: String,
        origem: String = "system",
        pendente: Boolean = false,
        manual: Boolean = false,
        reprovada: Boolean = false,
        erro: String? = null,
        envio: String? = null,
        citada: Int? = null,
        conteudo: String = "m$id",
    ) = Mensagem(
        id = id, conteudo = conteudo, origem = origem, timestamp = ts, pendenteAprovacao = pendente,
        manual = manual, reprovada = reprovada, erroEnvio = erro, timestampEnvio = envio, respostaAMensagemId = citada,
    )

    @Test
    fun `primeira carga pede 200 e as seguintes 50, mesclando`() = runTest {
        servidor.enqueue(MockResponse().setBody(corpoHistorico))
        servidor.enqueue(MockResponse().setBody(corpoDados))
        servidor.enqueue(MockResponse().setBody(corpoConfig))
        // Atualização: a 11 foi reprovada e chegou a 13.
        servidor.enqueue(
            MockResponse().setBody(
                """{"mensagens":[
                  {"id":11,"conteudo":"Quantas catracas?","origem":"system","timestamp":"2026-11-23T12:00:05Z","reprovada":true},
                  {"id":13,"conteudo":"Anotado","origem":"system","timestamp":"2026-11-24T13:00:09Z","pendente_aprovacao":true}
                ]}""",
            ),
        )
        servidor.enqueue(MockResponse().setResponseCode(500))
        val m = modelo()

        m.carregar()
        assertEquals("/api/historico/+5519998986565?limit=200", servidor.takeRequest().path)
        assertEquals("/api/conversa/+5519998986565", servidor.takeRequest().path)
        assertEquals(listOf(10, 11, 12), m.estado.value.mensagens.map { it.id })
        assertEquals("humano", m.estado.value.dados?.atendimento?.modoOperacao)
        assertEquals("/api/config/sistema", servidor.takeRequest().path)
        assertEquals("simulado", m.estado.value.canalSaida)

        m.carregar()
        assertEquals("/api/historico/+5519998986565?limit=50", servidor.takeRequest().path)
        val estado = m.estado.value
        assertEquals(listOf(10, 11, 12, 13), estado.mensagens.map { it.id })
        assertTrue(estado.mensagens.first { it.id == 11 }.reprovada)
        // Falha no cabeçalho não apaga o anterior nem vira erro da conversa.
        assertEquals("Cris", tituloCabecalho(estado.dados, "x"))
        assertNull(estado.erro)
    }

    @Test
    fun `mescla ordena pelo instante e nao pela string`() {
        val atuais = listOf(msg(1, "2026-11-24T10:00:00.5Z"), msg(2, "2026-11-24T10:00:01Z"))
        val novas = listOf(msg(3, "2026-11-24T10:00:00Z"))
        assertEquals(listOf(3, 1, 2), mesclar(atuais, novas).map { it.id })
    }

    @Test
    fun `separador por dia em Brasilia e citacao resolvida`() {
        val hoje = LocalDate.of(2026, 11, 24)
        val mensagens = listOf(
            msg(1, "2026-11-24T02:00:00Z", origem = "user"), // 23/11 23:00 em Brasília
            msg(2, "2026-11-24T12:00:00Z"),
            msg(3, "2026-11-24T12:01:00Z", origem = "user", citada = 2),
            msg(4, "2026-11-24T12:02:00Z", origem = "user", citada = 999),
        )
        val itens = montarItens(mensagens, hoje)
        assertEquals(
            listOf("d2026-11-23", "m1", "d2026-11-24", "m2", "m3", "m4"),
            itens.map { it.chave },
        )
        assertEquals("Ontem", (itens[0] as ItemConversa.Dia).rotulo)
        assertEquals("Hoje", (itens[2] as ItemConversa.Dia).rotulo)
        assertEquals(2, (itens[4] as ItemConversa.Bolha).citada?.id)
        assertNull((itens[5] as ItemConversa.Bolha).citada)
        assertEquals("23:00", horaMensagem(mensagens[0]))
    }

    @Test
    fun `rotulo do dia como no WhatsApp`() {
        val hoje = LocalDate.of(2026, 11, 24)
        assertEquals("Sexta-feira", rotuloDia(LocalDate.of(2026, 11, 20), hoje))
        assertEquals("10/11/2026", rotuloDia(LocalDate.of(2026, 11, 10), hoje))
    }

    @Test
    fun `situacao e autor de cada mensagem`() {
        val ts = "2026-11-24T12:00:00Z"
        assertNull(situacao(msg(1, ts, origem = "user")))
        assertEquals(SituacaoMensagem.AGUARDANDO, situacao(msg(1, ts, pendente = true)))
        assertEquals(SituacaoMensagem.REPROVADA, situacao(msg(1, ts, reprovada = true)))
        assertEquals(SituacaoMensagem.ERRO_ENVIO, situacao(msg(1, ts, erro = "Twilio 63016")))
        assertEquals(SituacaoMensagem.ENVIADA, situacao(msg(1, ts, envio = ts)))
        assertEquals(SituacaoMensagem.APROVADA, situacao(msg(1, ts)))
        assertEquals("Cliente", autor(msg(1, ts, origem = "user")))
        assertEquals("IA", autor(msg(1, ts)))
        assertEquals("Atendente", autor(msg(1, ts, manual = true)))
        assertEquals("Atendente · Beto", autor(msg(1, ts, manual = true).copy(autorNome = "Beto")))
    }

    @Test
    fun `trecho da citacao numa linha e cortado`() {
        assertEquals("a b", trechoCitacao("a\n\n b"))
        assertEquals("x".repeat(90) + "…", trechoCitacao("x".repeat(120)))
    }

    @Test
    fun `assumir, responder e devolver a IA`() = runTest {
        servidor.enqueue(MockResponse().setBody(corpoHistorico))
        servidor.enqueue(MockResponse().setBody(corpoDados.replace("\"humano\"", "\"agente\"")))
        servidor.enqueue(MockResponse().setResponseCode(500)) // config: sem canal, tenta de novo depois
        servidor.enqueue(MockResponse().setBody("""{"id":5,"modo_operacao":"humano","fase":"esclarecendo","status":"ativo"}"""))
        servidor.enqueue(
            MockResponse().setResponseCode(201).setBody(
                """{"id":20,"conteudo":"Já te ligo","origem":"system","timestamp":"2026-11-24T13:05:00Z",
                   "atendimento_id":5,"manual":true,"timestamp_envio":null,"erro_envio":null,"entregue":false}""",
            ),
        )
        servidor.enqueue(
            MockResponse().setResponseCode(201).setBody(
                """{"id":21,"conteudo":"Oi?","origem":"system","timestamp":"2026-11-24T13:06:00Z",
                   "manual":true,"erro_envio":"Twilio 63016: fora da janela de 24h","entregue":false}""",
            ),
        )
        servidor.enqueue(
            MockResponse().setResponseCode(400)
                .setBody("""{"detail":"Atendimento não tem contato com telefone associado"}"""),
        )
        servidor.enqueue(MockResponse().setBody("""{"id":5,"modo_operacao":"agente"}"""))
        val m = modelo(atendimentoIdLista = 99)

        m.carregar()
        repeat(3) { servidor.takeRequest() }
        assertNull(m.estado.value.canalSaida)

        assertNull(m.alterarModo(MODO_HUMANO))
        val patch = servidor.takeRequest()
        assertEquals("PATCH", patch.method)
        // O atendimento ativo de /api/conversa vence o que veio da lista.
        assertEquals("/api/atendimentos/5/modo-operacao", patch.path)
        assertEquals("""{"modo_operacao":"humano"}""", patch.body.readUtf8())
        assertEquals("humano", m.estado.value.dados?.atendimento?.modoOperacao)

        assertEquals(DesfechoEnvio.Simulado, m.enviar("  Já te ligo \n"))
        val post = servidor.takeRequest()
        assertEquals("/api/atendimentos/5/mensagens-manuais", post.path)
        assertEquals("""{"conteudo":"Já te ligo"}""", post.body.readUtf8())
        val gravada = m.estado.value.mensagens.last()
        assertEquals(20, gravada.id)
        assertTrue(gravada.manual)
        assertEquals(SituacaoMensagem.GRAVADA, situacao(gravada))

        val naoEntregue = m.enviar("Oi?")
        assertEquals(DesfechoEnvio.NaoEntregue("Twilio 63016: fora da janela de 24h"), naoEntregue)
        servidor.takeRequest()
        assertEquals(SituacaoMensagem.ERRO_ENVIO, situacao(m.estado.value.mensagens.last()))

        assertEquals(DesfechoEnvio.Falhou("Atendimento não tem contato com telefone associado"), m.enviar("x"))
        servidor.takeRequest()
        assertEquals(listOf(10, 11, 12, 20, 21), m.estado.value.mensagens.map { it.id })

        assertEquals(DesfechoEnvio.Falhou("Mensagem vazia."), m.enviar("   "))
        assertNull(m.alterarModo(MODO_AGENTE))
        assertEquals("agente", m.estado.value.dados?.atendimento?.modoOperacao)
        assertFalse(m.estado.value.ocupado)
    }

    @Test
    fun `sem cabecalho usa o atendimento da lista e erro de modo vem com o motivo`() = runTest {
        servidor.enqueue(MockResponse().setBody(corpoHistorico))
        servidor.enqueue(MockResponse().setResponseCode(500))
        servidor.enqueue(MockResponse().setBody(corpoConfig))
        servidor.enqueue(MockResponse().setResponseCode(404).setBody("""{"detail":"Atendimento não encontrado"}"""))
        val m = modelo(atendimentoIdLista = 99)
        m.carregar()
        repeat(3) { servidor.takeRequest() }

        assertEquals("Atendimento não encontrado", m.alterarModo(MODO_HUMANO))
        assertEquals("/api/atendimentos/99/modo-operacao", servidor.takeRequest().path)
        assertNull(m.estado.value.dados)
        assertFalse(m.estado.value.ocupado)
    }

    @Test
    fun `desfecho do envio, canal e situacao da manual`() {
        val base = MensagemManualEnviada(id = 1, conteudo = "x")
        assertEquals(DesfechoEnvio.Entregue, desfecho(base.copy(entregue = true, timestampEnvio = "2026-11-24T12:00:00Z")))
        assertEquals(DesfechoEnvio.Simulado, desfecho(base))
        assertEquals(DesfechoEnvio.NaoEntregue("63016"), desfecho(base.copy(erroEnvio = "63016")))

        assertEquals("simulado", canalSaida(Rede.json.decodeFromString<ConfiguracoesSistema>(corpoConfig)))
        assertNull(canalSaida(ConfiguracoesSistema()))
        assertTrue(avisoCanal("simulado")!!.contains("não chega ao cliente"))
        assertTrue(avisoCanal("twilio")!!.contains("WhatsApp do cliente"))
        assertNull(avisoCanal(null))

        val ts = "2026-11-24T12:00:00Z"
        assertEquals(SituacaoMensagem.GRAVADA, situacao(msg(1, ts, manual = true)))
        assertEquals(SituacaoMensagem.ENVIADA, situacao(msg(1, ts, manual = true, envio = ts)))
        assertEquals(SituacaoMensagem.ERRO_ENVIO, situacao(msg(1, ts, manual = true, erro = "63016")))
    }
}
