package br.com.inforrel.atendente

import android.app.Application
import android.content.Context
import android.content.SharedPreferences
import br.com.inforrel.atendente.rede.ApiBackend
import br.com.inforrel.atendente.rede.ArmazemCookiesPrefs
import br.com.inforrel.atendente.rede.CookieJarPersistente
import br.com.inforrel.atendente.rede.Rede
import br.com.inforrel.atendente.rede.Usuario
import br.com.inforrel.atendente.sessao.MemoriaUsuario
import br.com.inforrel.atendente.sessao.Sessao
import kotlinx.coroutines.MainScope
import kotlinx.coroutines.launch

/** Monta, uma vez por processo, a camada de rede e a sessão que as telas usam. */
class AppAtendente : Application() {
    lateinit var api: ApiBackend
        private set
    lateinit var sessao: Sessao
        private set

    override fun onCreate() {
        super.onCreate()
        val cookieJar = CookieJarPersistente(
            ArmazemCookiesPrefs(getSharedPreferences("cookies", Context.MODE_PRIVATE)),
        )
        sessao = Sessao(cookieJar, MemoriaUsuarioPrefs(getSharedPreferences("sessao", Context.MODE_PRIVATE)))
        api = Rede.criarApi(BuildConfig.BACKEND_URL, cookieJar, aoExpirarSessao = sessao::expirou)
        sessao.api = api
        // Confere a sessão guardada uma vez por processo, fora da Activity: girar a tela recria a
        // Activity e não pode cancelar nem repetir a validação.
        MainScope().launch { sessao.validar() }
    }
}

private class MemoriaUsuarioPrefs(private val prefs: SharedPreferences) : MemoriaUsuario {
    override fun ler(): Usuario? = prefs.getString("usuario", null)?.let {
        runCatching { Rede.json.decodeFromString(Usuario.serializer(), it) }.getOrNull()
    }

    override fun gravar(usuario: Usuario?) {
        prefs.edit().apply {
            if (usuario == null) remove("usuario") else putString("usuario", Rede.json.encodeToString(Usuario.serializer(), usuario))
        }.apply()
    }
}
