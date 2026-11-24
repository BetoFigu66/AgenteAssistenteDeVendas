package br.com.inforrel.atendente.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Create
import androidx.compose.material.icons.filled.Done
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.repeatOnLifecycle
import br.com.inforrel.atendente.conversas.INTERVALO_ATUALIZACAO_MS
import br.com.inforrel.atendente.conversas.ModeloConversas
import br.com.inforrel.atendente.conversas.emModoHumano
import br.com.inforrel.atendente.conversas.formatarHorarioLista
import br.com.inforrel.atendente.conversas.formatarTelefone
import br.com.inforrel.atendente.conversas.iniciais
import br.com.inforrel.atendente.conversas.momentoConversa
import br.com.inforrel.atendente.conversas.rotuloFase
import br.com.inforrel.atendente.conversas.textoPrevia
import br.com.inforrel.atendente.conversas.tituloConversa
import br.com.inforrel.atendente.rede.AtendimentoResumo
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/** Pausa depois da última tecla antes de buscar no servidor. */
private const val ESPERA_BUSCA_MS = 400L

/**
 * Tela principal: a lista de atendimentos ativos, como a lista de conversas do WhatsApp.
 * Atualiza sozinha a cada [INTERVALO_ATUALIZACAO_MS] enquanto está visível (para em segundo
 * plano) e ao puxar para baixo.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TelaConversas(
    modelo: ModeloConversas,
    semConfirmar: Boolean,
    aoAbrirConversa: (AtendimentoResumo) -> Unit,
    aoAbrirSobre: () -> Unit,
    aoSair: () -> Unit,
) {
    val estado by modelo.estado.collectAsState()
    var menuAberto by remember { mutableStateOf(false) }
    var buscando by rememberSaveable { mutableStateOf(estado.termo.isNotEmpty()) }
    val escopo = rememberCoroutineScope()
    val ciclo = LocalLifecycleOwner.current.lifecycle

    // Polling só com a tela em primeiro plano: ao ir para segundo plano o bloco é cancelado e,
    // ao voltar, recomeça já buscando.
    LaunchedEffect(ciclo) {
        ciclo.repeatOnLifecycle(Lifecycle.State.STARTED) {
            while (true) {
                modelo.carregar()
                delay(INTERVALO_ATUALIZACAO_MS)
            }
        }
    }
    // Busca com espera curta depois da digitação; a primeira composição já é coberta acima.
    var primeiroTermo by remember { mutableStateOf(true) }
    LaunchedEffect(estado.termo) {
        if (primeiroTermo) {
            primeiroTermo = false
            return@LaunchedEffect
        }
        delay(ESPERA_BUSCA_MS)
        modelo.carregar()
    }

    Scaffold(
        topBar = {
            if (buscando) {
                BarraBusca(
                    termo = estado.termo,
                    aoMudar = modelo::mudarTermo,
                    aoFechar = { buscando = false; modelo.mudarTermo("") },
                )
            } else {
                TopAppBar(
                    title = { Text("Conversas") },
                    colors = coresBarraTopo(),
                    actions = {
                        IconButton(onClick = { buscando = true }) {
                            Icon(Icons.Filled.Search, contentDescription = "Buscar")
                        }
                        IconButton(onClick = { menuAberto = true }) {
                            Icon(Icons.Filled.MoreVert, contentDescription = "Menu")
                        }
                        DropdownMenu(expanded = menuAberto, onDismissRequest = { menuAberto = false }) {
                            DropdownMenuItem(text = { Text("Sobre") }, onClick = { menuAberto = false; aoAbrirSobre() })
                            DropdownMenuItem(text = { Text("Sair") }, onClick = { menuAberto = false; aoSair() })
                        }
                    },
                )
            }
        },
    ) { padding ->
        PullToRefreshBox(
            isRefreshing = estado.atualizandoManual,
            onRefresh = { escopo.launch { modelo.atualizarManual() } },
            modifier = Modifier.fillMaxSize().padding(padding),
        ) {
            LazyColumn(Modifier.fillMaxSize()) {
                val aviso = estado.erro ?: if (semConfirmar && !estado.carregou) {
                    "Sem conexão com o servidor: sessão ainda não confirmada."
                } else {
                    null
                }
                if (aviso != null) {
                    item(key = "aviso") { FaixaAviso(aviso) }
                }
                when {
                    !estado.carregou && estado.erro == null -> item(key = "carregando") {
                        Box(Modifier.fillMaxWidth().padding(48.dp), contentAlignment = Alignment.Center) {
                            CircularProgressIndicator()
                        }
                    }
                    estado.carregou && estado.conversas.isEmpty() -> item(key = "vazio") {
                        Text(
                            if (estado.termo.isBlank()) "Nenhum atendimento ativo." else "Nada encontrado para \"${estado.termo.trim()}\".",
                            modifier = Modifier.fillMaxWidth().padding(48.dp),
                            textAlign = TextAlign.Center,
                            color = Color.Gray,
                        )
                    }
                }
                items(estado.conversas, key = { it.id }) { conversa ->
                    LinhaConversa(conversa, aoTocar = { aoAbrirConversa(conversa) })
                    HorizontalDivider(Modifier.padding(start = 80.dp), color = Color(0xFFEEEEEE))
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun BarraBusca(termo: String, aoMudar: (String) -> Unit, aoFechar: () -> Unit) {
    TopAppBar(
        colors = coresBarraTopo(),
        navigationIcon = {
            IconButton(onClick = aoFechar) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Fechar busca")
            }
        },
        title = {
            TextField(
                value = termo,
                onValueChange = aoMudar,
                placeholder = { Text("Nome, empresa ou telefone", color = Color.White.copy(alpha = 0.7f)) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                colors = TextFieldDefaults.colors(
                    focusedContainerColor = Color.Transparent,
                    unfocusedContainerColor = Color.Transparent,
                    focusedTextColor = Color.White,
                    unfocusedTextColor = Color.White,
                    cursorColor = Color.White,
                    focusedIndicatorColor = Color.Transparent,
                    unfocusedIndicatorColor = Color.Transparent,
                ),
                trailingIcon = {
                    if (termo.isNotEmpty()) {
                        IconButton(onClick = { aoMudar("") }) {
                            Icon(Icons.Filled.Clear, contentDescription = "Limpar busca", tint = Color.White)
                        }
                    }
                },
            )
        },
    )
}

@Composable
private fun FaixaAviso(texto: String) {
    Text(
        texto,
        modifier = Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.errorContainer).padding(12.dp),
        color = MaterialTheme.colorScheme.onErrorContainer,
        style = MaterialTheme.typography.bodySmall,
    )
}

/** Uma linha da lista: avatar, título e horário; prévia e pendências; telefone, empresa, fase e selo. */
@Composable
private fun LinhaConversa(conversa: AtendimentoResumo, aoTocar: () -> Unit) {
    val titulo = tituloConversa(conversa)
    val pendentes = conversa.mensagensPendentes
    val previa = conversa.ultimaMensagem
    Row(
        modifier = Modifier.fillMaxWidth().clickable(onClick = aoTocar).padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier.size(52.dp).background(InforrelSecondary, CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Text(iniciais(titulo), color = Color.White, fontWeight = FontWeight.SemiBold, fontSize = 18.sp)
        }
        Spacer(Modifier.width(12.dp))
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    titulo,
                    modifier = Modifier.weight(1f),
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 16.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    formatarHorarioLista(momentoConversa(conversa)),
                    style = MaterialTheme.typography.bodySmall,
                    color = if (pendentes > 0) InforrelAccent else Color.Gray,
                    fontWeight = if (pendentes > 0) FontWeight.SemiBold else FontWeight.Normal,
                )
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (previa?.origem == "system") {
                    // Resposta nossa: lápis enquanto aguarda aprovação, "feito" depois.
                    Icon(
                        if (previa.pendenteAprovacao) Icons.Filled.Create else Icons.Filled.Done,
                        contentDescription = if (previa.pendenteAprovacao) "Aguardando aprovação" else "Resposta aprovada",
                        tint = if (previa.pendenteAprovacao) InforrelAccent else Color.Gray,
                        modifier = Modifier.size(16.dp),
                    )
                    Spacer(Modifier.width(4.dp))
                }
                Text(
                    textoPrevia(conversa).ifEmpty { "Sem mensagens" },
                    modifier = Modifier.weight(1f),
                    color = Color.Gray,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    style = MaterialTheme.typography.bodyMedium,
                )
                if (pendentes > 0) {
                    Spacer(Modifier.width(8.dp))
                    Box(
                        modifier = Modifier.widthIn(min = 22.dp).background(InforrelAccent, CircleShape).padding(horizontal = 6.dp, vertical = 2.dp),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(pendentes.toString(), color = Color.White, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                val detalhes = listOfNotNull(
                    formatarTelefone(conversa.telefone).takeIf { it != titulo },
                    conversa.empresaNome?.takeIf { it.isNotBlank() && it != titulo },
                    rotuloFase(conversa.fase),
                ).joinToString(" · ")
                Text(
                    detalhes,
                    modifier = Modifier.weight(1f, fill = false),
                    style = MaterialTheme.typography.labelSmall,
                    color = Color.Gray,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                if (emModoHumano(conversa)) SeloHumano()
            }
        }
    }
}

/** Selo do atendimento em modo HUMANO: o agente não responde, o atendente assumiu. */
@Composable
private fun SeloHumano() {
    Text(
        "HUMANO",
        modifier = Modifier.background(InforrelPrimary, RoundedCornerShape(4.dp)).padding(horizontal = 6.dp, vertical = 1.dp),
        color = Color.White,
        fontSize = 10.sp,
        fontWeight = FontWeight.Bold,
    )
}
