package com.gabriel.jarvis

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class MemoryFactsPolicyTest {
    @Test
    fun normalizesWhitespaceAndDeduplicatesIgnoringCase() {
        assertEquals(
            listOf("prefiro respostas curtas"),
            MemoryFactsPolicy.normalize(
                listOf("  prefiro   respostas curtas  ", "PREFIRO respostas curtas")
            )
        )
    }

    @Test
    fun keepsOnlyTheMostRecentFiftyFacts() {
        val result = MemoryFactsPolicy.normalize((1..55).map { "fato $it" })
        assertEquals(50, result.size)
        assertEquals("fato 6", result.first())
        assertEquals("fato 55", result.last())
    }

    @Test
    fun truncatesFactsToTwoHundredCharacters() {
        val result = MemoryFactsPolicy.normalize(listOf("x".repeat(240)))
        assertEquals(200, result.single().length)
    }

    @Test
    fun ignoresBlankFacts() {
        assertTrue(MemoryFactsPolicy.normalize(listOf("", "   ", "\n\t")).isEmpty())
    }

    @Test
    fun appendAddsNewFactWithoutDuplicatingExistingFact() {
        assertEquals(
            listOf("uso português", "prefiro voz"),
            MemoryFactsPolicy.append(listOf("uso português"), " PREFIRO   VOZ ")
        )
    }
}
