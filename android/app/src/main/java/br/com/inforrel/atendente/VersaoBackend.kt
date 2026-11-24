package br.com.inforrel.atendente

import org.json.JSONException
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.SocketTimeoutException
import java.net.URL
import java.net.UnknownHostException

/** Resultado da consulta da versão do backend: a versão, ou um erro legível para a tela. */
sealed interface VersaoBackend {
    data class Ok(val versao: String) : VersaoBackend
    data class Erro(val mensagem: String) : VersaoBackend
}

/**
 * Lê a versão do backend em `GET <backendUrl>/health` (rota pública, devolve
 * `{"status": "healthy", "version": "AAAA.MM.DD-HHMM"}`). Bloqueante: chamar fora da thread
 * principal.
 */
fun consultarVersaoBackend(backendUrl: String, timeoutMs: Int = 10_000): VersaoBackend {
    val conexao = try {
        URL("$backendUrl/health").openConnection() as HttpURLConnection
    } catch (e: IOException) {
        return VersaoBackend.Erro("Endereço do servidor inválido: $backendUrl")
    }
    return try {
        conexao.connectTimeout = timeoutMs
        conexao.readTimeout = timeoutMs
        val codigo = conexao.responseCode
        if (codigo != HttpURLConnection.HTTP_OK) {
            erroHttp(codigo)
        } else {
            interpretarHealth(conexao.inputStream.bufferedReader().use { it.readText() })
        }
    } catch (e: UnknownHostException) {
        VersaoBackend.Erro("Sem internet ou servidor não encontrado.")
    } catch (e: SocketTimeoutException) {
        VersaoBackend.Erro("O servidor demorou demais para responder.")
    } catch (e: IOException) {
        VersaoBackend.Erro("Não foi possível falar com o servidor (${e.javaClass.simpleName}).")
    } finally {
        conexao.disconnect()
    }
}

/** Mensagem para um status HTTP diferente de 200. 502 a 530 vêm do Cloudflare com o túnel ou o backend fora. */
fun erroHttp(codigo: Int): VersaoBackend.Erro = when (codigo) {
    in 502..504, 530 -> VersaoBackend.Erro("Servidor fora do ar no momento (HTTP $codigo).")
    else -> VersaoBackend.Erro("O servidor respondeu com erro (HTTP $codigo).")
}

/** Extrai a versão do corpo do `/health`. */
fun interpretarHealth(corpo: String): VersaoBackend = try {
    val versao = JSONObject(corpo).optString("version")
    if (versao.isBlank()) {
        VersaoBackend.Erro("Resposta do servidor sem a versão.")
    } else {
        VersaoBackend.Ok(versao)
    }
} catch (e: JSONException) {
    VersaoBackend.Erro("Resposta do servidor em formato inesperado.")
}
