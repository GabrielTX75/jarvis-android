package com.gabriel.jarvis

import android.content.Context
import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import org.json.JSONObject
import org.vosk.Model
import org.vosk.Recognizer
import org.vosk.android.StorageService
import java.io.ByteArrayOutputStream
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Transcrição offline de áudios do WhatsApp (Vosk, português). */
object AudioTranscriber {
    @Volatile private var model: Model? = null
    private var loading = false

    /** Carrega o modelo uma vez. Chame na thread principal. */
    @Synchronized
    fun ensureModel(context: Context, onReady: (Boolean) -> Unit) {
        model?.let { onReady(true); return }
        if (loading) { onReady(false); return }
        loading = true
        StorageService.unpack(context, "model-pt", "model",
            { m -> model = m; loading = false; onReady(true) },
            { _ -> loading = false; onReady(false) })
    }

    fun modelo(): Model? = model

    fun newestVoiceNote(sinceMs: Long): File? {
        val base = android.os.Environment.getExternalStorageDirectory()
        val pastas = listOf(
            "Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Voice Notes",
            "Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Audio",
            "WhatsApp/Media/WhatsApp Voice Notes",
            "WhatsApp/Media/WhatsApp Audio"
        )
        return pastas.map { File(base, it) }
            .filter { it.isDirectory }
            .flatMap { it.listFiles()?.toList() ?: emptyList() }
            .filter { it.isFile && it.length() > 0 && it.lastModified() >= sinceMs }
            .filter { it.extension.equals("opus", true) || it.extension.equals("ogg", true) || it.extension.equals("m4a", true) }
            .maxByOrNull { it.lastModified() }
    }

    fun transcribe(file: File): String {
        val m = model ?: throw IllegalStateException("modelo não carregado")
        val pcm = decodeTo16kMono(file)
        val rec = Recognizer(m, 16000f)
        try {
            var offset = 0
            while (offset < pcm.size) {
                val n = minOf(8000, pcm.size - offset)
                rec.acceptWaveForm(pcm.copyOfRange(offset, offset + n), n)
                offset += n
            }
            return JSONObject(rec.finalResult).optString("text", "").trim()
        } finally {
            rec.close()
        }
    }

    private fun decodeTo16kMono(file: File): ByteArray {
        val extractor = MediaExtractor()
        extractor.setDataSource(file.absolutePath)
        var format: MediaFormat? = null
        var track = -1
        for (i in 0 until extractor.trackCount) {
            val f = extractor.getTrackFormat(i)
            if ((f.getString(MediaFormat.KEY_MIME) ?: "").startsWith("audio/")) { format = f; track = i; break }
        }
        if (format == null || track < 0) { extractor.release(); throw IllegalStateException("sem faixa de áudio") }
        extractor.selectTrack(track)
        val codec = MediaCodec.createDecoderByType(format.getString(MediaFormat.KEY_MIME)!!)
        codec.configure(format, null, null, 0)
        codec.start()
        val rate = format.getInteger(MediaFormat.KEY_SAMPLE_RATE)
        val channels = format.getInteger(MediaFormat.KEY_CHANNEL_COUNT)
        val raw = ByteArrayOutputStream()
        val info = MediaCodec.BufferInfo()
        var inputDone = false
        var outputDone = false
        try {
            while (!outputDone) {
                if (!inputDone) {
                    val inIdx = codec.dequeueInputBuffer(10_000)
                    if (inIdx >= 0) {
                        val buf = codec.getInputBuffer(inIdx)!!
                        val size = extractor.readSampleData(buf, 0)
                        if (size < 0) {
                            codec.queueInputBuffer(inIdx, 0, 0, 0, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
                            inputDone = true
                        } else {
                            codec.queueInputBuffer(inIdx, 0, size, extractor.sampleTime, 0)
                            extractor.advance()
                        }
                    }
                }
                val outIdx = codec.dequeueOutputBuffer(info, 10_000)
                if (outIdx >= 0) {
                    val buf = codec.getOutputBuffer(outIdx)!!
                    if (info.size > 0) {
                        val chunk = ByteArray(info.size)
                        buf.position(info.offset)
                        buf.get(chunk)
                        raw.write(chunk)
                    }
                    codec.releaseOutputBuffer(outIdx, false)
                    if ((info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0) outputDone = true
                }
            }
        } finally {
            codec.stop()
            codec.release()
            extractor.release()
        }
        return toMono16k(raw.toByteArray(), rate, maxOf(1, channels))
    }

    private fun toMono16k(pcm: ByteArray, rate: Int, channels: Int): ByteArray {
        val frames = pcm.size / (2 * channels)
        if (frames == 0) return ByteArray(0)
        val src = ByteBuffer.wrap(pcm).order(ByteOrder.LITTLE_ENDIAN)
        val mono = ShortArray(frames)
        for (f in 0 until frames) {
            var sum = 0
            for (c in 0 until channels) sum += src.getShort((f * channels + c) * 2).toInt()
            mono[f] = (sum / channels).toShort()
        }
        val outLen = (frames.toLong() * 16000L / rate).toInt()
        val out = ByteArray(outLen * 2)
        val dst = ByteBuffer.wrap(out).order(ByteOrder.LITTLE_ENDIAN)
        for (i in 0 until outLen) {
            val pos = i.toDouble() * rate / 16000.0
            val i0 = pos.toInt().coerceAtMost(frames - 1)
            val i1 = (i0 + 1).coerceAtMost(frames - 1)
            val frac = pos - i0
            val v = mono[i0] * (1 - frac) + mono[i1] * frac
            dst.putShort(i * 2, v.toInt().toShort())
        }
        return out
    }
}
