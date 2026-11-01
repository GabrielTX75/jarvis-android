package com.gabriel.jarvis

import android.app.Notification
import android.app.PendingIntent
import android.app.RemoteInput
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.Handler
import android.os.Looper
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.CompletableFuture
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/** Guarda a resposta de cada notificação do WhatsApp para poder responder depois. */
object WhatsAppBridge {
    val replies = ConcurrentHashMap<String, Pair<Notification.Action, RemoteInput>>()

    fun reply(context: Context, key: String, text: String): Boolean {
        val entry = replies[key] ?: return false
        return try {
            val (action, remote) = entry
            val intent = Intent()
            val bundle = Bundle().apply { putCharSequence(remote.resultKey, text) }
            RemoteInput.addResultsToIntent(arrayOf(remote), intent, bundle)
            val pending: PendingIntent = action.actionIntent
            pending.send(context, 0, intent)
            true
        } catch (e: Exception) {
            false
        }
    }
}

/**
 * Responde o WhatsApp sozinho, em segundo plano: o serviço de notificações fica ativo
 * mesmo com o JARVIS fechado. Configuração vem de "jarvis_wpp" (salva pela tela de ajustes).
 */
class WhatsAppNotificationService : NotificationListenerService() {
    private val worker = Executors.newSingleThreadExecutor()
    private val recentes = ConcurrentHashMap<String, Long>()

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (sbn.packageName != "com.whatsapp" && sbn.packageName != "com.whatsapp.w4b") return
        val n = sbn.notification ?: return
        if ((n.flags and Notification.FLAG_GROUP_SUMMARY) != 0) return
        val cfg = getSharedPreferences("jarvis_wpp", Context.MODE_PRIVATE)
        if (!cfg.getBoolean("auto", false)) return
        val extras = n.extras ?: return
        val isGroup = Build.VERSION.SDK_INT >= 28 && extras.getBoolean("android.isGroupConversation", false)
        val titulo = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString()?.trim().orEmpty()
        var remetente = titulo
        var texto = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString()?.trim().orEmpty()
        if (isGroup) {
            val last = extras.getParcelableArray("android.messages")?.lastOrNull() as? Bundle
            if (last != null) {
                val body = last.getCharSequence("text")?.toString()?.trim().orEmpty()
                val name = last.getCharSequence("sender")?.toString()?.trim().orEmpty()
                if (body.isNotEmpty()) texto = body
                if (name.isNotEmpty()) remetente = name
            }
        }
        if (titulo.isEmpty() || texto.isEmpty()) return
        if (remetente.equals("Você", true) || remetente.equals("You", true)) return
        val agora = System.currentTimeMillis()
        if (agora - (recentes[titulo] ?: 0L) < 120_000L) return
        recentes[titulo] = agora
        val replyAction = n.actions?.firstOrNull { !it.remoteInputs.isNullOrEmpty() } ?: return
        WhatsAppBridge.replies[sbn.key] = Pair(replyAction, replyAction.remoteInputs.first())
        val ehAudio = Regex("(🎤|🎙)|^(áudio|audio)\\b", RegexOption.IGNORE_CASE).containsMatchIn(texto)
        val chave = sbn.key
        val postado = sbn.postTime
        worker.execute { responder(chave, titulo, remetente, texto, isGroup, ehAudio, postado, cfg) }
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {
        WhatsAppBridge.replies.remove(sbn.key)
    }

    private fun responder(
        chave: String, titulo: String, remetente: String, texto0: String,
        grupo: Boolean, ehAudio: Boolean, postado: Long, cfg: android.content.SharedPreferences
    ) {
        var texto = texto0
        if (ehAudio) {
            val transcrito = ouvirAudio(postado)
            if (transcrito.isNullOrBlank()) {
                if (!grupo) enviar(chave, "Não consegui ouvir seu áudio agora. Pode escrever, por favor?")
                return
            }
            texto = transcrito.trim()
        }
        if (grupo) {
            val nome = normaliza(cfg.getString("nome", "") ?: "")
            if (nome.isEmpty() || !normaliza(texto).contains("@$nome")) return
        }
        val resposta = pedirIa(titulo, remetente, texto, grupo, ehAudio, cfg) ?: return
        enviar(chave, resposta)
    }

    private fun enviar(chave: String, texto: String) {
        WhatsAppBridge.reply(this, chave, texto.take(600))
    }

    private fun ouvirAudio(postado: Long): String? {
        val pronto = CompletableFuture<Boolean>()
        Handler(Looper.getMainLooper()).post { AudioTranscriber.ensureModel(this) { pronto.complete(it) } }
        if (!pronto.get(60, TimeUnit.SECONDS)) return null
        var arquivo: File? = null
        val limite = System.currentTimeMillis() + 20_000L
        while (arquivo == null && System.currentTimeMillis() < limite) {
            arquivo = AudioTranscriber.newestVoiceNote(postado - 5_000L)
            if (arquivo == null) Thread.sleep(1000)
        }
        if (arquivo == null) return null
        Thread.sleep(1500)
        return try { AudioTranscriber.transcribe(arquivo) } catch (e: Exception) { null }
    }

    private fun pedirIa(
        titulo: String, remetente: String, texto: String, grupo: Boolean, ehAudio: Boolean,
        cfg: android.content.SharedPreferences
    ): String? {
        val endpoint = cfg.getString("endpoint", "") ?: ""
        val modelo = cfg.getString("model", "") ?: ""
        if (!(endpoint.startsWith("http://") || endpoint.startsWith("https://"))) return null
        val chave = try { WhatsAppSecrets.chaveIa(this) } catch (e: Exception) { "" }
        val sistema = "Você responde mensagens de WhatsApp em nome do dono do JARVIS. Responda em português do Brasil, em até 2 frases, de forma educada e natural. Não prometa nada, não invente informações e não envie dados pessoais nem senhas. Se a mensagem tratar de dinheiro, local, compromisso ou algo importante, diga apenas que o dono verá e responderá em breve. Devolva somente o texto da resposta."
        val usuario = (if (grupo) "Você foi marcado no grupo $titulo por $remetente" else "Mensagem de $remetente") +
            (if (ehAudio) " (áudio transcrito)" else "") + ": " + texto
        val corpo = JSONObject()
            .put("model", modelo)
            .put("stream", false)
            .put("messages", JSONArray()
                .put(JSONObject().put("role", "system").put("content", sistema))
                .put(JSONObject().put("role", "user").put("content", usuario)))
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
            JSONObject(resp).getJSONArray("choices").getJSONObject(0)
                .getJSONObject("message").getString("content").trim()
                .takeIf { it.isNotEmpty() }
        } catch (e: Exception) {
            null
        }
    }

    private fun normaliza(s: String): String =
        java.text.Normalizer.normalize(s, java.text.Normalizer.Form.NFD)
            .replace(Regex("\\p{M}+"), "").lowercase(java.util.Locale.ROOT).trim()
}

/** Acesso à chave da IA guardada criptografada (mesmo arquivo usado pela tela). */
object WhatsAppSecrets {
    fun chaveIa(context: Context): String {
        val masterKey = androidx.security.crypto.MasterKey.Builder(context.applicationContext)
            .setKeyScheme(androidx.security.crypto.MasterKey.KeyScheme.AES256_GCM).build()
        val prefs = androidx.security.crypto.EncryptedSharedPreferences.create(
            context.applicationContext, "jarvis_segredos", masterKey,
            androidx.security.crypto.EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            androidx.security.crypto.EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
        return prefs.getString("ai_key", "") ?: ""
    }
}
