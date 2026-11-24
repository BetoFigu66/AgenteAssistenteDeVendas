package br.com.inforrel.atendente.rede

import android.content.SharedPreferences
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl

/** Onde os cookies ficam guardados entre aberturas do App. Interface para o teste usar memória. */
interface ArmazemCookies {
    fun ler(): Map<String, String>
    fun gravar(cookies: Map<String, String>)
}

/** [ArmazemCookies] nas SharedPreferences privadas do App (o manifesto não permite backup). */
class ArmazemCookiesPrefs(private val prefs: SharedPreferences) : ArmazemCookies {
    override fun ler(): Map<String, String> =
        prefs.all.mapNotNull { (chave, valor) -> (valor as? String)?.let { chave to it } }.toMap()

    override fun gravar(cookies: Map<String, String>) {
        prefs.edit().clear().apply { cookies.forEach { (k, v) -> putString(k, v) } }.apply()
    }
}

/**
 * CookieJar que sobrevive a fechar o App: guarda cada cookie no [ArmazemCookies] no formato do
 * `Set-Cookie` (com `expires`) e descarta os vencidos ao ler.
 *
 * O único cookie que o backend manda é o `session` do Starlette `SessionMiddleware`: assinado,
 * `Max-Age` = `SESSION_MAX_AGE_SEGUNDOS` (8 h), `path=/`, `samesite=lax`, sem `secure`. O
 * middleware o reenvia em toda resposta enquanto a sessão tiver dados, então as 8 h contam da
 * última chamada, e a assinatura também vence em 8 h no servidor. Sessão vencida vira 401, que o
 * [InterceptadorSessao] trata. Senha nunca passa por aqui: só o cookie.
 */
class CookieJarPersistente(
    private val armazem: ArmazemCookies,
    private val agora: () -> Long = System::currentTimeMillis,
) : CookieJar {
    private val cookies = mutableMapOf<String, Cookie>()

    init {
        // A URL só serve ao parse; domínio e path vêm do próprio texto guardado.
        armazem.ler().forEach { (chave, texto) ->
            val dominio = chave.split('|').getOrNull(1) ?: return@forEach
            val url = HttpUrl.Builder().scheme("https").host(dominio).build()
            Cookie.parse(url, texto)?.let { cookies[chave] = it }
        }
        removerVencidos()
    }

    @Synchronized
    override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        cookies.forEach { this.cookies[chave(it)] = it }
        removerVencidos()
        persistir()
    }

    @Synchronized
    override fun loadForRequest(url: HttpUrl): List<Cookie> {
        if (removerVencidos()) persistir()
        return cookies.values.filter { it.matches(url) }
    }

    /** Há cookie de sessão válido guardado? Decide, na abertura, se vale validar com `/api/auth/me`. */
    @Synchronized
    fun temSessao(): Boolean {
        removerVencidos()
        return cookies.values.any { it.name == NOME_COOKIE_SESSAO }
    }

    @Synchronized
    fun limpar() {
        cookies.clear()
        persistir()
    }

    private fun removerVencidos(): Boolean {
        val momento = agora()
        return cookies.values.removeAll { it.expiresAt <= momento }
    }

    private fun persistir() = armazem.gravar(cookies.mapValues { it.value.toString() })

    private fun chave(cookie: Cookie) = "${cookie.name}|${cookie.domain}|${cookie.path}"

    companion object {
        /** Nome padrão do cookie do Starlette `SessionMiddleware` (o backend não muda). */
        const val NOME_COOKIE_SESSAO = "session"
    }
}
