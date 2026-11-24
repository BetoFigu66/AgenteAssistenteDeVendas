package br.com.inforrel.atendente

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Surface
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import br.com.inforrel.atendente.sessao.EstadoSessao
import br.com.inforrel.atendente.ui.TelaInicial
import br.com.inforrel.atendente.ui.TelaLogin
import br.com.inforrel.atendente.ui.TelaSobre
import br.com.inforrel.atendente.ui.TemaInforrel
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val app = application as AppAtendente
        setContent {
            TemaInforrel {
                Surface(Modifier.fillMaxSize()) {
                    val estado by app.sessao.estado.collectAsState()
                    var noSobre by rememberSaveable { mutableStateOf(false) }
                    val escopo = rememberCoroutineScope()

                    when (val atual = estado) {
                        EstadoSessao.Verificando -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                            CircularProgressIndicator()
                        }
                        is EstadoSessao.Deslogado -> {
                            // Quem voltar a entrar cai na tela inicial, não no Sobre de antes.
                            LaunchedEffect(Unit) { noSobre = false }
                            TelaLogin(app.sessao, atual.aviso)
                        }
                        is EstadoSessao.Logado -> if (noSobre) {
                            TelaSobre(app.api, aoVoltar = { noSobre = false })
                        } else {
                            TelaInicial(
                                usuario = atual.usuario,
                                semConfirmar = atual.semConfirmar,
                                aoAbrirSobre = { noSobre = true },
                                aoSair = { escopo.launch { app.sessao.sair() } },
                            )
                        }
                    }
                }
            }
        }
    }
}
