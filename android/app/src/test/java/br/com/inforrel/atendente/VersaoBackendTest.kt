package br.com.inforrel.atendente

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class VersaoBackendTest {
    @Test
    fun health_com_versao() {
        assertEquals(
            VersaoBackend.Ok("2026.11.24-1345"),
            interpretarHealth("""{"status":"healthy","version":"2026.11.24-1345"}"""),
        )
    }

    @Test
    fun health_sem_versao_e_erro() {
        assertTrue(interpretarHealth("""{"status":"healthy"}""") is VersaoBackend.Erro)
    }

    @Test
    fun pagina_html_do_cloudflare_e_erro() {
        assertTrue(interpretarHealth("<html>Bad gateway</html>") is VersaoBackend.Erro)
    }

    @Test
    fun http_do_tunel_fora_diz_que_o_servidor_esta_fora() {
        assertTrue(erroHttp(530).mensagem.contains("fora do ar"))
        assertTrue(erroHttp(502).mensagem.contains("fora do ar"))
        assertTrue(erroHttp(500).mensagem.contains("HTTP 500"))
    }

    @Test
    fun servidor_inexistente_da_erro_legivel() {
        val resultado = consultarVersaoBackend("https://servidor-que-nao-existe.invalid", timeoutMs = 3000)
        assertTrue(resultado is VersaoBackend.Erro)
    }
}

class VersaoAppTest {
    /** O versionCode tem de ser os minutos desde 2026-01-01 do versionName (android/VERSAO). */
    @Test
    fun version_code_derivado_do_version_name() {
        val partes = Regex("""(\d{4})\.(\d{2})\.(\d{2})-(\d{2})(\d{2})""")
            .matchEntire(BuildConfig.VERSION_NAME)!!.groupValues.drop(1).map { it.toInt() }
        val momento = java.time.LocalDateTime.of(partes[0], partes[1], partes[2], partes[3], partes[4])
        val minutos = java.time.temporal.ChronoUnit.MINUTES.between(
            java.time.LocalDateTime.of(2026, 1, 1, 0, 0), momento,
        )
        assertEquals(minutos.toInt(), BuildConfig.VERSION_CODE)
    }
}
