package br.com.inforrel.atendente

import br.com.inforrel.atendente.rede.ApiBackend
import br.com.inforrel.atendente.rede.ArmazemCookies
import br.com.inforrel.atendente.rede.Consulta
import br.com.inforrel.atendente.rede.CookieJarPersistente
import br.com.inforrel.atendente.rede.Rede
import br.com.inforrel.atendente.rede.Usuario
import br.com.inforrel.atendente.rede.consultarVersaoBackend
import br.com.inforrel.atendente.rede.consultarVersaoPublicada
import br.com.inforrel.atendente.rede.mensagemHttp
import br.com.inforrel.atendente.sessao.EstadoSessao
import br.com.inforrel.atendente.sessao.MemoriaUsuario
import br.com.inforrel.atendente.sessao.Sessao
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

private class ArmazemMemoria : ArmazemCookies {
    var dados: Map<String, String> = emptyMap()
    override fun ler() = dados
    override fun gravar(cookies: Map<String, String>) { dados = cookies }
}

private class MemoriaUsuarioFake : MemoriaUsuario {
    var usuario: Usuario? = null
    override fun ler() = usuario
    override fun gravar(usuario: Usuario?) { this.usuario = usuario }
}

/** Login, sessão persistente e 401 contra um servidor falso com as respostas do backend real. */
class RedeSessaoTest {
    private lateinit var servidor: MockWebServer
    private val armazem = ArmazemMemoria()
    private val memoria = MemoriaUsuarioFake()

    // Formato do Set-Cookie do Starlette SessionMiddleware (max_age de 8 h).
    private val setCookieSessao = "session=eyJ1c2VyX2lkIjogMTk3fQ==.assinatura; path=/; Max-Age=28800; httponly; samesite=lax"
    private val corpoUsuario = """{"id":197,"nome":"Beto","login":"beto","tem_senha":true,"created_at":"2026-07-29T19:22:32Z"}"""

    @Before
    fun subir() {
        servidor = MockWebServer().apply { start() }
    }

    @After
    fun derrubar() = servidor.shutdown()

    /** Monta o que o AppAtendente monta, como se o App tivesse acabado de abrir. */
    private fun abrirApp(): Pair<Sessao, ApiBackend> {
        val cookieJar = CookieJarPersistente(armazem)
        val sessao = Sessao(cookieJar, memoria)
        val api = Rede.criarApi(servidor.url("/").toString(), cookieJar, sessao::expirou, timeoutSegundos = 3)
        sessao.api = api
        return sessao to api
    }

    @Test
    fun sem_cookie_guardado_abre_no_login_sem_chamar_o_servidor() = runTest {
        val (sessao, _) = abrirApp()
        sessao.validar()
        assertEquals(EstadoSessao.Deslogado(), sessao.estado.value)
        assertEquals(0, servidor.requestCount)
    }

    @Test
    fun login_valido_entra_e_a_sessao_sobrevive_a_reabrir_o_app() = runTest {
        servidor.enqueue(MockResponse().setBody(corpoUsuario).addHeader("Set-Cookie", setCookieSessao))
        val (sessao, _) = abrirApp()
        assertNull(sessao.entrar("beto", "segredo"))
        assertTrue(sessao.estado.value is EstadoSessao.Logado)
        val login = servidor.takeRequest()
        assertEquals("/api/auth/login", login.path)
        assertEquals("""{"login":"beto","senha":"segredo"}""", login.body.readUtf8())
        // A senha não fica em lugar nenhum: só o cookie e o usuário (sem senha).
        assertFalse(armazem.dados.values.any { "segredo" in it })

        // "Fecha e reabre": jar e sessão novos lendo o mesmo armazém.
        servidor.enqueue(MockResponse().setBody(corpoUsuario).addHeader("Set-Cookie", setCookieSessao))
        val (reaberta, _) = abrirApp()
        reaberta.validar()
        val me = servidor.takeRequest()
        assertEquals("/api/auth/me", me.path)
        assertTrue(me.getHeader("Cookie")!!.startsWith("session=eyJ1c2VyX2lkIjogMTk3fQ==.assinatura"))
        assertEquals(EstadoSessao.Logado(Usuario(197, "Beto", "beto")), reaberta.estado.value)
    }

    @Test
    fun login_invalido_mostra_erro_e_nao_conta_como_sessao_expirada() = runTest {
        servidor.enqueue(MockResponse().setResponseCode(401).setBody("""{"detail":"Login ou senha inválidos"}"""))
        val (sessao, _) = abrirApp()
        assertEquals("Usuário ou senha inválidos.", sessao.entrar("beto", "errada"))
        assertFalse(sessao.estado.value is EstadoSessao.Logado)
    }

    @Test
    fun campos_vazios_nao_chamam_o_servidor() = runTest {
        val (sessao, _) = abrirApp()
        assertEquals("Informe usuário e senha.", sessao.entrar(" ", "x"))
        assertEquals(0, servidor.requestCount)
    }

    @Test
    fun cookie_vencido_no_servidor_volta_ao_login_com_aviso() = runTest {
        servidor.enqueue(MockResponse().setBody(corpoUsuario).addHeader("Set-Cookie", setCookieSessao))
        val (sessao, _) = abrirApp()
        sessao.entrar("beto", "segredo")

        servidor.enqueue(MockResponse().setResponseCode(401).setBody("""{"detail":"Não autenticado"}"""))
        val (reaberta, _) = abrirApp()
        reaberta.validar()
        assertEquals(EstadoSessao.Deslogado("Sua sessão expirou. Entre de novo."), reaberta.estado.value)
        assertTrue(armazem.dados.isEmpty())
        assertNull(memoria.usuario)
    }

    @Test
    fun qualquer_401_depois_de_logado_volta_ao_login() = runTest {
        servidor.enqueue(MockResponse().setBody(corpoUsuario).addHeader("Set-Cookie", setCookieSessao))
        val (sessao, api) = abrirApp()
        sessao.entrar("beto", "segredo")
        servidor.enqueue(MockResponse().setResponseCode(401))
        runCatching { api.eu() }
        assertTrue(sessao.estado.value is EstadoSessao.Deslogado)
        assertFalse(CookieJarPersistente(armazem).temSessao())
    }

    @Test
    fun sem_rede_na_abertura_segue_com_o_usuario_lembrado() = runTest {
        servidor.enqueue(MockResponse().setBody(corpoUsuario).addHeader("Set-Cookie", setCookieSessao))
        abrirApp().first.entrar("beto", "segredo")
        servidor.enqueue(MockResponse().setResponseCode(530))
        val (reaberta, _) = abrirApp()
        reaberta.validar()
        assertEquals(EstadoSessao.Logado(Usuario(197, "Beto", "beto"), semConfirmar = true), reaberta.estado.value)
    }

    @Test
    fun logout_avisa_o_servidor_e_apaga_a_sessao_local() = runTest {
        servidor.enqueue(MockResponse().setBody(corpoUsuario).addHeader("Set-Cookie", setCookieSessao))
        val (sessao, _) = abrirApp()
        sessao.entrar("beto", "segredo")
        // O Starlette responde ao logout expirando o cookie.
        servidor.enqueue(
            MockResponse().setBody("""{"status":"ok"}""")
                .addHeader("Set-Cookie", "session=null; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; httponly; samesite=lax"),
        )
        sessao.sair()
        servidor.takeRequest()
        assertEquals("/api/auth/logout", servidor.takeRequest().path)
        assertEquals(EstadoSessao.Deslogado(), sessao.estado.value)
        assertTrue(armazem.dados.isEmpty())
        assertNull(memoria.usuario)
    }

    @Test
    fun logout_sem_rede_apaga_a_sessao_local_do_mesmo_jeito() = runTest {
        servidor.enqueue(MockResponse().setBody(corpoUsuario).addHeader("Set-Cookie", setCookieSessao))
        val (sessao, _) = abrirApp()
        sessao.entrar("beto", "segredo")
        servidor.shutdown()
        sessao.sair()
        assertEquals(EstadoSessao.Deslogado(), sessao.estado.value)
        assertTrue(armazem.dados.isEmpty())
    }

    @Test
    fun cookie_com_validade_vencida_no_aparelho_e_descartado() {
        // expires 00:20:00 GMT de 1970 = 1.200.000 ms.
        armazem.dados = mapOf("session|localhost|/" to "session=abc; expires=Thu, 01 Jan 1970 00:20:00 GMT; path=/")
        assertTrue(CookieJarPersistente(armazem, agora = { 1_000_000L }).temSessao())
        assertFalse(CookieJarPersistente(armazem, agora = { 1_300_000L }).temSessao())
    }

    @Test
    fun versoes_do_sobre() = runTest {
        val (_, api) = abrirApp()
        servidor.enqueue(MockResponse().setBody("""{"status":"healthy","version":"2026.11.24-1345"}"""))
        assertEquals(Consulta.Ok("2026.11.24-1345"), consultarVersaoBackend(api))
        servidor.enqueue(MockResponse().setBody("""{"status":"healthy"}"""))
        assertEquals(Consulta.Erro("Resposta do servidor sem a versão."), consultarVersaoBackend(api))
        servidor.enqueue(MockResponse().setResponseCode(502).setBody("<html>Bad gateway</html>"))
        assertTrue((consultarVersaoBackend(api) as Consulta.Erro).mensagem.contains("fora do ar"))
        servidor.enqueue(MockResponse().setBody("<html>não é json</html>"))
        assertEquals(Consulta.Erro("Resposta do servidor em formato inesperado."), consultarVersaoBackend(api))
        servidor.enqueue(
            MockResponse().setBody("""{"versao": "2026.11.24-1455", "versionCode": 471775, "data": "x", "commit": "b33b5ba"}"""),
        )
        val publicada = consultarVersaoPublicada(api) as Consulta.Ok
        assertEquals(471775L, publicada.valor.versionCode)
        assertEquals(
            listOf("/health", "/health", "/health", "/health", "/android/versao.json"),
            List(5) { servidor.takeRequest().path },
        )
    }

    @Test
    fun mensagens_http_legiveis() {
        assertTrue(mensagemHttp(530).contains("fora do ar"))
        assertTrue(mensagemHttp(500).contains("HTTP 500"))
    }
}
