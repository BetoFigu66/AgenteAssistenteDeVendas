package br.com.inforrel.atendente

import br.com.inforrel.atendente.conversas.ModeloConversas
import br.com.inforrel.atendente.conversas.ZONA_BRASILIA
import br.com.inforrel.atendente.conversas.emModoHumano
import br.com.inforrel.atendente.conversas.formatarHorarioLista
import br.com.inforrel.atendente.conversas.formatarTelefone
import br.com.inforrel.atendente.conversas.iniciais
import br.com.inforrel.atendente.conversas.lerInstante
import br.com.inforrel.atendente.conversas.momentoConversa
import br.com.inforrel.atendente.conversas.rotuloFase
import br.com.inforrel.atendente.conversas.textoPrevia
import br.com.inforrel.atendente.conversas.tituloConversa
import br.com.inforrel.atendente.rede.AtendimentoResumo
import br.com.inforrel.atendente.rede.CookieJarPersistente
import br.com.inforrel.atendente.rede.ArmazemCookies
import br.com.inforrel.atendente.rede.Rede
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.time.ZonedDateTime

/** Lista de conversas: leitura de `/api/atendimentos/ativas` e a formatação de cada linha. */
class ConversasTest {
    private lateinit var servidor: MockWebServer

    // Recorte de uma resposta real do backend (backend/main.py, listar_atendimentos_ativos).
    private val corpoLista = """
        {"total":2,"page":1,"limit":200,"atendimentos":[
          {"id":42,"numero_atendimento_cliente":3,"status":"ativo","modo_operacao":"humano",
           "motivo_escalonamento":"reclamacao","fase":"finalizando","titulo":null,
           "telefone":"+5519998986565","nome_contato":"Maria Souza","empresa_id":7,
           "empresa_nome":"Acme","mensagens_pendentes":2,"updated_at":"2026-11-24T17:00:00Z",
           "ultima_mensagem_at":"2026-11-24T17:05:12.345678Z",
           "ultima_mensagem":{"id":900,"conteudo":"Qual a quantidade?\nE o modelo?","origem":"system",
             "timestamp":"2026-11-24T17:05:12.345678Z","pendente_aprovacao":true}},
          {"id":43,"numero_atendimento_cliente":null,"status":"ativo","modo_operacao":"agente",
           "fase":null,"telefone":"+5511999964007","nome_contato":null,"empresa_id":null,
           "empresa_nome":null,"mensagens_pendentes":0,"updated_at":"2026-11-20T10:00:00Z",
           "ultima_mensagem_at":null,"ultima_mensagem":null}
        ]}
    """.trimIndent()

    @Before
    fun subir() {
        servidor = MockWebServer().apply { start() }
    }

    @After
    fun derrubar() = servidor.shutdown()

    private fun modelo(): ModeloConversas {
        val armazem = object : ArmazemCookies {
            override fun ler() = emptyMap<String, String>()
            override fun gravar(cookies: Map<String, String>) {}
        }
        val api = Rede.criarApi(servidor.url("/").toString(), CookieJarPersistente(armazem), {}, timeoutSegundos = 3)
        return ModeloConversas(api)
    }

    @Test
    fun `carrega a lista na ordem do backend com a previa`() = runTest {
        servidor.enqueue(MockResponse().setBody(corpoLista))
        val m = modelo()
        m.carregar()

        val req = servidor.takeRequest()
        assertEquals("/api/atendimentos/ativas?limit=200", req.path)
        val estado = m.estado.value
        assertTrue(estado.carregou)
        assertNull(estado.erro)
        assertEquals(listOf(42, 43), estado.conversas.map { it.id })
        val primeira = estado.conversas[0]
        assertEquals(2, primeira.mensagensPendentes)
        assertTrue(emModoHumano(primeira))
        assertTrue(primeira.ultimaMensagem!!.pendenteAprovacao)
        assertEquals("Qual a quantidade? E o modelo?", textoPrevia(primeira))
        assertFalse(emModoHumano(estado.conversas[1]))
        assertEquals("", textoPrevia(estado.conversas[1]))
    }

    @Test
    fun `busca vai no parametro q e erro mantem a lista anterior`() = runTest {
        servidor.enqueue(MockResponse().setBody(corpoLista))
        servidor.enqueue(MockResponse().setResponseCode(502))
        val m = modelo()
        m.carregar()
        servidor.takeRequest()

        m.mudarTermo(" maria ")
        m.carregar()
        assertEquals("/api/atendimentos/ativas?q=maria&limit=200", servidor.takeRequest().path)
        val estado = m.estado.value
        assertEquals(2, estado.conversas.size)
        assertEquals("Servidor fora do ar no momento (HTTP 502).", estado.erro)
    }

    @Test
    fun `atualizar manual liga e desliga o indicador`() = runTest {
        servidor.enqueue(MockResponse().setBody(corpoLista))
        val m = modelo()
        m.atualizarManual()
        assertFalse(m.estado.value.atualizandoManual)
        assertTrue(m.estado.value.carregou)
    }

    private fun resumo(nome: String? = null, empresa: String? = null, telefone: String = "+5511999964007") =
        AtendimentoResumo(id = 1, telefone = telefone, nomeContato = nome, empresaNome = empresa)

    @Test
    fun `titulo cai do contato para a empresa e para o telefone`() {
        assertEquals("Maria", tituloConversa(resumo(nome = "Maria", empresa = "Acme")))
        assertEquals("Acme", tituloConversa(resumo(nome = " ", empresa = "Acme")))
        assertEquals("(11) 99996-4007", tituloConversa(resumo()))
    }

    @Test
    fun `telefone e iniciais`() {
        assertEquals("(19) 9898-6565", formatarTelefone("+551998986565"))
        assertEquals("+14155238886", formatarTelefone("+14155238886"))
        assertEquals("MS", iniciais("Maria da Silva Souza"))
        assertEquals("A", iniciais("Acme"))
        assertEquals("#", iniciais("(11) 99996-4007"))
    }

    @Test
    fun `fase com os rotulos do painel`() {
        assertEquals("Em orçamentação", rotuloFase("em_orcamentacao"))
        assertEquals("Finalizando", rotuloFase("finalizando"))
        assertNull(rotuloFase(null))
    }

    @Test
    fun `horario em Brasilia como a lista do WhatsApp`() {
        // 24/11/2026 18:00 em Brasília (terça-feira).
        val agora = ZonedDateTime.of(2026, 11, 24, 18, 0, 0, 0, ZONA_BRASILIA)
        // 17:05 UTC = 14:05 em Brasília.
        assertEquals("14:05", formatarHorarioLista(lerInstante("2026-11-24T17:05:12.345678Z"), agora))
        // 02:30 UTC do dia 24 ainda é dia 23 em Brasília.
        assertEquals("Ontem", formatarHorarioLista(lerInstante("2026-11-24T02:30:00Z"), agora))
        assertEquals("sexta-feira", formatarHorarioLista(lerInstante("2026-11-20T15:00:00Z"), agora))
        assertEquals("10/11/2026", formatarHorarioLista(lerInstante("2026-11-10T15:00:00Z"), agora))
        assertEquals("", formatarHorarioLista(null, agora))
        assertNull(lerInstante("lixo"))
    }

    @Test
    fun `momento vem da ultima mensagem e cai para o atendimento`() {
        val semMensagem = resumo().copy(updatedAt = "2026-11-20T10:00:00Z")
        assertNotNull(momentoConversa(semMensagem))
        assertEquals(7, momentoConversa(semMensagem)!!.hour)
        assertNull(momentoConversa(resumo()))
    }
}
