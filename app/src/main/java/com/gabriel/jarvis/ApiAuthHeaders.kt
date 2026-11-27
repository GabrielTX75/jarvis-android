package com.gabriel.jarvis

/**
 * Cabeçalhos de autenticação dos testes de conectividade.
 * Não coloca chaves em URLs nem registra os valores.
 */
internal object ApiAuthHeaders {
    fun forProvider(provider: String, apiKey: String): Map<String, String> {
        if (apiKey.isBlank()) return emptyMap()
        return when (provider) {
            "groq" -> mapOf("Authorization" to "Bearer $apiKey")
            "gemini" -> mapOf("x-goog-api-key" to apiKey)
            "brapi" -> mapOf("Authorization" to "Bearer $apiKey")
            else -> emptyMap()
        }
    }
}
