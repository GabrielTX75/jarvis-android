package com.gabriel.jarvis

import java.net.URI
import java.net.URL
import java.util.Locale

internal data class ValidatedAiEndpoint(
    val normalized: String,
    val local: Boolean,
    val display: String
)

/**
 * Valida e normaliza endpoints OpenAI-compatible antes de armazenar ou usar
 * credenciais. A aprovação remota é vinculada à URL completa normalizada.
 */
internal object AiEndpointPolicy {
    fun validate(raw: String): ValidatedAiEndpoint? {
        if (raw.isBlank() || raw.length > 2048) return null
        val parsed = try { URI(raw.trim()).normalize() } catch (_: Exception) { return null }
        if (!parsed.isAbsolute || parsed.isOpaque ||
            parsed.rawUserInfo != null || parsed.rawQuery != null || parsed.rawFragment != null) {
            return null
        }

        val scheme = parsed.scheme?.lowercase(Locale.ROOT) ?: return null
        val host = parsed.host?.lowercase(Locale.ROOT) ?: return null
        val local = host == "localhost" || host == "127.0.0.1"
        if (!(scheme == "https" || (scheme == "http" && local))) return null
        if (parsed.port !in -1..65535 || parsed.port == 0) return null

        val path = parsed.rawPath?.takeIf { it.isNotEmpty() } ?: "/"
        if (!path.startsWith("/")) return null
        val authorityHost = if (host.contains(":") && !host.startsWith("[")) "[$host]" else host
        val defaultPort = if (scheme == "https") 443 else 80
        val portSuffix = if (parsed.port == -1 || parsed.port == defaultPort) "" else ":\u0024{parsed.port}"
        val normalized = "\u0024scheme://\u0024authorityHost\u0024portSuffix\u0024path"
        if (normalized.length > 2048) return null
        try { URL(normalized) } catch (_: Exception) { return null }

        return ValidatedAiEndpoint(normalized, local, "\u0024authorityHost\u0024portSuffix\u0024path")
    }
}
