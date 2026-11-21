package com.gabriel.jarvis

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build

class ReminderReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val title = intent.getStringExtra("title") ?: "Compromisso"
        val eventTime = intent.getLongExtra("event_time", 0L)
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channelId = "jarvis_reminders"
        if (Build.VERSION.SDK_INT >= 26) {
            manager.createNotificationChannel(
                NotificationChannel(channelId, "Lembretes do JARVIS", NotificationManager.IMPORTANCE_HIGH)
            )
        }
        val open = PendingIntent.getActivity(
            context, title.hashCode(),
            Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val time = if (eventTime > 0) java.text.SimpleDateFormat("HH:mm", java.util.Locale("pt", "BR")).format(java.util.Date(eventTime)) else ""
        val notification = if (Build.VERSION.SDK_INT >= 26) {
            Notification.Builder(context, channelId)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle("Lembrete do JARVIS")
                .setContentText("$title — às $time")
                .setStyle(Notification.BigTextStyle().bigText("$title — às $time. Este é o aviso programado 10 minutos antes."))
                .setContentIntent(open)
                .setAutoCancel(true)
                .setCategory(Notification.CATEGORY_REMINDER)
                .build()
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(context)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle("Lembrete do JARVIS")
                .setContentText("$title — às $time")
                .setContentIntent(open)
                .setAutoCancel(true)
                .build()
        }
        manager.notify((title + eventTime).hashCode(), notification)
    }
}
