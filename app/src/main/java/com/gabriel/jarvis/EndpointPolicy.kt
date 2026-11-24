package com.gabriel.jarvis

import java.net.URL

/**
 * Valida destinos usados para enviar prompts e chaves de IA.
 * HTTPS é obrigatório para servidores remotos; HTTP só é aceito no próprio aparelho.
 */
object EndpointPolicy {
    fun isAllowed(endpoint: String): Boolean = try {
        val parsed = URL(endpoint.trim())
        val secureRemote = parsed.protocol.equals("https", ignoreCase = true)
        val localHttp = parsed.protocol.equals("http", ignoreCase = true) &&
            (parsed.host.equals("localhost", ignoreCase = true) || parsed.host == "127.0.0.1")

        parsed.host.isNotBlank() &&
            parsed.userInfo == null &&
            (secureRemote || localHttp)
    } catch (_: Exception) {
        false
    }
}
