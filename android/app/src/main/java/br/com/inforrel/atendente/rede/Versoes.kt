package br.com.inforrel.atendente.rede

/** Resultado de uma consulta de versão para a tela Sobre: o valor, ou um erro legível. */
sealed interface Consulta<out T> {
    data object Carregando : Consulta<Nothing>
    data class Ok<T>(val valor: T) : Consulta<T>
    data class Erro(val mensagem: String) : Consulta<Nothing>
}

/** Versão do backend em `GET /health`. */
suspend fun consultarVersaoBackend(api: ApiBackend): Consulta<String> = consultar {
    api.health().version?.takeIf { it.isNotBlank() } ?: throw SemVersao()
}

/** Versão do APK publicado em `/android/versao.json`. */
suspend fun consultarVersaoPublicada(api: ApiBackend): Consulta<VersaoPublicada> = consultar { api.versaoPublicada() }

/** Há versão mais nova do App para baixar? Compara pelo versionCode, que cresce a cada versão. */
fun haVersaoNova(publicada: VersaoPublicada, versionCodeInstalado: Long): Boolean =
    publicada.versionCode > versionCodeInstalado

private suspend fun <T> consultar(bloco: suspend () -> T): Consulta<T> = try {
    Consulta.Ok(bloco())
} catch (e: kotlinx.coroutines.CancellationException) {
    throw e
} catch (e: SemVersao) {
    Consulta.Erro("Resposta do servidor sem a versão.")
} catch (e: Exception) {
    Consulta.Erro(mensagemDeErro(e))
}

private class SemVersao : Exception()
