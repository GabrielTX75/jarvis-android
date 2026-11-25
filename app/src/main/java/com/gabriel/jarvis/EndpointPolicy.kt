package com.gabriel.jarvis

/** Compatibilidade com os testes e chamadas legadas; a política completa fica em AiEndpointPolicy. */
object EndpointPolicy {
    fun isAllowed(endpoint: String): Boolean = AiEndpointPolicy.validate(endpoint) != null
}
