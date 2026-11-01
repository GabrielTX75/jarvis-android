package com.gabriel.jarvis

import ai.picovoice.porcupine.Porcupine
import ai.picovoice.porcupine.PorcupineManager
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * Fica em segundo plano ouvindo a palavra "Jarvis" (Porcupine, offline).
 * Quando ouve, mostra um alerta de tela cheia que abre o app.
 */
class JarvisOuvidoService : Service() {
    private var manager: PorcupineManager? = null
    private var ultimoAlerta = 0L

    companion object {
        private const val CANAL_OUVIR = "jarvis_ouvir"
        private const val CANAL_ALERTA = "jarvis_alerta"
        private const val ID_OUVIR = 77
        private const val ID_ALERTA = 78
        @Volatile private var instancia: JarvisOuvidoService? = null
        @Volatile private var tela = false

        /** Chamado pela tela: quando o app está visível, o microfone fica com a tela. */
        fun telaAtiva(ativa: Boolean) {
            tela = ativa
            instancia?.let { if (ativa) it.pausar() else it.retomar() }
        }
    }

    override fun onCreate() {
        super.onCreate()
        instancia = this
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel(CANAL_OUVIR, "JARVIS ouvindo", NotificationManager.IMPORTANCE_LOW))
        nm.createNotificationChannel(NotificationChannel(CANAL_ALERTA, "JARVIS chamando", NotificationManager.IMPORTANCE_HIGH))
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notif = Notification.Builder(this, CANAL_OUVIR)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("JARVIS em segundo plano")
            .setContentText("Sempre ouvindo. Diga \"Jarvis\" para abrir o app.")
            .setOngoing(true)
            .setContentIntent(abrirApp(2, false))
            .build()
        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(ID_OUVIR, notif, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
        } else {
            startForeground(ID_OUVIR, notif)
        }
        if (manager == null && !tela) ligar()
        return START_STICKY
    }

    override fun onDestroy() {
        parar()
        instancia = null
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun ligar() {
        val chave = Cofre.ler(this, "picovoice_key")
        if (chave.isEmpty()) return
        try {
            manager = PorcupineManager.Builder()
                .setAccessKey(chave)
                .setKeyword(Porcupine.BuiltInKeyword.JARVIS)
                .build(applicationContext) { _ -> aoOuvirJarvis() }
            manager?.start()
        } catch (e: Exception) {
            manager = null
        }
    }

    private fun parar() {
        try { manager?.stop(); manager?.delete() } catch (_: Exception) {}
        manager = null
    }

    private fun pausar() {
        try { manager?.stop() } catch (_: Exception) {}
    }

    private fun retomar() {
        if (manager == null) { ligar(); return }
        try { manager?.start() } catch (_: Exception) {}
    }

    private fun aoOuvirJarvis() {
        if (tela) return
        val agora = System.currentTimeMillis()
        if (agora - ultimoAlerta < 5_000L) return
        ultimoAlerta = agora
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
        try { abrir.send() } catch (_: Exception) {}
    }

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
        val masterKey = MasterKey.Builder(context.applicationContext)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build()
        val p = EncryptedSharedPreferences.create(
            context.applicationContext, "jarvis_segredos", masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
        p.getString(nome, "") ?: ""
    } catch (e: Exception) {
        ""
    }
}
