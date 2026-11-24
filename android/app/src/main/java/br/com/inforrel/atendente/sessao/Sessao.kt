package br.com.inforrel.atendente.sessao

import br.com.inforrel.atendente.rede.ApiBackend
import br.com.inforrel.atendente.rede.CookieJarPersistente
import br.com.inforrel.atendente.rede.LoginRequest
import br.com.inforrel.atendente.rede.Usuario
import br.com.inforrel.atendente.rede.mensagemDeErro
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import retrofit2.HttpException

sealed interface EstadoSessao {
    /** Abrindo o App com cookie guardado, conferindo em `/api/auth/me`. */
    data object Verificando : EstadoSessao

    /** Sem sessão: tela de login. [aviso] explica por que voltou (ex.: sessão expirada). */
    data class Deslogado(val aviso: String? = null) : EstadoSessao

    /** [semConfirmar]: o servidor não respondeu na abertura e o App seguiu com a sessão guardada. */
    data class Logado(val usuario: Usuario, val semConfirmar: Boolean = false) : EstadoSessao
}

/** Guarda o último usuário logado (nome e login, nunca a senha) para mostrar sem rede. */
interface MemoriaUsuario {
    fun ler(): Usuario?
    fun gravar(usuario: Usuario?)
}

/**
 * Login, logout e validação da sessão. A sessão é só o cookie do [CookieJarPersistente]; a senha
 * vai no corpo do login e não é guardada em lugar nenhum.
 */
class Sessao(
    private val cookieJar: CookieJarPersistente,
    private val memoria: MemoriaUsuario,
) {
    lateinit var api: ApiBackend

    private val _estado = MutableStateFlow<EstadoSessao>(EstadoSessao.Verificando)
    val estado: StateFlow<EstadoSessao> = _estado.asStateFlow()

    /** Chamado na abertura do App. */
    suspend fun validar() {
        if (!cookieJar.temSessao()) {
            _estado.value = EstadoSessao.Deslogado()
            return
        }
        _estado.value = EstadoSessao.Verificando
        try {
            val usuario = api.eu()
            memoria.gravar(usuario)
            _estado.value = EstadoSessao.Logado(usuario)
        } catch (e: CancellationException) {
            throw e
        } catch (e: HttpException) {
            // 401 já passou pelo interceptador (cookie apagado, estado Deslogado). Outro erro HTTP
            // (servidor fora) é tratado como falta de rede.
            if (e.code() != 401) seguirSemConfirmar()
        } catch (e: Exception) {
            seguirSemConfirmar()
        }
    }

    /** Sem rede na abertura: com o usuário lembrado segue logado (a próxima chamada confirma). */
    private fun seguirSemConfirmar() {
        val lembrado = memoria.ler()
        _estado.value = if (lembrado != null) {
            EstadoSessao.Logado(lembrado, semConfirmar = true)
        } else {
            EstadoSessao.Deslogado("Não foi possível confirmar a sessão. Entre de novo.")
        }
    }

    /** Devolve null se entrou, ou a mensagem de erro para a tela de login. */
    suspend fun entrar(login: String, senha: String): String? {
        if (login.isBlank() || senha.isEmpty()) return "Informe usuário e senha."
        return try {
            val usuario = api.login(LoginRequest(login.trim(), senha))
            memoria.gravar(usuario)
            _estado.value = EstadoSessao.Logado(usuario)
            null
        } catch (e: CancellationException) {
            throw e
        } catch (e: HttpException) {
            if (e.code() == 401) "Usuário ou senha inválidos." else mensagemDeErro(e)
        } catch (e: Exception) {
            mensagemDeErro(e)
        }
    }

    /** Avisa o servidor (se der) e apaga a sessão local de qualquer jeito. */
    suspend fun sair() {
        try {
            api.logout()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            // Sem rede o cookie some do aparelho do mesmo jeito; no servidor ele vence sozinho.
        }
        cookieJar.limpar()
        memoria.gravar(null)
        _estado.value = EstadoSessao.Deslogado()
    }

    /** Chamado pelo interceptador quando qualquer chamada leva 401. */
    fun expirou() {
        memoria.gravar(null)
        if (_estado.value !is EstadoSessao.Deslogado) {
            _estado.value = EstadoSessao.Deslogado("Sua sessão expirou. Entre de novo.")
        }
    }
}
