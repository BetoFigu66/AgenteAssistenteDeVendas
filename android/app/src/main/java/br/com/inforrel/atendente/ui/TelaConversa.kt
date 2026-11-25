package br.com.inforrel.atendente.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Create
import androidx.compose.material.icons.filled.Done
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SmallFloatingActionButton
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import br.com.inforrel.atendente.conversas.INTERVALO_CONVERSA_MS
import br.com.inforrel.atendente.conversas.ItemConversa
import br.com.inforrel.atendente.conversas.ModeloConversa
import br.com.inforrel.atendente.conversas.SituacaoMensagem
import br.com.inforrel.atendente.conversas.autor
import br.com.inforrel.atendente.conversas.ehDoCliente
import br.com.inforrel.atendente.conversas.formatarTelefone
import br.com.inforrel.atendente.conversas.horaMensagem
import br.com.inforrel.atendente.conversas.montarItens
import br.com.inforrel.atendente.conversas.situacao
import br.com.inforrel.atendente.conversas.tituloCabecalho
import br.com.inforrel.atendente.conversas.trechoCitacao
import br.com.inforrel.atendente.rede.Mensagem
import kotlinx.coroutines.launch

/**
 * Conversa de um telefone, só leitura (aprovar e responder ficam para os próximos goals):
 * cliente à esquerda, IA e atendente à direita, separador por dia, citação, horário e
 * situação de cada mensagem do sistema. Abre na última mensagem e, ao chegar mensagem nova,
 * só desce sozinha se o usuário já estava no fim.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TelaConversa(
    modelo: ModeloConversa,
    telefone: String,
    tituloLista: String,
    modoLista: String?,
    aoVoltar: () -> Unit,
) {
    BackHandler(onBack = aoVoltar)
    val estado by modelo.estado.collectAsState()
    AtualizacaoPeriodica(INTERVALO_CONVERSA_MS) { modelo.carregar() }

    val itens = remember(estado.mensagens) { montarItens(estado.mensagens) }
    val lista = rememberLazyListState()
    val escopo = rememberCoroutineScope()

    // Rolagem: na primeira carga vai para o fim; depois, só segue o fim se a última mensagem
    // anterior estava visível (o usuário não tinha subido para ler o passado).
    val ultimaChave = itens.lastOrNull()?.chave
    var chaveAnterior by remember { mutableStateOf<String?>(null) }
    LaunchedEffect(ultimaChave) {
        if (ultimaChave == null) return@LaunchedEffect
        val anterior = chaveAnterior
        chaveAnterior = ultimaChave
        if (anterior == null) {
            lista.scrollToItem(itens.lastIndex)
        } else if (lista.layoutInfo.visibleItemsInfo.any { it.key == anterior }) {
            lista.animateScrollToItem(itens.lastIndex)
        }
    }

    val modo = estado.dados?.atendimento?.modoOperacao ?: modoLista
    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            tituloCabecalho(estado.dados, tituloLista),
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            fontSize = 18.sp,
                        )
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text(formatarTelefone(telefone), fontSize = 12.sp, color = Color.White.copy(alpha = 0.85f))
                            SeloModo(modo)
                        }
                    }
                },
                colors = coresBarraTopo(),
                navigationIcon = {
                    IconButton(onClick = aoVoltar) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Voltar")
                    }
                },
            )
        },
        floatingActionButton = {
            if (lista.canScrollForward) {
                SmallFloatingActionButton(
                    onClick = { escopo.launch { lista.animateScrollToItem(itens.lastIndex.coerceAtLeast(0)) } },
                    containerColor = Color.White,
                    contentColor = InforrelPrimary,
                ) { Icon(Icons.Filled.KeyboardArrowDown, contentDescription = "Ir para a última mensagem") }
            }
        },
    ) { padding ->
        BoxWithConstraints(Modifier.fillMaxSize().padding(padding).background(FundoConversa)) {
            val larguraBolha = maxWidth * 0.82f
            when {
                !estado.carregou && estado.erro == null -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
                estado.carregou && itens.isEmpty() -> Text(
                    "Nenhuma mensagem nesta conversa.",
                    modifier = Modifier.align(Alignment.Center),
                    color = Color.Gray,
                )
                else -> LazyColumn(
                    state = lista,
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(horizontal = 8.dp, vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    items(itens, key = { it.chave }) { item ->
                        when (item) {
                            is ItemConversa.Dia -> SeparadorDia(item.rotulo)
                            is ItemConversa.Bolha -> Bolha(
                                item = item,
                                larguraMax = larguraBolha,
                                aoTocarCitacao = { citada ->
                                    val indice = itens.indexOfFirst { it.chave == "m${citada.id}" }
                                    if (indice >= 0) escopo.launch { lista.animateScrollToItem(indice) }
                                },
                            )
                        }
                    }
                }
            }
            estado.erro?.let { erro ->
                Text(
                    erro,
                    modifier = Modifier.fillMaxWidth().align(Alignment.TopCenter)
                        .background(MaterialTheme.colorScheme.errorContainer).padding(12.dp),
                    color = MaterialTheme.colorScheme.onErrorContainer,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
    }
}

/** Selo do modo do atendimento: HUMANO (atendente assumiu) ou IA (agente responde). */
@Composable
private fun SeloModo(modo: String?) {
    if (modo == null) return
    val humano = modo.equals("humano", ignoreCase = true)
    Text(
        if (humano) "HUMANO" else "IA",
        modifier = Modifier
            .background(if (humano) InforrelAccent else Color.White.copy(alpha = 0.25f), RoundedCornerShape(4.dp))
            .padding(horizontal = 6.dp, vertical = 1.dp),
        color = Color.White,
        fontSize = 10.sp,
        fontWeight = FontWeight.Bold,
    )
}

@Composable
private fun SeparadorDia(rotulo: String) {
    Box(Modifier.fillMaxWidth().padding(vertical = 6.dp), contentAlignment = Alignment.Center) {
        Text(
            rotulo,
            modifier = Modifier.background(Color.White.copy(alpha = 0.9f), RoundedCornerShape(8.dp)).padding(horizontal = 10.dp, vertical = 3.dp),
            fontSize = 12.sp,
            color = Color.DarkGray,
        )
    }
}

@Composable
private fun Bolha(item: ItemConversa.Bolha, larguraMax: Dp, aoTocarCitacao: (Mensagem) -> Unit) {
    val m = item.mensagem
    val doCliente = ehDoCliente(m)
    val fundo = when {
        doCliente -> Color.White
        m.manual -> BolhaAtendente
        else -> BolhaIA
    }
    val forma = if (doCliente) RoundedCornerShape(2.dp, 10.dp, 10.dp, 10.dp) else RoundedCornerShape(10.dp, 2.dp, 10.dp, 10.dp)
    Row(Modifier.fillMaxWidth(), horizontalArrangement = if (doCliente) Arrangement.Start else Arrangement.End) {
        Column(
            Modifier.widthIn(max = larguraMax).background(fundo, forma).padding(horizontal = 10.dp, vertical = 6.dp),
        ) {
            if (!doCliente) {
                Text(
                    autor(m),
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = if (m.manual) InforrelAccent else InforrelSecondary,
                )
            }
            if (m.respostaAMensagemId != null) {
                Citacao(item.citada, aoTocar = { item.citada?.let(aoTocarCitacao) })
            }
            Text(m.conteudo, fontSize = 15.sp, color = Color(0xFF202020))
            val sit = situacao(m)
            if (sit == SituacaoMensagem.ERRO_ENVIO && !m.erroEnvio.isNullOrBlank()) {
                Text("Não entregue: ${m.erroEnvio}", fontSize = 12.sp, color = VermelhoErro, modifier = Modifier.padding(top = 4.dp))
            }
            Row(
                Modifier.align(Alignment.End).padding(top = 2.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                if (sit != null) RotuloSituacao(sit)
                Text(horaMensagem(m), fontSize = 11.sp, color = Color.Gray)
            }
        }
    }
}

@Composable
private fun RotuloSituacao(sit: SituacaoMensagem) {
    val (icone, cor) = when (sit) {
        SituacaoMensagem.AGUARDANDO -> Icons.Filled.Create to InforrelAccent
        SituacaoMensagem.REPROVADA -> Icons.Filled.Close to VermelhoErro
        SituacaoMensagem.ERRO_ENVIO -> Icons.Filled.Warning to VermelhoErro
        SituacaoMensagem.ENVIADA -> Icons.Filled.Done to InforrelSecondary
        SituacaoMensagem.APROVADA -> Icons.Filled.Done to Color.Gray
    }
    Icon(icone, contentDescription = null, tint = cor, modifier = Modifier.size(14.dp))
    Text(sit.rotulo, fontSize = 11.sp, color = cor)
}

/** A mensagem citada, como no WhatsApp: barra à esquerda, autor e trecho. Toque leva até ela. */
@Composable
private fun Citacao(citada: Mensagem?, aoTocar: () -> Unit) {
    Row(
        Modifier
            .padding(top = 2.dp, bottom = 4.dp)
            .height(IntrinsicSize.Min)
            .background(Color.Black.copy(alpha = 0.05f), RoundedCornerShape(6.dp))
            .clickable(enabled = citada != null, onClick = aoTocar),
    ) {
        Box(Modifier.width(4.dp).fillMaxHeight().background(InforrelSecondary, RoundedCornerShape(topStart = 6.dp, bottomStart = 6.dp)))
        Column(Modifier.padding(horizontal = 8.dp, vertical = 4.dp)) {
            Text(
                citada?.let(::autor) ?: "Em resposta a",
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
                color = InforrelSecondary,
            )
            Text(
                citada?.let { trechoCitacao(it.conteudo) } ?: "mensagem fora das carregadas",
                fontSize = 13.sp,
                color = Color.DarkGray,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}
