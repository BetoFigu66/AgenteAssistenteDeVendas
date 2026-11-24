package br.com.inforrel.atendente.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import br.com.inforrel.atendente.rede.Usuario

/**
 * Tela principal depois do login. Por enquanto só o menu (Sobre, Sair); a lista de conversas
 * entra no goal app-android-03.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TelaInicial(
    usuario: Usuario,
    semConfirmar: Boolean,
    aoAbrirSobre: () -> Unit,
    aoSair: () -> Unit,
) {
    var menuAberto by remember { mutableStateOf(false) }
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Inforrel Atendente") },
                colors = coresBarraTopo(),
                actions = {
                    IconButton(onClick = { menuAberto = true }) {
                        Icon(Icons.Filled.MoreVert, contentDescription = "Menu")
                    }
                    DropdownMenu(expanded = menuAberto, onDismissRequest = { menuAberto = false }) {
                        DropdownMenuItem(text = { Text("Sobre") }, onClick = { menuAberto = false; aoAbrirSobre() })
                        DropdownMenuItem(text = { Text("Sair") }, onClick = { menuAberto = false; aoSair() })
                    }
                },
            )
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding).padding(24.dp), contentAlignment = Alignment.Center) {
            Column(
                verticalArrangement = Arrangement.spacedBy(12.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text("Olá, ${usuario.nome}!", style = MaterialTheme.typography.headlineSmall, color = InforrelPrimary)
                Text(
                    "As conversas aparecem aqui na próxima versão do App.",
                    textAlign = TextAlign.Center,
                    color = Color.Gray,
                )
                if (semConfirmar) {
                    Text(
                        "Sem conexão com o servidor: sessão ainda não confirmada.",
                        textAlign = TextAlign.Center,
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
        }
    }
}
