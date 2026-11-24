package br.com.inforrel.atendente.ui

import android.content.Intent
import android.net.Uri
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import br.com.inforrel.atendente.BuildConfig
import br.com.inforrel.atendente.rede.ApiBackend
import br.com.inforrel.atendente.rede.Consulta
import br.com.inforrel.atendente.rede.VersaoPublicada
import br.com.inforrel.atendente.rede.consultarVersaoBackend
import br.com.inforrel.atendente.rede.consultarVersaoPublicada
import br.com.inforrel.atendente.rede.haVersaoNova

/** Página de download do APK (nginx do frontend, publicada por scripts/app_publicar.sh). */
private const val CAMINHO_DOWNLOAD = "/android/"

/** Versões do App e do Backend, e aviso quando há App mais novo publicado para baixar. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TelaSobre(api: ApiBackend, aoVoltar: () -> Unit) {
    BackHandler(onBack = aoVoltar)
    var backend by remember { mutableStateOf<Consulta<String>>(Consulta.Carregando) }
    var publicada by remember { mutableStateOf<Consulta<VersaoPublicada>>(Consulta.Carregando) }
    var tentativa by remember { mutableIntStateOf(0) }
    val contexto = LocalContext.current

    LaunchedEffect(tentativa) {
        backend = Consulta.Carregando
        publicada = Consulta.Carregando
        backend = consultarVersaoBackend(api)
        publicada = consultarVersaoPublicada(api)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Sobre") },
                colors = coresBarraTopo(),
                navigationIcon = {
                    IconButton(onClick = aoVoltar) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Voltar")
                    }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState()).padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            LinhaVersao("Versão do App", BuildConfig.VERSION_NAME)
            when (val atual = backend) {
                Consulta.Carregando -> LinhaVersao("Versão do Backend", "consultando…")
                is Consulta.Ok -> LinhaVersao("Versão do Backend", atual.valor)
                is Consulta.Erro -> LinhaVersao("Versão do Backend", atual.mensagem, erro = true)
            }
            when (val atual = publicada) {
                Consulta.Carregando -> {}
                is Consulta.Erro -> Text(
                    "Não deu para conferir se há versão nova do App: ${atual.mensagem}",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color.Gray,
                )
                is Consulta.Ok -> if (haVersaoNova(atual.valor, BuildConfig.VERSION_CODE.toLong())) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = InforrelAccent.copy(alpha = 0.15f)),
                    ) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(
                                "Há versão nova do App: ${atual.valor.versao}",
                                fontWeight = FontWeight.SemiBold,
                                color = InforrelPrimary,
                            )
                            Button(
                                onClick = {
                                    val url = BuildConfig.BACKEND_URL + CAMINHO_DOWNLOAD
                                    contexto.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                                },
                                colors = ButtonDefaults.buttonColors(containerColor = InforrelAccent),
                            ) { Text("Baixar a versão nova") }
                        }
                    }
                } else {
                    Text("O App está na versão mais recente.", style = MaterialTheme.typography.bodySmall, color = Color.Gray)
                }
            }
            Text(BuildConfig.BACKEND_URL, style = MaterialTheme.typography.bodySmall, color = Color.Gray)
            OutlinedButton(onClick = { tentativa++ }, enabled = backend != Consulta.Carregando) {
                Text("Atualizar")
            }
        }
    }
}

@Composable
private fun LinhaVersao(rotulo: String, valor: String, erro: Boolean = false) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp)) {
            Text(rotulo, style = MaterialTheme.typography.labelLarge, color = InforrelPrimary)
            Text(
                valor,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold,
                color = if (erro) MaterialTheme.colorScheme.error else Color.Unspecified,
            )
        }
    }
}
