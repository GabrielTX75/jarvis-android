package com.gabriel.jarvis

import android.accessibilityservice.AccessibilityService
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

/**
 * Cola texto no campo editável do app que estiver na frente (ex.: Pydroid 3).
 * Só funciona depois que você liga o JARVIS em Configurações > Acessibilidade.
 * Não lê nem guarda nada da tela: só insere o texto pedido, e só no app indicado.
 */
class JarvisAcessibilidade : AccessibilityService() {

    override fun onServiceConnected() {
        super.onServiceConnected()
        ativa = this
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}

    override fun onInterrupt() {}

    override fun onUnbind(intent: Intent?): Boolean {
        if (ativa === this) ativa = null
        return super.onUnbind(intent)
    }

    override fun onDestroy() {
        if (ativa === this) ativa = null
        super.onDestroy()
    }

    /** Tenta colar [texto] no campo editável do app [pacote]. Devolve true se conseguiu. */
    fun colar(pacote: String, texto: String): Boolean {
        val raiz = rootInActiveWindow ?: return false
        if (raiz.packageName?.toString() != pacote) return false
        val campo = raiz.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)?.takeIf { it.isEditable }
            ?: acharEditavel(raiz)
            ?: return false
        val args = Bundle().apply {
            putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, texto)
        }
        return campo.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
    }

    private fun acharEditavel(no: AccessibilityNodeInfo): AccessibilityNodeInfo? {
        if (no.isEditable && no.isVisibleToUser) return no
        for (i in 0 until no.childCount) {
            val filho = no.getChild(i) ?: continue
            acharEditavel(filho)?.let { return it }
        }
        return null
    }

    companion object {
        /** Instância viva do serviço (null quando desligado). */
        @Volatile var ativa: JarvisAcessibilidade? = null

        /** Confere nas configurações do sistema se o usuário ligou o serviço. */
        fun ligada(context: Context): Boolean {
            val lista = Settings.Secure.getString(
                context.contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
            ) ?: return false
            return lista.contains(ComponentName(context, JarvisAcessibilidade::class.java).flattenToString())
        }
    }
}
