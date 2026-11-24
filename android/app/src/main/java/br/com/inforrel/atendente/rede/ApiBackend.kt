package br.com.inforrel.atendente.rede

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

/** Usuário do sistema, como `User.to_dict()` do backend devolve em `/api/auth/login` e `/api/auth/me`. */
@Serializable
data class Usuario(
    val id: Int,
    val nome: String,
    val login: String? = null,
)

@Serializable
data class LoginRequest(val login: String, val senha: String)

/** `GET /health` (público): `{"status": "healthy", "version": "AAAA.MM.DD-HHMM"}`. */
@Serializable
data class Health(val status: String? = null, val version: String? = null)

/**
 * `GET /android/versao.json` (estático, servido pelo nginx; gerado por `scripts/app_publicar.sh`):
 * a versão do APK publicado para download.
 */
@Serializable
data class VersaoPublicada(
    val versao: String,
    @SerialName("versionCode") val versionCode: Long,
)

/**
 * Rotas do backend usadas pelo App. Os próximos goals (conversas, mensagens) acrescentam aqui.
 * A sessão vai no cookie assinado do `SessionMiddleware`, guardado pelo [CookieJarPersistente].
 */
interface ApiBackend {
    @POST("api/auth/login")
    suspend fun login(@Body corpo: LoginRequest): Usuario

    @POST("api/auth/logout")
    suspend fun logout()

    @GET("api/auth/me")
    suspend fun eu(): Usuario

    @GET("health")
    suspend fun health(): Health

    @GET("android/versao.json")
    suspend fun versaoPublicada(): VersaoPublicada
}
