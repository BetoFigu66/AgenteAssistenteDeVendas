package br.com.inforrel.atendente.conversas

import br.com.inforrel.atendente.rede.ApiBackend
import br.com.inforrel.atendente.rede.AtendimentoResumo
import br.com.inforrel.atendente.rede.mensagemDeErro
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.time.format.TextStyle
import java.time.temporal.ChronoUnit
import java.util.Locale

/** Fuso em que o painel mostra os horários (os timestamps vêm em UTC do backend). */
val ZONA_BRASILIA: ZoneId = ZoneId.of("America/Sao_Paulo")

/** Intervalo da atualização automática enquanto a lista está na tela. */
const val INTERVALO_ATUALIZACAO_MS = 15_000L

/**
 * Estado da lista de conversas. [carregou] separa "ainda não chegou nada" de "chegou vazia";
 * [erro] da última tentativa fica junto da lista anterior, que continua na tela.
 */
data class EstadoConversas(
    val conversas: List<AtendimentoResumo> = emptyList(),
    val termo: String = "",
    val carregou: Boolean = false,
    val atualizandoManual: Boolean = false,
    val erro: String? = null,
)

/**
 * Busca a lista em `GET /api/atendimentos/ativas`, mantendo a ordem do backend (a mesma do
 * Acompanhamento do painel). Uma carga por vez: o polling, o puxar para atualizar e a busca
 * passam pelo mesmo [Mutex], e resposta de um termo que já mudou é descartada.
 */
class ModeloConversas(private val api: ApiBackend) {
    private val _estado = MutableStateFlow(EstadoConversas())
    val estado: StateFlow<EstadoConversas> = _estado.asStateFlow()
    private val trava = Mutex()

    fun mudarTermo(termo: String) = _estado.update { it.copy(termo = termo) }

    suspend fun carregar() = trava.withLock {
        val termo = _estado.value.termo.trim()
        try {
            val lista = api.atendimentosAtivos(q = termo.ifEmpty { null }).atendimentos
            if (termo == _estado.value.termo.trim()) {
                _estado.update { it.copy(conversas = lista, carregou = true, erro = null) }
            }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            _estado.update { it.copy(erro = mensagemDeErro(e)) }
        }
    }

    /** Puxar para atualizar: igual a [carregar], com o indicador ligado enquanto dura. */
    suspend fun atualizarManual() {
        _estado.update { it.copy(atualizandoManual = true) }
        try {
            carregar()
        } finally {
            _estado.update { it.copy(atualizandoManual = false) }
        }
    }
}

/** Título da conversa: o nome do contato, senão a empresa, senão o telefone. */
fun tituloConversa(a: AtendimentoResumo): String =
    a.nomeContato?.takeIf { it.isNotBlank() }
        ?: a.empresaNome?.takeIf { it.isNotBlank() }
        ?: formatarTelefone(a.telefone)

/** Iniciais para o avatar (até duas letras); "#" quando o título é só número. */
fun iniciais(titulo: String): String {
    val palavras = titulo.split(' ').filter { p -> p.firstOrNull()?.isLetter() == true }
    return when {
        palavras.isEmpty() -> "#"
        palavras.size == 1 -> palavras[0].take(1).uppercase()
        else -> (palavras.first().take(1) + palavras.last().take(1)).uppercase()
    }
}

/** "+5511999986001" vira "(11) 99998-6001"; fora do padrão brasileiro fica como veio. */
fun formatarTelefone(telefone: String): String {
    val digitos = telefone.filter { it.isDigit() }
    if (!digitos.startsWith("55") || digitos.length !in 12..13) return telefone
    val ddd = digitos.substring(2, 4)
    val numero = digitos.substring(4)
    val corte = numero.length - 4
    return "($ddd) ${numero.substring(0, corte)}-${numero.substring(corte)}"
}

/** Mesmos rótulos do painel (frontend/src/utils/atendimento.js). */
fun rotuloFase(fase: String?): String? = when (fase) {
    null, "" -> null
    "esclarecendo" -> "Esclarecendo"
    "finalizando" -> "Finalizando"
    "em_orcamentacao" -> "Em orçamentação"
    else -> fase
}

fun emModoHumano(a: AtendimentoResumo): Boolean = a.modoOperacao.equals("humano", ignoreCase = true)

/** Momento da última atividade: a última mensagem e, sem ela, o próprio atendimento. */
fun momentoConversa(a: AtendimentoResumo): ZonedDateTime? =
    (a.ultimaMensagem?.timestamp ?: a.ultimaMensagemAt ?: a.updatedAt)?.let(::lerInstante)

/** ISO 8601 do backend (`...Z`, com ou sem fração) em horário de Brasília; null se inválido. */
fun lerInstante(iso: String): ZonedDateTime? =
    runCatching { OffsetDateTime.parse(iso).atZoneSameInstant(ZONA_BRASILIA) }.getOrNull()

private val LOCALE_BR = Locale("pt", "BR")
private val FORMATO_HORA = DateTimeFormatter.ofPattern("HH:mm")
private val FORMATO_DATA = DateTimeFormatter.ofPattern("dd/MM/yyyy")

/** Como a lista do WhatsApp: hoje "14:05", ontem "Ontem", na semana o dia, depois a data. */
fun formatarHorarioLista(momento: ZonedDateTime?, agora: ZonedDateTime = ZonedDateTime.now(ZONA_BRASILIA)): String {
    if (momento == null) return ""
    val dias = ChronoUnit.DAYS.between(momento.toLocalDate(), agora.withZoneSameInstant(ZONA_BRASILIA).toLocalDate())
    return when {
        dias <= 0L -> momento.format(FORMATO_HORA)
        dias == 1L -> "Ontem"
        dias < 7L -> momento.dayOfWeek.getDisplayName(TextStyle.FULL, LOCALE_BR)
        else -> momento.format(FORMATO_DATA)
    }
}

/** Texto da prévia numa linha só (quebras de linha viram espaço). */
fun textoPrevia(a: AtendimentoResumo): String =
    a.ultimaMensagem?.conteudo?.replace(Regex("\\s+"), " ")?.trim().orEmpty()
