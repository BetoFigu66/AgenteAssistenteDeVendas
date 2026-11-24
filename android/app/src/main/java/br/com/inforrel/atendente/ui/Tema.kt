package br.com.inforrel.atendente.ui

import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.TopAppBarColors
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Cores da marca Inforrel (frontend/tailwind.config.js).
val InforrelPrimary = Color(0xFF1B4F72)
val InforrelSecondary = Color(0xFF2E86AB)
val InforrelAccent = Color(0xFFF39C12)

@Composable
fun TemaInforrel(conteudo: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = lightColorScheme(
            primary = InforrelPrimary,
            secondary = InforrelSecondary,
            tertiary = InforrelAccent,
        ),
        content = conteudo,
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun coresBarraTopo(): TopAppBarColors = TopAppBarDefaults.topAppBarColors(
    containerColor = InforrelPrimary,
    titleContentColor = Color.White,
    navigationIconContentColor = Color.White,
    actionIconContentColor = Color.White,
)
