package br.com.inforrel.atendente

import br.com.inforrel.atendente.conversas.ItemConversa
import br.com.inforrel.atendente.conversas.ModeloConversa
import br.com.inforrel.atendente.conversas.SituacaoMensagem
import br.com.inforrel.atendente.conversas.autor
import br.com.inforrel.atendente.conversas.horaMensagem
import br.com.inforrel.atendente.conversas.mesclar
import br.com.inforrel.atendente.conversas.montarItens
import br.com.inforrel.atendente.conversas.rotuloDia
import br.com.inforrel.atendente.conversas.situacao
import br.com.inforrel.atendente.conversas.tituloCabecalho
import br.com.inforrel.atendente.conversas.trechoCitacao
import br.com.inforrel.atendente.rede.ArmazemCookies
import br.com.inforrel.atendente.rede.CookieJarPersistente
import br.com.inforrel.atendente.rede.Mensagem
import br.com.inforrel.atendente.rede.Rede
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
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

    @Before
    fun subir() {
        servidor = MockWebServer().apply { start() }
    }

    @After
    fun derrubar() = servidor.shutdown()

    private fun modelo(): ModeloConversa {
        val armazem = object : ArmazemCookies {
            override fun ler() = emptyMap<String, String>()
            override fun gravar(cookies: Map<String, String>) {}
        }
        val api = Rede.criarApi(servidor.url("/").toString(), CookieJarPersistente(armazem), {}, timeoutSegundos = 3)
        return ModeloConversa(api, "+5519998986565")
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
    }

    @Test
    fun `trecho da citacao numa linha e cortado`() {
        assertEquals("a b", trechoCitacao("a\n\n b"))
        assertEquals("x".repeat(90) + "…", trechoCitacao("x".repeat(120)))
    }
}
