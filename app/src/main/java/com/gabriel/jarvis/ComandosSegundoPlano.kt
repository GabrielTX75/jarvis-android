package com.gabriel.jarvis

import android.content.Context
import android.content.Intent
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.util.Locale

/** Abre um app instalado pelo nome (falado ou digitado). Usado pela tela e pelo núcleo em segundo plano. */
object AbrirApp {
    class Resultado(val ok: Boolean, val mensagem: String, val pacote: String?)

    fun normalizar(s: String): String =
        java.text.Normalizer.normalize(s, java.text.Normalizer.Form.NFD)
            .replace(Regex("\\p{M}+"), "")
            .lowercase(Locale.ROOT)
            .trim()
            // Vosk costuma transcrever o número "3" como "tres" ou "dois".
            .replace(Regex("\\btres\\b"), "3")
            .replace(Regex("\\bdois\\b"), "2")

    fun abrir(context: Context, consulta: String): Resultado {
        val procurado = normalizar(consulta)
        val pm = context.packageManager
        val apps = pm.queryIntentActivities(
            Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER), 0
        ).map { Pair(normalizar(it.loadLabel(pm).toString()), it.activityInfo.packageName) }
        val achado = apps.firstOrNull { it.first == procurado }
            ?: apps.firstOrNull { procurado.isNotEmpty() && it.first.contains(procurado) }
            ?: return Resultado(false, "Não encontrei nenhum aplicativo chamado $consulta.", null)
        val launch = pm.getLaunchIntentForPackage(achado.second)
            ?: return Resultado(false, "Esse aplicativo não pode ser aberto.", null)
        return try {
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(launch)
            Resultado(true, achado.first + " aberto.", achado.second)
        } catch (e: Exception) {
            Resultado(false, "O Android não conseguiu abrir esse aplicativo.", null)
        }
    }
}

/** Pesquisa na web pelo servidor próprio (Cloudflare Worker). A chave fica no cofre criptografado. */
object Pesquisa {
    /** Devolve um texto curto, pronto para ser falado. */
    fun buscar(context: Context, termo: String): String {
        val base = Cofre.ler(context, "busca_url").trim().trimEnd('/')
        val token = Cofre.ler(context, "busca_token").trim()
        if (!base.startsWith("https://") || token.isEmpty()) {
            return "Configure o servidor e a senha da busca nas configurações."
        }
        return try {
            val url = URL(base + "/busca?q=" + URLEncoder.encode(termo.take(200), "UTF-8"))
            val conn = (url.openConnection() as HttpURLConnection).apply {
                connectTimeout = 15_000
                readTimeout = 25_000
                setRequestProperty("X-Jarvis-Token", token)
            }
            if (conn.responseCode !in 200..299) return "A busca recusou o pedido."
            val corpo = conn.inputStream.bufferedReader().use { it.readText() }
            val lista: JSONArray = JSONObject(corpo).optJSONArray("resultados") ?: JSONArray()
            if (lista.length() == 0) return "Não encontrei resultados para isso."
            val partes = (0 until minOf(3, lista.length())).map { i ->
                val r = lista.getJSONObject(i)
                r.optString("titulo").take(120) + ". " + r.optString("trecho").take(160)
            }
            "Encontrei estes resultados. " + partes.joinToString(" ")
        } catch (e: Exception) {
            "Não consegui falar com o servidor de busca agora."
        }
    }
}

/** Código para colocar no Pydroid 3. "Olá, mundo" sai pronto; o resto vem da IA configurada. */
object Codigo {
    const val OLA_MUNDO = "print(\"Olá, mundo!\")\n"

    val promptSistema =
        "Você escreve código para o aplicativo Pydroid 3 (Python rodando no Android). " +
        "Responda APENAS com o código, sem explicações, sem markdown e sem crases. " +
        "Use Python, a não ser que o pedido diga outra linguagem. " +
        "O código deve ser completo, legível e com comentários curtos em português."

    /** Remove cercas de markdown que alguns modelos colocam mesmo quando não devem. */
    fun limpar(texto: String): String =
        texto.replace(Regex("```[a-zA-Z0-9+#]*\\n?"), "").trim().take(6000)
}
