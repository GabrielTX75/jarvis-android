package com.gabriel.jarvis

import org.junit.Assert.assertEquals
import org.junit.Test

class AudioReadPolicyTest {
    @Test
    fun positiveReadResultsAreProcessed() {
        assertEquals(AudioReadDecision.PROCESS, AudioReadPolicy.decide(1))
        assertEquals(AudioReadDecision.PROCESS, AudioReadPolicy.decide(3200))
    }

    @Test
    fun zeroReadResultsWaitWithoutProcessing() {
        assertEquals(AudioReadDecision.WAIT, AudioReadPolicy.decide(0))
    }

    @Test
    fun negativeReadResultsRequestRecorderRecovery() {
        assertEquals(AudioReadDecision.RECOVER, AudioReadPolicy.decide(-1))
        assertEquals(AudioReadDecision.RECOVER, AudioReadPolicy.decide(-3))
        assertEquals(AudioReadDecision.RECOVER, AudioReadPolicy.decide(-6))
    }
}
