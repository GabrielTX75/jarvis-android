package com.gabriel.jarvis

import android.app.Notification
import android.app.PendingIntent
import android.app.RemoteInput
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import java.util.concurrent.ConcurrentHashMap

/** Ponte entre o serviço de notificações e a página do JARVIS. */
object WhatsAppBridge {
    // chave da notificação -> ação de resposta (com o campo de texto)
    val replies = ConcurrentHashMap<String, Pair<Notification.Action, RemoteInput>>()
    @Volatile var onMessage: ((String, String, String) -> Unit)? = null

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

class WhatsAppNotificationService : NotificationListenerService() {
    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (sbn.packageName != "com.whatsapp" && sbn.packageName != "com.whatsapp.w4b") return
        val n = sbn.notification ?: return
        if ((n.flags and Notification.FLAG_GROUP_SUMMARY) != 0) return
        val extras = n.extras ?: return
        // Grupos são ignorados para não responder em conversas coletivas.
        val isGroup = Build.VERSION.SDK_INT >= 28 && extras.getBoolean("android.isGroupConversation", false)
        if (isGroup) return
        val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString()?.trim().orEmpty()
        val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString()?.trim().orEmpty()
        if (title.isEmpty() || text.isEmpty()) return
        if (title.equals("Você", true) || title.equals("You", true)) return
        val replyAction = n.actions?.firstOrNull { !it.remoteInputs.isNullOrEmpty() } ?: return
        val remote = replyAction.remoteInputs.first()
        WhatsAppBridge.replies[sbn.key] = Pair(replyAction, remote)
        WhatsAppBridge.onMessage?.invoke(sbn.key, title, text)
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {
        WhatsAppBridge.replies.remove(sbn.key)
    }
}
