package br.com.inforrel.atendente.rede

import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Response
import retrofit2.HttpException
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.io.IOException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.util.concurrent.TimeUnit

/**
 * 401 em qualquer chamada, menos no próprio login (onde 401 é "senha errada"), quer dizer que a
 * sessão acabou: apaga o cookie e avisa quem cuida da sessão, que volta o App para o login.
 */
class InterceptadorSessao(
    private val cookieJar: CookieJarPersistente,
    private val aoExpirar: () -> Unit,
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val resposta = chain.proceed(chain.request())
        if (resposta.code == 401 && !chain.request().url.encodedPath.endsWith(CAMINHO_LOGIN)) {
            cookieJar.limpar()
            aoExpirar()
        }
        return resposta
    }

    companion object {
        const val CAMINHO_LOGIN = "/api/auth/login"
    }
}

/** Monta a camada de rede única do App: um OkHttpClient com o cookie persistente e o Retrofit. */
object Rede {
    val json = Json { ignoreUnknownKeys = true }

    fun criarApi(
        urlBase: String,
        cookieJar: CookieJarPersistente,
        aoExpirarSessao: () -> Unit,
        timeoutSegundos: Long = 15,
    ): ApiBackend {
        val cliente = OkHttpClient.Builder()
            .cookieJar(cookieJar)
            .addInterceptor(InterceptadorSessao(cookieJar, aoExpirarSessao))
            .connectTimeout(timeoutSegundos, TimeUnit.SECONDS)
            .readTimeout(timeoutSegundos, TimeUnit.SECONDS)
            .build()
        return Retrofit.Builder()
            .baseUrl(urlBase.trimEnd('/') + "/")
            .client(cliente)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(ApiBackend::class.java)
    }
}

/** Mensagem legível para a tela a partir de uma falha de chamada ao backend. */
fun mensagemDeErro(erro: Throwable): String = when (erro) {
    is HttpException -> mensagemHttp(erro.code())
    is UnknownHostException -> "Sem internet ou servidor não encontrado."
    is SocketTimeoutException -> "O servidor demorou demais para responder."
    is SerializationException -> "Resposta do servidor em formato inesperado."
    is IOException -> "Não foi possível falar com o servidor (${erro.javaClass.simpleName})."
    else -> "Erro inesperado (${erro.javaClass.simpleName})."
}

/** 502 a 530 vêm do Cloudflare com o túnel ou o backend fora. */
fun mensagemHttp(codigo: Int): String = when (codigo) {
    401 -> "Sessão encerrada. Entre de novo."
    in 502..504, 530 -> "Servidor fora do ar no momento (HTTP $codigo)."
    else -> "O servidor respondeu com erro (HTTP $codigo)."
}
