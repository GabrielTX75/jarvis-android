package com.gabriel.jarvis

import java.util.Locale

/**
 * Regras de normalização da memória factual, sem dependência do Android.
 * O mesmo contrato pode ser reimplementado por outros clientes no futuro.
 */
internal object MemoryFactsPolicy {
    const val MAX_FACT_LENGTH = 200
    const val MAX_FACTS = 50

    fun normalize(facts: List<String>): List<String> {
        val seen = HashSet<String>()
        val result = ArrayList<String>()
        for (raw in facts) {
            val value = raw.replace(Regex("\\s+"), " ").trim().take(MAX_FACT_LENGTH)
            if (value.isNotEmpty() && seen.add(value.lowercase(Locale.ROOT))) {
                result.add(value)
            }
        }
        return result.takeLast(MAX_FACTS)
    }

    fun append(existing: List<String>, newFact: String): List<String> =
        normalize(existing + newFact)
}
