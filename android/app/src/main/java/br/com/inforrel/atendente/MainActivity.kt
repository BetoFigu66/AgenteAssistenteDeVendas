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
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import br.com.inforrel.atendente.conversas.ModeloConversa
import br.com.inforrel.atendente.conversas.ModeloConversas
import br.com.inforrel.atendente.conversas.tituloConversa
import br.com.inforrel.atendente.sessao.EstadoSessao
import br.com.inforrel.atendente.ui.TelaConversa
import br.com.inforrel.atendente.ui.TelaConversas
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
                    // Conversa aberta (id, telefone, título e modo vindos da lista), guardada para
                    // sobreviver a girar a tela.
                    var conversaId by rememberSaveable { mutableStateOf<Int?>(null) }
                    var conversaTelefone by rememberSaveable { mutableStateOf("") }
                    var conversaTitulo by rememberSaveable { mutableStateOf("") }
                    var conversaModo by rememberSaveable { mutableStateOf<String?>(null) }
                    val escopo = rememberCoroutineScope()

                    when (val atual = estado) {
                        EstadoSessao.Verificando -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                            CircularProgressIndicator()
                        }
                        is EstadoSessao.Deslogado -> {
                            // Quem voltar a entrar cai na lista, não no Sobre nem na conversa de antes.
                            LaunchedEffect(Unit) { noSobre = false; conversaId = null }
                            TelaLogin(app.sessao, atual.aviso)
                        }
                        is EstadoSessao.Logado -> {
                            // Um modelo por login: a lista (e a busca) de outro usuário não fica para trás.
                            val modelo = remember(atual.usuario.id) { ModeloConversas(app.api) }
                            val aberta = conversaId
                            when {
                                noSobre -> TelaSobre(app.api, aoVoltar = { noSobre = false })
                                aberta != null -> {
                                    val modeloConversa = remember(aberta) { ModeloConversa(app.api, conversaTelefone) }
                                    TelaConversa(
                                        modelo = modeloConversa,
                                        telefone = conversaTelefone,
                                        tituloLista = conversaTitulo,
                                        modoLista = conversaModo,
                                        aoVoltar = { conversaId = null },
                                    )
                                }
                                else -> TelaConversas(
                                    modelo = modelo,
                                    semConfirmar = atual.semConfirmar,
                                    aoAbrirConversa = { conversa ->
                                        conversaTitulo = tituloConversa(conversa)
                                        conversaTelefone = conversa.telefone
                                        conversaModo = conversa.modoOperacao
                                        conversaId = conversa.id
                                    },
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
}
