package br.com.inforrel.atendente.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import br.com.inforrel.atendente.BuildConfig
import br.com.inforrel.atendente.sessao.Sessao
import kotlinx.coroutines.launch

/** Login com o mesmo usuário e senha do painel. A senha só vive nesta tela, nunca é gravada. */
@Composable
fun TelaLogin(sessao: Sessao, aviso: String?) {
    var login by rememberSaveable { mutableStateOf("") }
    // Senha fora do rememberSaveable: não vai para o estado salvo da Activity.
    var senha by remember { mutableStateOf("") }
    var erro by remember(aviso) { mutableStateOf(aviso) }
    var entrando by remember { mutableStateOf(false) }
    val escopo = rememberCoroutineScope()

    fun entrar() {
        if (entrando) return
        entrando = true
        erro = null
        escopo.launch {
            erro = sessao.entrar(login, senha)
            entrando = false
            if (erro == null) senha = ""
        }
    }

    Column(
        modifier = Modifier.fillMaxSize().imePadding().padding(32.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterVertically),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            "Inforrel Atendente",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold,
            color = InforrelPrimary,
        )
        Text("Entre com o usuário do sistema", color = Color.Gray)
        OutlinedTextField(
            value = login,
            onValueChange = { login = it },
            label = { Text("Usuário") },
            singleLine = true,
            enabled = !entrando,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Ascii, imeAction = ImeAction.Next),
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = senha,
            onValueChange = { senha = it },
            label = { Text("Senha") },
            singleLine = true,
            enabled = !entrando,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password, imeAction = ImeAction.Done),
            keyboardActions = KeyboardActions(onDone = { entrar() }),
            modifier = Modifier.fillMaxWidth(),
        )
        erro?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Button(
            onClick = ::entrar,
            enabled = !entrando,
            colors = ButtonDefaults.buttonColors(containerColor = InforrelSecondary),
            modifier = Modifier.fillMaxWidth(),
        ) {
            if (entrando) {
                CircularProgressIndicator(Modifier.size(20.dp), color = Color.White, strokeWidth = 2.dp)
            } else {
                Text("Entrar")
            }
        }
        Text("App ${BuildConfig.VERSION_NAME}", style = MaterialTheme.typography.bodySmall, color = Color.Gray)
    }
}
