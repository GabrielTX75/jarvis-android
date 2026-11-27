package com.gabriel.jarvis

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ApiAuthHeadersTest {
    @Test
    fun geminiUsesDedicatedApiKeyHeader() {
        assertEquals(
            mapOf("x-goog-api-key" to "test-key"),
            ApiAuthHeaders.forProvider("gemini", "test-key")
        )
    }

    @Test
    fun groqKeepsBearerAuthentication() {
        assertEquals(
            mapOf("Authorization" to "Bearer test-key"),
            ApiAuthHeaders.forProvider("groq", "test-key")
        )
    }

    @Test
    fun blankOrUnsupportedCredentialsProduceNoHeaders() {
        assertTrue(ApiAuthHeaders.forProvider("gemini", " ").isEmpty())
        assertTrue(ApiAuthHeaders.forProvider("unknown", "test-key").isEmpty())
    }
}
