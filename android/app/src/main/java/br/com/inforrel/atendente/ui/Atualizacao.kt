package br.com.inforrel.atendente.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberUpdatedState
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.repeatOnLifecycle
import kotlinx.coroutines.delay

/**
 * Roda [bloco] já ao aparecer e depois a cada [intervaloMs], só com a tela em primeiro plano:
 * em segundo plano o laço é cancelado e, ao voltar, recomeça já rodando.
 */
@Composable
fun AtualizacaoPeriodica(intervaloMs: Long, bloco: suspend () -> Unit) {
    val ciclo = LocalLifecycleOwner.current.lifecycle
    val atual by rememberUpdatedState(bloco)
    LaunchedEffect(ciclo, intervaloMs) {
        ciclo.repeatOnLifecycle(Lifecycle.State.STARTED) {
            while (true) {
                atual()
                delay(intervaloMs)
            }
        }
    }
}
