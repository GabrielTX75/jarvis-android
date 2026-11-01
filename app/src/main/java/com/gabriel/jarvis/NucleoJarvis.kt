package com.gabriel.jarvis

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.PixelFormat
import android.graphics.RadialGradient
import android.graphics.Shader
import android.graphics.drawable.GradientDrawable
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.Image
import android.media.ImageReader
import android.media.MediaRecorder
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Base64
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import org.json.JSONArray
import org.json.JSONObject
import org.vosk.Recognizer
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale
import java.util.concurrent.CompletableFuture
import java.util.concurrent.TimeUnit

/** Estado da captura de tela enquanto a permissão do usuário estiver valendo. */
object TelaCaptura {
    @Volatile var resultCode: Int = 0
    @Volatile var dados: Intent? = null
    @Volatile var projecao: MediaProjection? = null
    @Volatile var leitor: ImageReader? = null
    @Volatile var virtual: VirtualDisplay? = null
    @Volatile var aoResponder: ((Boolean) -> Unit)? = null
}

/** Tela transparente que mostra o pedido de captura do Android e devolve a resposta. */
class PedirCapturaActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val mpm = getSystemService(MediaProjectionManager::class.java)
        @Suppress("DEPRECATION")
        startActivityForResult(mpm.createScreenCaptureIntent(), REQ)
    }

    @Suppress("DEPRECATION", "OVERRIDE_DEPRECATION")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQ) {
            val ok = resultCode == RESULT_OK && data != null
            if (ok) {
                TelaCaptura.resultCode = resultCode
                TelaCaptura.dados = data
            }
            TelaCaptura.aoResponder?.invoke(ok)
            TelaCaptura.aoResponder = null
        }
        finish()
    }

    companion object { const val REQ = 5101 }
}

/** Núcleo flutuante: esfera dourada com anéis HUD e fragmentos girando. Modo 0 ouvindo, 1 pensando, 2 falando. */
class OrbView(context: Context) : View(context) {
    private val pincel = Paint(Paint.ANTI_ALIAS_FLAG)
    private val ouro = Color.rgb(255, 180, 40)
    private val claro = Color.rgb(255, 236, 170)
    private val fundo = Color.rgb(40, 20, 0)
    private var angulo = 0f
    var modo: Int = 0
        set(v) { field = v; invalidate() }
    private val fragmentos = List(16) {
        Pair(kotlin.random.Random.nextFloat() * 360f, 0.7f + kotlin.random.Random.nextFloat() * 0.5f)
    }
    private val animar = object : Runnable {
        override fun run() {
            angulo = (angulo + (if (modo == 1) 3.5f else 1.2f)) % 360f
            invalidate()
            postOnAnimation(this)
        }
    }

    init { postOnAnimation(animar) }

    override fun onDetachedFromWindow() {
        removeCallbacks(animar)
        super.onDetachedFromWindow()
    }

    override fun onDraw(c: Canvas) {
        super.onDraw(c)
        val cx = width / 2f
        val cy = height / 2f
        val base = minOf(width, height) / 2f * 0.5f
        val pulso = if (modo == 2) 0.06f * (1f + kotlin.math.sin(Math.toRadians(angulo * 6.0)).toFloat()) else 0f
        val r = base * (1f + pulso)
        pincel.style = Paint.Style.FILL
        pincel.shader = RadialGradient(
            cx - r * 0.35f, cy - r * 0.35f, r * 1.7f,
            intArrayOf(claro, ouro, fundo, Color.BLACK), floatArrayOf(0f, 0.4f, 0.85f, 1f), Shader.TileMode.CLAMP
        )
        c.drawCircle(cx, cy, r, pincel)
        pincel.shader = null
        pincel.style = Paint.Style.STROKE
        pincel.color = ouro
        pincel.strokeWidth = r * 0.04f
        for (i in 0 until 3) {
            val rr = r * (1.25f + i * 0.22f)
            val sentido = if (i % 2 == 0) 1f else -1f
            val inicio = angulo * sentido * (0.6f + i * 0.5f)
            for (k in 0 until 3) c.drawArc(cx - rr, cy - rr, cx + rr, cy + rr, inicio + k * 120f, 70f, false, pincel)
        }
        pincel.style = Paint.Style.FILL
        pincel.color = claro
        for ((a, d) in fragmentos) {
            val ang = Math.toRadians((a + angulo * 0.7f).toDouble())
            val rr = r * (1.1f + (d - 0.7f) * 0.9f)
            c.drawCircle(cx + rr * kotlin.math.cos(ang).toFloat(), cy + rr * kotlin.math.sin(ang).toFloat(), r * 0.035f, pincel)
        }
    }
}

/** Uma conversa com o núcleo flutuante: ouve, pensa, responde falando e pode olhar a tela. */
class NucleoSessao(private val servico: JarvisOuvidoService, private val aoEncerrar: () -> Unit) {
    private val ctx: Context get() = servico
    private val main = Handler(Looper.getMainLooper())
    private val wm = servico.getSystemService(Context.WINDOW_SERVICE) as WindowManager
    private var orb: View? = null
    @Volatile var ativa = false
        private set
    @Volatile private var falando = false
    @Volatile private var ttsPronto = false
    private var tts: TextToSpeech? = null
    private val historico = ArrayList<JSONObject>()

    fun iniciar() {
        if (ativa) return
        ativa = true
        main.post { mostrarOrb() }
        tts = TextToSpeech(ctx) { st ->
            if (st == TextToSpeech.SUCCESS) {
                val r = tts?.setLanguage(Locale("pt", "BR"))
                ttsPronto = r != TextToSpeech.LANG_MISSING_DATA && r != TextToSpeech.LANG_NOT_SUPPORTED
            }
        }
        AudioTranscriber.ensureModel(ctx) { ok ->
            if (ok) {
                val m = AudioTranscriber.modelo()
                if (m != null) Thread { ouvir(m) }.start() else encerrar()
            } else {
                encerrar()
            }
        }
    }

    private fun ouvir(modelo: org.vosk.Model) {
        val tamanho = maxOf(AudioRecord.getMinBufferSize(16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT), 8000)
        val gravador = AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION, 16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, tamanho)
        val rec = Recognizer(modelo, 16000f)
        try {
            gravador.startRecording()
        } catch (e: Exception) {
            gravador.release(); rec.close(); encerrar(); return
        }
        falar("Pode falar, senhor.")
        var ultimo = System.currentTimeMillis()
        val buf = ByteArray(3200)
        while (ativa) {
            val n = gravador.read(buf, 0, buf.size)
            if (n <= 0) continue
            if (falando) { rec.reset(); ultimo = System.currentTimeMillis(); continue }
            if (rec.acceptWaveForm(buf, n)) {
                val texto = JSONObject(rec.result).optString("text", "").trim()
                if (texto.isNotEmpty()) {
                    ultimo = System.currentTimeMillis()
                    processar(texto)
                }
            }
            if (System.currentTimeMillis() - ultimo > 45_000L) {
                falar("Vou ficar em silêncio. Diga Jarvis quando precisar.")
                encerrar()
                break
            }
        }
        try { gravador.stop() } catch (_: Exception) {}
        gravador.release()
        rec.close()
    }

    private fun processar(texto: String) {
        val t = semAcento(texto)
        if (Regex("\\b(tchau|encerrar|encerra|fechar|ate logo)\\b").containsMatchIn(t)) {
            falar("Até logo, senhor.")
            encerrar()
            return
        }
        var imagem: String? = null
        definir(1)
        if (t.contains("tela")) {
            imagem = pegarTela()
            if (imagem == null) {
                falar("Não consegui ver sua tela agora. Confira se a permissão foi concedida.")
                return
            }
        }
        val resposta = pedirIa(texto, imagem)
        falar(resposta ?: "Não consegui pensar agora. Confira a IA nas configurações.")
    }

    private fun pegarTela(): String? {
        if (TelaCaptura.virtual == null) {
            val concedido = pedirConsentimento() ?: return null
            if (!concedido) return null
            if (!montarCaptura()) return null
        }
        val leitor = TelaCaptura.leitor ?: return null
        val limite = System.currentTimeMillis() + 3000L
        var img: Image? = null
        while (img == null && System.currentTimeMillis() < limite) {
            img = leitor.acquireLatestImage()
            if (img == null) Thread.sleep(100)
        }
        if (img == null) return null
        return try { imagemParaBase64(img) } catch (e: Exception) { null } finally { img.close() }
    }

    private fun pedirConsentimento(): Boolean? {
        val futuro = CompletableFuture<Boolean>()
        TelaCaptura.aoResponder = { futuro.complete(it) }
        main.post {
            ctx.startActivity(Intent(ctx, PedirCapturaActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        }
        return try { futuro.get(60, TimeUnit.SECONDS) } catch (e: Exception) { null }
    }

    private fun montarCaptura(): Boolean {
        return try {
            servico.modoCaptura(true)
            val mpm = servico.getSystemService(MediaProjectionManager::class.java)
            val proj = mpm.getMediaProjection(TelaCaptura.resultCode, TelaCaptura.dados!!)
            proj.registerCallback(object : MediaProjection.Callback() {
                override fun onStop() { liberarCaptura() }
            }, main)
            val dm = servico.resources.displayMetrics
            val w = dm.widthPixels / 2
            val h = dm.heightPixels / 2
            val leitor = ImageReader.newInstance(w, h, PixelFormat.RGBA_8888, 2)
            val virtual = proj.createVirtualDisplay(
                "jarvis-tela", w, h, dm.densityDpi,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR, leitor.surface, null, main
            )
            TelaCaptura.projecao = proj
            TelaCaptura.leitor = leitor
            TelaCaptura.virtual = virtual
            true
        } catch (e: Exception) {
            liberarCaptura()
            false
        }
    }

    fun liberarCaptura() {
        val v = TelaCaptura.virtual; val l = TelaCaptura.leitor; val p = TelaCaptura.projecao
        TelaCaptura.virtual = null; TelaCaptura.leitor = null; TelaCaptura.projecao = null
        try { v?.release() } catch (_: Exception) {}
        try { l?.close() } catch (_: Exception) {}
        try { p?.stop() } catch (_: Exception) {}
        if (v != null || p != null) servico.modoCaptura(false)
    }

    private fun imagemParaBase64(img: Image): String {
        val plano = img.planes[0]
        val folga = plano.rowStride - plano.pixelStride * img.width
        val bmp = Bitmap.createBitmap(img.width + folga / plano.pixelStride, img.height, Bitmap.Config.ARGB_8888)
        bmp.copyPixelsFromBuffer(plano.buffer)
        val recorte = Bitmap.createBitmap(bmp, 0, 0, img.width, img.height)
        val out = ByteArrayOutputStream()
        recorte.compress(Bitmap.CompressFormat.JPEG, 70, out)
        return Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP)
    }

    private fun pedirIa(texto: String, imagem: String?): String? {
        val cfg = servico.getSharedPreferences("jarvis_wpp", Context.MODE_PRIVATE)
        val endpoint = cfg.getString("endpoint", "") ?: ""
        val modelo = cfg.getString("model", "") ?: ""
        if (!(endpoint.startsWith("http://") || endpoint.startsWith("https://"))) return null
        val chave = Cofre.ler(ctx, "ai_key")
        val msgs = JSONArray().put(JSONObject().put("role", "system").put("content",
            "Você é o JARVIS, um assistente pessoal falado. Responda em português do Brasil, em até 3 frases curtas, sem markdown e sem listas. Trate o usuário por senhor."))
        historico.takeLast(8).forEach { msgs.put(it) }
        val conteudo: Any = if (imagem == null) texto else JSONArray()
            .put(JSONObject().put("type", "text").put("text", texto))
            .put(JSONObject().put("type", "image_url").put("image_url",
                JSONObject().put("url", "data:image/jpeg;base64,$imagem")))
        msgs.put(JSONObject().put("role", "user").put("content", conteudo))
        val corpo = JSONObject().put("model", modelo).put("stream", false).put("messages", msgs)
        val resposta = chamarIa(endpoint, chave, corpo)?.trim()?.takeIf { it.isNotEmpty() } ?: return null
        historico.add(JSONObject().put("role", "user").put("content", texto))
        historico.add(JSONObject().put("role", "assistant").put("content", resposta))
        while (historico.size > 16) historico.removeAt(0)
        return resposta
    }

    private fun chamarIa(endpoint: String, chave: String, corpo: JSONObject): String? {
        return try {
            val conn = (URL(endpoint).openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = 15_000
                readTimeout = 60_000
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
                if (chave.isNotEmpty()) setRequestProperty("Authorization", "Bearer $chave")
            }
            conn.outputStream.use { it.write(corpo.toString().toByteArray(Charsets.UTF_8)) }
            if (conn.responseCode !in 200..299) return null
            val resp = conn.inputStream.bufferedReader().use { it.readText() }
            JSONObject(resp).getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content")
        } catch (e: Exception) {
            null
        }
    }

    private fun falar(texto: String) {
        val t = tts ?: return
        if (!ttsPronto) return
        falando = true
        definir(2)
        t.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(id: String?) {}
            override fun onDone(id: String?) { falando = false; definir(0) }
            override fun onError(id: String?) { falando = false; definir(0) }
        })
        t.speak(texto.take(600), TextToSpeech.QUEUE_FLUSH, null, "jv-" + System.nanoTime())
    }

    private fun definir(m: Int) {
        main.post { (orb as? OrbView)?.modo = m }
    }

    private fun mostrarOrb() {
        val v = OrbView(ctx)
        val tamanho = (ctx.resources.displayMetrics.density * 150).toInt()
        val params = WindowManager.LayoutParams(
            tamanho, tamanho,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT
        )
        params.gravity = Gravity.TOP or Gravity.START
        params.x = 40
        params.y = 300
        var x0 = 0
        var y0 = 0
        var tx = 0f
        var ty = 0f
        var moveu = false
        v.setOnTouchListener { _, e ->
            when (e.action) {
                MotionEvent.ACTION_DOWN -> {
                    x0 = params.x; y0 = params.y; tx = e.rawX; ty = e.rawY; moveu = false; true
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx = (e.rawX - tx).toInt()
                    val dy = (e.rawY - ty).toInt()
                    if (Math.abs(dx) > 8 || Math.abs(dy) > 8) moveu = true
                    params.x = x0 + dx
                    params.y = y0 + dy
                    try { wm.updateViewLayout(v, params) } catch (_: Exception) {}
                    true
                }
                MotionEvent.ACTION_UP -> {
                    if (!moveu) encerrar()
                    true
                }
                else -> false
            }
        }
        try {
            wm.addView(v, params)
            orb = v
        } catch (e: Exception) {
            encerrar()
        }
    }

    fun encerrar() {
        if (!ativa) return
        ativa = false
        main.post {
            orb?.let { try { wm.removeView(it) } catch (_: Exception) {} }
            orb = null
        }
        liberarCaptura()
        main.postDelayed({ try { tts?.shutdown() } catch (_: Exception) {}; tts = null }, 4000L)
        aoEncerrar()
    }

    private fun semAcento(x: String): String =
        java.text.Normalizer.normalize(x, java.text.Normalizer.Form.NFD)
            .replace(Regex("\\p{M}+"), "").lowercase(Locale.ROOT)
}
