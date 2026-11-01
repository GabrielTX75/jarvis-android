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
 * Permite ao JARVIS, quando o senhor liga nas configurações de acessibilidade:
 * - colar código no campo de edição do app na frente (ex.: Pydroid 3);
 * - ler o texto visível da tela, para responder perguntas sobre ela;
 * - tocar em um botão ou item pelo nome, quando o senhor pedir.
 * Nada é guardado nem enviado para fora pelo serviço: o texto só segue para a IA quando o senhor pergunta.
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
            ?: acharEditavel(raiz, 0)
            ?: return false
        val args = Bundle().apply {
            putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, texto)
        }
        return campo.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
    }

    /** Texto visível na tela, para a IA ler. Null se não houver texto. */
    fun lerTela(): String? {
        val raiz = rootInActiveWindow ?: return null
        val partes = ArrayList<String>()
        coletar(raiz, partes, 0)
        return partes.joinToString(" | ").take(2000).ifBlank { null }
    }

    /** Toca no item cujo texto contém [alvo]. Devolve true se tocou. */
    fun tocar(alvo: String): Boolean {
        val raiz = rootInActiveWindow ?: return false
        val procurado = AbrirApp.normalizar(alvo)
        if (procurado.isEmpty()) return false
        val no = acharPorTexto(raiz, procurado, 0) ?: return false
        var atual: AccessibilityNodeInfo? = no
        while (atual != null) {
            if (atual.isClickable) return atual.performAction(AccessibilityNodeInfo.ACTION_CLICK)
            atual = atual.parent
        }
        return false
    }

    private fun acharEditavel(no: AccessibilityNodeInfo, prof: Int): AccessibilityNodeInfo? {
        if (prof > 30) return null
        if (no.isEditable && no.isVisibleToUser) return no
        for (i in 0 until no.childCount) {
            val filho = no.getChild(i) ?: continue
            acharEditavel(filho, prof + 1)?.let { return it }
        }
        return null
    }

    private fun coletar(no: AccessibilityNodeInfo, saida: MutableList<String>, prof: Int) {
        if (prof > 30 || saida.size > 300) return
        val t = (no.text ?: no.contentDescription)?.toString()?.trim()
        if (!t.isNullOrEmpty() && no.isVisibleToUser) saida.add(t)
        for (i in 0 until no.childCount) {
            no.getChild(i)?.let { coletar(it, saida, prof + 1) }
        }
    }

    private fun acharPorTexto(no: AccessibilityNodeInfo, procurado: String, prof: Int): AccessibilityNodeInfo? {
        if (prof > 30) return null
        val t = (no.text ?: no.contentDescription)?.toString()
        if (t != null && no.isVisibleToUser && AbrirApp.normalizar(t).contains(procurado)) return no
        for (i in 0 until no.childCount) {
            val filho = no.getChild(i) ?: continue
            acharPorTexto(filho, procurado, prof + 1)?.let { return it }
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
