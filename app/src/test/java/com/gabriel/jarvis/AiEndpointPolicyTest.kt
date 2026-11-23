package com.gabriel.jarvis

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AiEndpointPolicyTest {
    @Test
    fun normalizesHttpsHostAndDefaultPort() {
        val result = AiEndpointPolicy.validate("HTTPS://API.GROQ.COM:443/openai/v1/chat/completions")
        assertEquals("https://api.groq.com/openai/v1/chat/completions", result?.normalized)
        assertFalse(result?.local ?: true)
    }

    @Test
    fun allowsHttpOnlyForLoopbackNames() {
        assertTrue(AiEndpointPolicy.validate("http://localhost:11434/v1/chat/completions")?.local == true)
        assertTrue(AiEndpointPolicy.validate("http://127.0.0.1:11434/v1/chat/completions")?.local == true)
        assertNull(AiEndpointPolicy.validate("http://192.168.1.20:11434/v1/chat/completions"))
    }

    @Test
    fun rejectsCredentialsQueryAndFragment() {
        assertNull(AiEndpointPolicy.validate("https://user:pass@example.com/v1/chat/completions"))
        assertNull(AiEndpointPolicy.validate("https://example.com/v1/chat/completions?api_key=secret"))
        assertNull(AiEndpointPolicy.validate("https://example.com/v1/chat/completions#other"))
    }

    @Test
    fun rejectsInvalidSchemesAndPorts() {
        assertNull(AiEndpointPolicy.validate("ftp://example.com/model"))
        assertNull(AiEndpointPolicy.validate("http://example.com/v1/chat/completions"))
        assertNull(AiEndpointPolicy.validate("https://example.com:0/v1/chat/completions"))
        assertNull(AiEndpointPolicy.validate("https://example.com:99999/v1/chat/completions"))
        assertNull(AiEndpointPolicy.validate(""))
    }

    @Test
    fun normalizesDotSegmentsBeforeApproval() {
        val result = AiEndpointPolicy.validate("https://example.com/v1/../v1/chat/completions")
        assertEquals("https://example.com/v1/chat/completions", result?.normalized)
    }
}
