package br.com.inforrel.atendente.rede

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

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

/** Prévia da última mensagem de um atendimento (`ultima_mensagem` em `/api/atendimentos/ativas`). */
@Serializable
data class PreviaMensagem(
    val id: Int,
    val conteudo: String,
    /** "user" (cliente) ou "system" (agente ou atendente). */
    val origem: String,
    val timestamp: String? = null,
    @SerialName("pendente_aprovacao") val pendenteAprovacao: Boolean = false,
)

/** Um item de `GET /api/atendimentos/ativas` (backend/main.py, `listar_atendimentos_ativos`). */
@Serializable
data class AtendimentoResumo(
    val id: Int,
    val status: String? = null,
    @SerialName("modo_operacao") val modoOperacao: String? = null,
    val fase: String? = null,
    val titulo: String? = null,
    val telefone: String,
    @SerialName("nome_contato") val nomeContato: String? = null,
    @SerialName("empresa_nome") val empresaNome: String? = null,
    @SerialName("mensagens_pendentes") val mensagensPendentes: Int = 0,
    @SerialName("updated_at") val updatedAt: String? = null,
    @SerialName("ultima_mensagem_at") val ultimaMensagemAt: String? = null,
    @SerialName("ultima_mensagem") val ultimaMensagem: PreviaMensagem? = null,
)

@Serializable
data class ListaAtendimentos(
    val total: Int = 0,
    val atendimentos: List<AtendimentoResumo> = emptyList(),
)

/** Uma mensagem de `GET /api/historico/{telefone}` (`Mensagem.to_dict()` mais `reprovada`). */
@Serializable
data class Mensagem(
    val id: Int,
    val conteudo: String,
    /** "user" (cliente) ou "system" (IA ou atendente, ver [manual]). */
    val origem: String,
    val timestamp: String? = null,
    @SerialName("atendimento_id") val atendimentoId: Int? = null,
    @SerialName("resposta_a_mensagem_id") val respostaAMensagemId: Int? = null,
    @SerialName("timestamp_envio") val timestampEnvio: String? = null,
    @SerialName("erro_envio") val erroEnvio: String? = null,
    @SerialName("pendente_aprovacao") val pendenteAprovacao: Boolean = false,
    /** Escrita pelo atendente, não pela IA. */
    val manual: Boolean = false,
    /** Nome de quem escreveu a resposta manual (o usuário logado que enviou). */
    @SerialName("autor_nome") val autorNome: String? = null,
    val reprovada: Boolean = false,
)

@Serializable
data class Historico(val mensagens: List<Mensagem> = emptyList())

@Serializable
data class ContatoConversa(val nome: String? = null)

@Serializable
data class EmpresaConversa(val nome: String? = null, val fantasia: String? = null)

@Serializable
data class AtendimentoConversa(
    val id: Int,
    @SerialName("modo_operacao") val modoOperacao: String? = null,
    val fase: String? = null,
)

/** `GET /api/conversa/{telefone}`: o que o cabeçalho da conversa usa (o resto é ignorado). */
@Serializable
data class DadosConversa(
    val contato: ContatoConversa? = null,
    val empresa: EmpresaConversa? = null,
    val pessoa: ContatoConversa? = null,
    val atendimento: AtendimentoConversa? = null,
)

/** Corpo de `PATCH /api/atendimentos/{id}/modo-operacao`: "agente" ou "humano". */
@Serializable
data class AlterarModoRequest(@SerialName("modo_operacao") val modoOperacao: String)

/** Corpo de `POST /api/atendimentos/{id}/mensagens-manuais` (o backend não aceita citação). */
@Serializable
data class MensagemManualRequest(val conteudo: String)

/**
 * Resposta de `POST /api/atendimentos/{id}/mensagens-manuais`: a mensagem gravada mais o
 * desfecho da entrega. `entregue=false` sem `erro_envio` é o canal simulado (nada sai);
 * com `erro_envio`, tentou e falhou (ex.: janela de 24 h do WhatsApp, Twilio 63016).
 */
@Serializable
data class MensagemManualEnviada(
    val id: Int,
    val conteudo: String,
    val origem: String = "system",
    val timestamp: String? = null,
    @SerialName("atendimento_id") val atendimentoId: Int? = null,
    @SerialName("timestamp_envio") val timestampEnvio: String? = null,
    @SerialName("erro_envio") val erroEnvio: String? = null,
    val entregue: Boolean = false,
) {
    fun comoMensagem() = Mensagem(
        id = id, conteudo = conteudo, origem = origem, timestamp = timestamp, atendimentoId = atendimentoId,
        timestampEnvio = timestampEnvio, erroEnvio = erroEnvio, manual = true,
    )
}

/** Um item de `GET /api/config/sistema` (configurações do `.env`, segredos já mascarados). */
@Serializable
data class ItemConfiguracao(val nome: String, val valor: JsonElement? = null)

@Serializable
data class ConfiguracoesSistema(val configuracoes: List<ItemConfiguracao> = emptyList())

/**
 * Rotas do backend usadas pelo App; cada goal da série acrescenta as suas aqui.
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

    /**
     * Atendimentos ativos, na ordem do Acompanhamento do painel (pendências de aprovação
     * primeiro, depois a conversa mais recente). [q] busca por telefone, contato ou empresa.
     */
    @GET("api/atendimentos/ativas")
    suspend fun atendimentosAtivos(
        @Query("q") q: String? = null,
        @Query("limit") limit: Int = LIMITE_CONVERSAS,
    ): ListaAtendimentos

    /** As [limit] mensagens mais recentes do telefone, em ordem cronológica (o painel usa 200). */
    @GET("api/historico/{telefone}")
    suspend fun historico(@Path("telefone") telefone: String, @Query("limit") limit: Int): Historico

    @GET("api/conversa/{telefone}")
    suspend fun dadosConversa(@Path("telefone") telefone: String): DadosConversa

    /** Assumir (humano) ou devolver à IA (agente). Devolve o atendimento atualizado. */
    @PATCH("api/atendimentos/{id}/modo-operacao")
    suspend fun alterarModo(@Path("id") atendimentoId: Int, @Body corpo: AlterarModoRequest): AtendimentoConversa

    @POST("api/atendimentos/{id}/mensagens-manuais")
    suspend fun enviarMensagemManual(@Path("id") atendimentoId: Int, @Body corpo: MensagemManualRequest): MensagemManualEnviada

    /** Usado só para ler `CANAL_SAIDA` (se a resposta manual chega ou não ao cliente). */
    @GET("api/config/sistema")
    suspend fun configuracoesSistema(): ConfiguracoesSistema

    companion object {
        /** Máximo que o backend aceita numa página; o App não pagina. */
        const val LIMITE_CONVERSAS = 200
    }
}
