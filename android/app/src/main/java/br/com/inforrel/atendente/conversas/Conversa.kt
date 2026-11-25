package br.com.inforrel.atendente.conversas

import br.com.inforrel.atendente.rede.ApiBackend
import br.com.inforrel.atendente.rede.DadosConversa
import br.com.inforrel.atendente.rede.Mensagem
import br.com.inforrel.atendente.rede.mensagemDeErro
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.time.Instant
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.format.TextStyle
import java.time.temporal.ChronoUnit
import java.util.Locale

/** Mesmo limite do painel na abertura (`/api/historico` sem `limit` devolve 200). */
const val LIMITE_HISTORICO = 200

/** Nas atualizações, só as mais recentes: o bastante para mensagens novas e mudanças de estado. */
const val LIMITE_ATUALIZACAO = 50

/** Conversa aberta é mais viva que a lista: atualiza mais vezes (pedindo pouco, ver acima). */
const val INTERVALO_CONVERSA_MS = 5_000L

data class EstadoConversa(
    val mensagens: List<Mensagem> = emptyList(),
    val dados: DadosConversa? = null,
    val carregou: Boolean = false,
    val erro: String? = null,
)

/**
 * Mensagens de um telefone, como o painel mostra (`GET /api/historico/{telefone}`). A
 * primeira carga traz [LIMITE_HISTORICO]; as seguintes, [LIMITE_ATUALIZACAO], mescladas por id.
 */
class ModeloConversa(private val api: ApiBackend, private val telefone: String) {
    private val _estado = MutableStateFlow(EstadoConversa())
    val estado: StateFlow<EstadoConversa> = _estado.asStateFlow()
    private val trava = Mutex()

    suspend fun carregar() = trava.withLock {
        val primeira = !_estado.value.carregou
        try {
            val recebidas = api.historico(telefone, if (primeira) LIMITE_HISTORICO else LIMITE_ATUALIZACAO).mensagens
            _estado.update {
                it.copy(
                    mensagens = if (primeira) recebidas else mesclar(it.mensagens, recebidas),
                    carregou = true,
                    erro = null,
                )
            }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            _estado.update { it.copy(erro = mensagemDeErro(e)) }
            return@withLock
        }
        // Cabeçalho à parte: sem ele a conversa continua legível, com o título da lista.
        try {
            val dados = api.dadosConversa(telefone)
            _estado.update { it.copy(dados = dados) }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            // mantém o cabeçalho anterior
        }
    }
}

/** Junta a lista atual com as recebidas: a versão recebida vence (estado novo), ordem cronológica. */
fun mesclar(atuais: List<Mensagem>, recebidas: List<Mensagem>): List<Mensagem> {
    val porId = LinkedHashMap<Int, Mensagem>()
    atuais.forEach { porId[it.id] = it }
    recebidas.forEach { porId[it.id] = it }
    return porId.values.sortedWith(compareBy<Mensagem>({ instante(it) }, { it.id }))
}

private fun instante(m: Mensagem): Instant = m.timestamp?.let(::lerInstante)?.toInstant() ?: Instant.EPOCH

/** Situação de uma mensagem do sistema; null para mensagem do cliente. */
enum class SituacaoMensagem(val rotulo: String) {
    AGUARDANDO("Aguardando aprovação"),
    REPROVADA("Reprovada"),
    ERRO_ENVIO("Não entregue"),
    ENVIADA("Enviada"),
    APROVADA("Aprovada"),
}

fun situacao(m: Mensagem): SituacaoMensagem? = when {
    m.origem != "system" -> null
    m.pendenteAprovacao -> SituacaoMensagem.AGUARDANDO
    m.reprovada -> SituacaoMensagem.REPROVADA
    !m.erroEnvio.isNullOrBlank() -> SituacaoMensagem.ERRO_ENVIO
    m.timestampEnvio != null -> SituacaoMensagem.ENVIADA
    // Aprovada e sem envio: com o canal simulado é o normal (nada sai para o WhatsApp).
    else -> SituacaoMensagem.APROVADA
}

fun ehDoCliente(m: Mensagem): Boolean = m.origem != "system"

fun autor(m: Mensagem): String = when {
    ehDoCliente(m) -> "Cliente"
    m.manual -> "Atendente"
    else -> "IA"
}

/** O que a lista da conversa desenha: separador de dia ou bolha (com a citada já resolvida). */
sealed interface ItemConversa {
    val chave: String

    data class Dia(val rotulo: String, override val chave: String) : ItemConversa

    data class Bolha(
        val mensagem: Mensagem,
        /** A mensagem citada (reply-to), se está entre as carregadas. */
        val citada: Mensagem?,
    ) : ItemConversa {
        override val chave = "m${mensagem.id}"
    }
}

/** Mensagens em ordem com um separador antes do primeiro de cada dia (horário de Brasília). */
fun montarItens(mensagens: List<Mensagem>, hoje: LocalDate = LocalDate.now(ZONA_BRASILIA)): List<ItemConversa> {
    val porId = mensagens.associateBy { it.id }
    val itens = ArrayList<ItemConversa>(mensagens.size + 8)
    var diaAnterior: LocalDate? = null
    for (m in mensagens) {
        val dia = m.timestamp?.let(::lerInstante)?.toLocalDate()
        if (dia != null && dia != diaAnterior) {
            itens += ItemConversa.Dia(rotuloDia(dia, hoje), "d$dia")
            diaAnterior = dia
        }
        itens += ItemConversa.Bolha(m, m.respostaAMensagemId?.let(porId::get))
    }
    return itens
}

private val LOCALE_BR = Locale("pt", "BR")
private val FORMATO_DIA = DateTimeFormatter.ofPattern("dd/MM/yyyy")
private val FORMATO_HORA = DateTimeFormatter.ofPattern("HH:mm")

/** Separador de dia como no WhatsApp: "Hoje", "Ontem", o dia da semana até 6 dias, depois a data. */
fun rotuloDia(dia: LocalDate, hoje: LocalDate): String {
    val dias = ChronoUnit.DAYS.between(dia, hoje)
    return when {
        dias <= 0L -> "Hoje"
        dias == 1L -> "Ontem"
        dias < 7L -> dia.dayOfWeek.getDisplayName(TextStyle.FULL, LOCALE_BR).replaceFirstChar { it.uppercase() }
        else -> dia.format(FORMATO_DIA)
    }
}

/** Horário da bolha, em Brasília. */
fun horaMensagem(m: Mensagem): String = m.timestamp?.let(::lerInstante)?.format(FORMATO_HORA).orEmpty()

/** Trecho da citação, numa linha. */
fun trechoCitacao(texto: String, limite: Int = 90): String {
    val linha = texto.replace(Regex("\\s+"), " ").trim()
    return if (linha.length > limite) linha.take(limite) + "…" else linha
}

/** Nome do cabeçalho: contato, pessoa ou empresa do backend; senão o título vindo da lista. */
fun tituloCabecalho(dados: DadosConversa?, tituloLista: String): String =
    listOfNotNull(
        dados?.contato?.nome,
        dados?.pessoa?.nome,
        dados?.empresa?.fantasia,
        dados?.empresa?.nome,
    ).firstOrNull { it.isNotBlank() } ?: tituloLista
