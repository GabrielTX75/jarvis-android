package com.gabriel.jarvis

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.AlarmClock
import android.provider.MediaStore
import org.json.JSONArray
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

/** Ferramentas locais, sem chave e sem servidor: calculadora, anotações, lembretes e música. */
object Ferramentas {
    private const val ANOTACOES = "jarvis_anotacoes"
    private const val LISTA = "lista"

    /** Calcula uma expressão falada: "2 mais 2", "25 por cento de 80", "raiz de 16", "(3 + 4) vezes 2". */
    fun calcular(expressao: String): String {
        val valor = try {
            Calculadora(normalizarExpressao(expressao)).resolver()
        } catch (e: Exception) {
            null
        }
        if (valor == null || valor.isNaN() || valor.isInfinite()) return "Não consegui calcular isso."
        return "O resultado é " + formatarNumero(valor) + "."
    }

    private fun normalizarExpressao(texto: String): String {
        var s = texto.lowercase(Locale.ROOT)
        s = s.replace(Regex("raiz (quadrada )?de (\\d+(?:[.,]\\d+)?)")) {
            "sqrt(" + it.groupValues[2].replace(',', '.') + ")"
        }
        s = s.replace(Regex("(\\d+(?:[.,]\\d+)?) ?(?:%|por cento) ?de (\\d+(?:[.,]\\d+)?)")) {
            "(" + it.groupValues[1].replace(',', '.') + "/100*" + it.groupValues[2].replace(',', '.') + ")"
        }
        s = s.replace(" elevado a ", "^")
            .replace(" dividido por ", "/")
            .replace(" vezes ", "*")
            .replace(" mais ", "+")
            .replace(" menos ", "-")
            .replace(" x ", "*")
        s = s.replace(Regex("(\\d),(\\d)")) { it.groupValues[1] + "." + it.groupValues[2] }
        return s.replace(" ", "")
    }

    private fun formatarNumero(v: Double): String =
        if (v == Math.floor(v) && Math.abs(v) < 1e15) v.toLong().toString()
        else String.format(Locale("pt", "BR"), "%.2f", v)

    /** Analisador de expressões com precedência correta: ^ antes de * e /, e depois de + e -. */
    private class Calculadora(private val s: String) {
        private var i = 0

        fun resolver(): Double {
            val v = expr()
            if (i != s.length) throw IllegalArgumentException("sobrou texto")
            return v
        }

        private fun expr(): Double {
            var v = termo()
            while (i < s.length && (s[i] == '+' || s[i] == '-')) {
                val op = s[i++]
                val r = termo()
                v = if (op == '+') v + r else v - r
            }
            return v
        }

        private fun termo(): Double {
            var v = fator()
            while (i < s.length && (s[i] == '*' || s[i] == '/')) {
                val op = s[i++]
                val r = fator()
                v = if (op == '*') v * r else v / r
            }
            return v
        }

        private fun fator(): Double {
            val base = unario()
            if (i < s.length && s[i] == '^') {
                i++
                return Math.pow(base, fator())
            }
            return base
        }

        private fun unario(): Double {
            if (i < s.length && s[i] == '-') {
                i++
                return -unario()
            }
            return primario()
        }

        private fun primario(): Double {
            if (s.startsWith("sqrt(", i)) {
                i += 5
                val v = expr()
                consumir(')')
                return Math.sqrt(v)
            }
            if (i < s.length && s[i] == '(') {
                i++
                val v = expr()
                consumir(')')
                return v
            }
            val inicio = i
            while (i < s.length && (s[i].isDigit() || s[i] == '.')) i++
            if (inicio == i) throw IllegalArgumentException("número esperado")
            return s.substring(inicio, i).toDouble()
        }

        private fun consumir(c: Char) {
            if (i < s.length && s[i] == c) i++ else throw IllegalArgumentException("faltou " + c)
        }
    }

    fun anotar(ctx: Context, texto: String): String {
        val limpo = texto.trim().take(300)
        if (limpo.isEmpty()) return "O que o senhor quer anotar?"
        val data = SimpleDateFormat("dd/MM HH:mm", Locale("pt", "BR")).format(Date())
        salvarLista(ctx, (lerLista(ctx) + (data + " - " + limpo)).takeLast(100))
        return "Anotado, senhor."
    }

    fun lerAnotacoes(ctx: Context): String {
        val lista = lerLista(ctx)
        if (lista.isEmpty()) return "Não há anotações."
        return "Suas últimas anotações: " + lista.takeLast(5).joinToString(". ")
    }

    fun apagarAnotacoes(ctx: Context): String {
        prefs(ctx).edit().remove(LISTA).apply()
        return "Apaguei as anotações."
    }

    /** Marca um alarme no relógio do aparelho, com a mensagem do lembrete. */
    fun lembrete(ctx: Context, minutos: Int, texto: String): String {
        if (minutos <= 0 || minutos > 1440) return "Diga daqui a quantos minutos devo lembrar."
        val quando = Calendar.getInstance().apply { add(Calendar.MINUTE, minutos) }
        val mensagem = texto.trim().take(60).ifEmpty { "Lembrete do JARVIS" }
        val i = Intent(AlarmClock.ACTION_SET_ALARM)
            .putExtra(AlarmClock.EXTRA_HOUR, quando.get(Calendar.HOUR_OF_DAY))
            .putExtra(AlarmClock.EXTRA_MINUTES, quando.get(Calendar.MINUTE))
            .putExtra(AlarmClock.EXTRA_MESSAGE, mensagem)
            .putExtra(AlarmClock.EXTRA_SKIP_UI, true)
        val hora = SimpleDateFormat("HH:mm", Locale.ROOT).format(quando.time)
        return abrirIntent(ctx, i, "Lembrete marcado para " + hora + ": " + mensagem + ".")
    }

    /** Pede ao player de música do aparelho para buscar e tocar o termo. Sem player, abre a busca no YouTube. */
    fun tocarMusica(ctx: Context, termo: String): String {
        val alvo = termo.trim().take(120)
        if (alvo.isEmpty()) return "Qual música o senhor quer ouvir?"
        val midia = Intent(MediaStore.INTENT_ACTION_MEDIA_PLAY_FROM_SEARCH)
            .putExtra(MediaStore.EXTRA_MEDIA_FOCUS, "vnd.android.cursor.item/*")
            .putExtra(MediaStore.EXTRA_MEDIA_TITLE, alvo)
            .putExtra("query", alvo)
        return try {
            midia.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            ctx.startActivity(midia)
            "Pedi para tocar " + alvo + " no seu player de música."
        } catch (e: Exception) {
            val busca = Intent(Intent.ACTION_VIEW, Uri.parse("https://www.youtube.com/results?search_query=" + Uri.encode(alvo)))
            abrirIntent(ctx, busca, "Não achei um player de música. Abri a busca de " + alvo + " no navegador.")
        }
    }

    private fun abrirIntent(ctx: Context, i: Intent, sucesso: String): String = try {
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        ctx.startActivity(i)
        sucesso
    } catch (e: Exception) {
        "Não encontrei um aplicativo para isso."
    }

    private fun prefs(ctx: Context) = ctx.getSharedPreferences(ANOTACOES, Context.MODE_PRIVATE)

    private fun lerLista(ctx: Context): List<String> = try {
        val arr = JSONArray(prefs(ctx).getString(LISTA, "[]") ?: "[]")
        (0 until arr.length()).map { arr.getString(it) }
    } catch (e: Exception) {
        emptyList()
    }

    private fun salvarLista(ctx: Context, lista: List<String>) {
        prefs(ctx).edit().putString(LISTA, JSONArray(lista).toString()).apply()
    }
}
