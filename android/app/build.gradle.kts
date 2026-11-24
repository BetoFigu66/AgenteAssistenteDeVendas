import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

// Versão do App nos moldes do front e do back: android/VERSAO guarda AAAA.MM.DD-HHMM
// (horário de Brasília), atualizado por scripts/versao.py. É o versionName; o versionCode,
// que o Android exige inteiro e crescente para instalar por cima, são os minutos desde
// 2026-01-01 00:00 (cabe em Int por uns 4 mil anos).
val versaoApp: String = rootProject.file("VERSAO").readText().trim()
val versionCodeApp: Int = ChronoUnit.MINUTES.between(
    LocalDateTime.of(2026, 1, 1, 0, 0),
    LocalDateTime.parse(versaoApp, DateTimeFormatter.ofPattern("yyyy.MM.dd-HHmm")),
).toInt()

android {
    namespace = "br.com.inforrel.atendente"
    compileSdk = 34

    defaultConfig {
        applicationId = "br.com.inforrel.atendente"
        minSdk = 26
        targetSdk = 34
        versionCode = versionCodeApp
        versionName = versaoApp
        buildConfigField("String", "BACKEND_URL", "\"https://app.auxvendas.com\"")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            // Chave de debug do Windows (%USERPROFILE%\.android\debug.keystore), a mesma em
            // todos os builds, para cada versão instalar por cima da anterior. Nenhuma
            // keystore ou senha vai para o repositório.
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    lint {
        // O lint vital do release é a etapa que mais pede memória no build; com o Windows
        // apertado ela caía. O lint completo continua disponível em `gradlew lint`.
        checkReleaseBuilds = false
    }
    testOptions {
        unitTests.isReturnDefaultValues = true
        // JVM de teste pequena: com o padrão (G1, heap inicial de 1/64 da RAM) ela não abria
        // quando o Windows estava com pouca memória livre.
        unitTests.all {
            it.minHeapSize = "32m"
            it.maxHeapSize = "256m"
            it.jvmArgs("-XX:+UseSerialGC")
        }
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.10.01")
    implementation(composeBom)
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")
}
