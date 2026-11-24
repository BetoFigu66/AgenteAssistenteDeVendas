package br.com.inforrel.atendente

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

// Cores da marca Inforrel (frontend/tailwind.config.js).
private val InforrelPrimary = Color(0xFF1B4F72)
private val InforrelSecondary = Color(0xFF2E86AB)
private val InforrelAccent = Color(0xFFF39C12)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(
                colorScheme = lightColorScheme(
                    primary = InforrelPrimary,
                    secondary = InforrelSecondary,
                    tertiary = InforrelAccent,
                ),
            ) {
                TelaVersoes()
            }
        }
    }
}

@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
fun TelaVersoes() {
    var backend by remember { mutableStateOf<VersaoBackend?>(null) }
    var tentativa by remember { mutableIntStateOf(0) }

    LaunchedEffect(tentativa) {
        backend = null
        backend = withContext(Dispatchers.IO) { consultarVersaoBackend(BuildConfig.BACKEND_URL) }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Inforrel Atendente") },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = InforrelPrimary,
                    titleContentColor = Color.White,
                ),
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            LinhaVersao("Versão do App", BuildConfig.VERSION_NAME)
            when (val atual = backend) {
                null -> LinhaVersao("Versão do Backend", "consultando…")
                is VersaoBackend.Ok -> LinhaVersao("Versão do Backend", atual.versao)
                is VersaoBackend.Erro -> LinhaVersao("Versão do Backend", atual.mensagem, erro = true)
            }
            Text(
                BuildConfig.BACKEND_URL,
                style = MaterialTheme.typography.bodySmall,
                color = Color.Gray,
            )
            Spacer(Modifier.height(8.dp))
            Button(
                onClick = { tentativa++ },
                enabled = backend != null,
                colors = ButtonDefaults.buttonColors(containerColor = InforrelSecondary),
            ) {
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
