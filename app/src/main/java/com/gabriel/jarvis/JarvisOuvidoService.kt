package com.gabriel.jarvis

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.provider.Settings
import org.json.JSONObject
import org.vosk.Recognizer
import java.util.Locale
import java.util.concurrent.CompletableFuture
import java.util.concurrent.TimeUnit

/**
 * Fica em segundo plano ouvindo a palavra "Jarvis" (Vosk, offline).
 * Quando ouve, abre o núcleo flutuante (ou um alerta, se não houver permissão de sobreposição).
 * A notificação mostra o que está sendo ouvido, para testar a detecção.
 */
class JarvisOuvidoService : Service() {
    private var ultimoAlerta = 0L
    private var sessao: NucleoSessao? = null
    private var capturando = false
    @Volatile private var vivo = false
    private var escuta: Thread? = null
    @Volatile private var estado = "Iniciando…"
    private var ultimoStatus = 0L

    companion object {
        private const val CANAL_OUVIR = "jarvis_ouvir"
        private const val CANAL_ALERTA = "jarvis_alerta"
        private const val ID_OUVIR = 77
        private const val ID_ALERTA = 78
        private val PADRAO_JARVIS = Regex("(jarvi|jarbi|javi|chavi|charvi|ja vi)s?")
        @Volatile private var tela = false

        /** Chamado pela tela: quando o app está visível, o microfone fica com a tela. */
        fun telaAtiva(ativa: Boolean) {
            tela = ativa
        }
    }

    override fun onCreate() {
        super.onCreate()
        vivo = true
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel(CANAL_OUVIR, "JARVIS ouvindo", NotificationManager.IMPORTANCE_LOW))
        nm.createNotificationChannel(NotificationChannel(CANAL_ALERTA, "JARVIS chamando", NotificationManager.IMPORTANCE_HIGH))
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        try {
            iniciarPrimeiroPlano()
        } catch (_: Exception) {
            getSharedPreferences("jarvis_ouvir", MODE_PRIVATE).edit().putBoolean("ativo", false).apply()
            stopSelf(startId)
            return START_NOT_STICKY
        }
        if (escuta == null) {
            escuta = Thread {
                var tentativas = 0
                while (vivo && AudioTranscriber.modelo() == null && tentativas < 30) {
                    val pronto = CompletableFuture<Boolean>()
                    Handler(Looper.getMainLooper()).post { AudioTranscriber.ensureModel(this) { pronto.complete(it) } }
                    try { pronto.get(60, TimeUnit.SECONDS) } catch (_: Exception) {}
                    if (AudioTranscriber.modelo() == null) {
                        AudioTranscriber.cancelarCarga()
                        val motivo = AudioTranscriber.ultimoErro.take(120)
                        atualizarStatus("Modelo de voz não carregou: " + (if (motivo.isEmpty()) "sem detalhe" else motivo) + ". Tentando de novo…", true)
                        Thread.sleep(3000)
                    }
                    tentativas++
                }
                if (vivo && AudioTranscriber.modelo() != null) {
                    atualizarStatus("Ouvindo a palavra Jarvis…", true)
                    escutar()
                } else if (vivo) {
                    atualizarStatus("Não foi possível carregar o modelo de voz. A escuta foi pausada.", true)
                    getSharedPreferences("jarvis_ouvir", MODE_PRIVATE).edit().putBoolean("ativo", false).apply()
                    stopSelf()
                }
            }
            escuta?.start()
        }
        return START_STICKY
    }

    /** Liga ou desliga o tipo de serviço de captura de tela (exigido pelo Android 14). */
    fun modoCaptura(on: Boolean) {
        capturando = on
        iniciarPrimeiroPlano()
    }

    /** Atualiza a notificação fixa com o texto de estado (limitado para não sobrecarregar). */
    private fun atualizarStatus(texto: String, forca: Boolean = false) {
        val agora = System.currentTimeMillis()
        if (!forca && agora - ultimoStatus < 1500L) return
        ultimoStatus = agora
        estado = texto
        try {
            getSystemService(NotificationManager::class.java).notify(ID_OUVIR, montarNotificacao())
        } catch (_: Exception) {}
    }

    private fun montarNotificacao(): Notification =
        Notification.Builder(this, CANAL_OUVIR)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("JARVIS em segundo plano")
            .setContentText(estado)
            .setStyle(Notification.BigTextStyle().bigText(estado))
            .setVisibility(Notification.VISIBILITY_PRIVATE)
            .setOngoing(true)
            .setContentIntent(abrirApp(2, false))
            .build()

    private fun iniciarPrimeiroPlano() {
        val notif = montarNotificacao()
        if (Build.VERSION.SDK_INT >= 29) {
            var tipos = ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
            if (capturando) tipos = tipos or ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION
            startForeground(ID_OUVIR, notif, tipos)
        } else {
            startForeground(ID_OUVIR, notif)
        }
    }

    override fun onDestroy() {
        vivo = false
        escuta?.interrupt()
        sessao?.encerrar()
        sessao = null
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    /** Ouve o microfone em pedaços e procura a palavra. Pausa enquanto o app ou uma conversa usa o microfone. */
    private fun escutar() {
        val modelo = AudioTranscriber.modelo() ?: return
        val rec = Recognizer(modelo, 16000f)
        val buf = ByteArray(3200)
        var gravador: AudioRecord? = null
        var falhasDeLeitura = 0
        try {
            while (vivo) {
                if (tela || sessao != null || capturando) {
                    gravador?.let { try { it.stop() } catch (_: Exception) {}; it.release() }
                    gravador = null
                    falhasDeLeitura = 0
                    rec.reset()
                    Thread.sleep(500)
                    continue
                }
                if (gravador == null) {
                    val tamanho = maxOf(AudioRecord.getMinBufferSize(16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT), 8000)
                    try {
                        val g = AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION, 16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, tamanho)
                        g.startRecording()
                        gravador = g
                        atualizarStatus("Ouvindo a palavra Jarvis…", true)
                    } catch (e: Exception) {
                        atualizarStatus("Não consegui usar o microfone. Confira a permissão.", true)
                        Thread.sleep(2000)
                        continue
                    }
                }
                val n = try { gravador!!.read(buf, 0, buf.size) } catch (_: Exception) { -1 }
                when (AudioReadPolicy.decide(n)) {
                    AudioReadDecision.PROCESS -> {
                        falhasDeLeitura = 0
                        val fechou = rec.acceptWaveForm(buf, n)
                        val texto = if (fechou) JSONObject(rec.result).optString("text", "")
                        else JSONObject(rec.partialResult).optString("partial", "")
                        if (PADRAO_JARVIS.containsMatchIn(semAcento(texto))) {
                            rec.reset()
                            atualizarStatus("Jarvis detectado!", true)
                            aoOuvirJarvis()
                        }
                    }
                    AudioReadDecision.WAIT -> Thread.sleep(10)
                    AudioReadDecision.RECOVER -> {
                        falhasDeLeitura++
                        atualizarStatus("Microfone interrompido; tentando reconectar…", true)
                        gravador?.let { try { it.stop() } catch (_: Exception) {}; it.release() }
                        gravador = null
                        rec.reset()
                        if (falhasDeLeitura >= 3) {
                            atualizarStatus("Escuta pausada por falha no microfone. Ative novamente nas configurações do JARVIS.", true)
                            getSharedPreferences("jarvis_ouvir", MODE_PRIVATE).edit().putBoolean("ativo", false).apply()
                            stopSelf()
                            break
                        }
                        Thread.sleep(500L * falhasDeLeitura)
                    }
                }
            }
        } finally {
            gravador?.let { try { it.stop() } catch (_: Exception) {}; it.release() }
            rec.close()
        }
    }

    private fun aoOuvirJarvis() {
        if (tela || sessao != null) return
        val agora = System.currentTimeMillis()
        if (agora - ultimoAlerta < 5_000L) return
        ultimoAlerta = agora
        if (Settings.canDrawOverlays(this)) {
            val nova = NucleoSessao(this) { sessao = null }
            sessao = nova
            nova.iniciar()
            return
        }
        val abrir = abrirApp(3, true)
        val nm = getSystemService(NotificationManager::class.java)
        val alerta = Notification.Builder(this, CANAL_ALERTA)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("JARVIS")
            .setContentText("Chamando você…")
            .setFullScreenIntent(abrir, true)
            .setContentIntent(abrir)
            .setAutoCancel(true)
            .build()
        nm.notify(ID_ALERTA, alerta)
    }

    private fun semAcento(x: String): String =
        java.text.Normalizer.normalize(x, java.text.Normalizer.Form.NFD)
            .replace(Regex("\\p{M}+"), "").lowercase(Locale.ROOT)

    private fun abrirApp(codigo: Int, wake: Boolean): PendingIntent {
        val i = Intent(this, MainActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            .putExtra("wake", wake)
        return PendingIntent.getActivity(
            this, codigo, i, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
    }
}

/** Leitura de segredos guardados criptografados (mesmo arquivo da tela de chaves). */
object Cofre {
    fun ler(context: Context, nome: String): String = try {
        val masterKey = androidx.security.crypto.MasterKey.Builder(context.applicationContext)
            .setKeyScheme(androidx.security.crypto.MasterKey.KeyScheme.AES256_GCM).build()
        val p = androidx.security.crypto.EncryptedSharedPreferences.create(
            context.applicationContext, "jarvis_segredos", masterKey,
            androidx.security.crypto.EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            androidx.security.crypto.EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
        p.getString(nome, "") ?: ""
    } catch (e: Exception) {
        ""
    }
}
