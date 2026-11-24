package br.com.inforrel.atendente

import br.com.inforrel.atendente.rede.VersaoPublicada
import br.com.inforrel.atendente.rede.haVersaoNova
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

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

    @Test
    fun versao_nova_so_quando_o_publicado_e_maior() {
        assertTrue(haVersaoNova(VersaoPublicada("2026.11.24-1600", 471840), 471775))
        assertFalse(haVersaoNova(VersaoPublicada("2026.11.24-1455", 471775), 471775))
        assertFalse(haVersaoNova(VersaoPublicada("2026.11.24-1400", 471720), 471775))
    }
}
