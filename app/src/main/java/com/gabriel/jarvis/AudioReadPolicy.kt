package com.gabriel.jarvis

/** Classifica o resultado de AudioRecord.read sem depender de APIs Android. */
internal enum class AudioReadDecision {
    PROCESS,
    WAIT,
    RECOVER
}

internal object AudioReadPolicy {
    fun decide(readResult: Int): AudioReadDecision = when {
        readResult > 0 -> AudioReadDecision.PROCESS
        readResult == 0 -> AudioReadDecision.WAIT
        else -> AudioReadDecision.RECOVER
    }
}
