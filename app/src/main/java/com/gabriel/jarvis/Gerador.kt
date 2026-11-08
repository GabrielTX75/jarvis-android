package com.gabriel.jarvis

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/**
 * Gera código longo em segundo plano. Cada parte é gravada no arquivo assim que chega,
 * então o que já foi escrito não se perde se o app for fechado. Dá para retomar depois.
 */
object GeradorCodigo {
    private const val PREFS = "jarvis_codigo"

    @Volatile private var rodando = false
    @Volatile private var pararPedido = false

    fun emAndamento(): Boolean = rodando

    fun parar() {
        pararPedido = true
    }

    fun textoAtual(ctx: Context): String = try {
        prefs(ctx).getString("arquivo", null)?.let { File(it).readText() } ?: ""
    } catch (e: Exception) {
        ""
    }

    /** Frase com o andamento, para falar. */
    fun status(ctx: Context): String {
        val p = prefs(ctx)
        val partes = p.getInt("partes", 0)
        if (p.getString("pedido", null) == null) return "Não há código sendo gerado."
        val estado = when {
            rodando -> "ainda sendo gerado"
            p.getString("estado", "") == "gerando" -> "interrompido. Diga continua o código para retomar"
            else -> p.getString("estado", "") ?: ""
        }
        return "O código tem $partes partes escritas e está $estado."
    }

    /** Começa um código novo ([pedido] não nulo) ou retoma o último ([pedido] nulo). Devolve a frase para falar. */
    fun iniciar(ctx: Context, pedido: String?): String {
        if (rodando) return "Já estou gerando o código. Diga como está o código para ver o andamento."
        val p = prefs(ctx)
        val endpoint = ctx.getSharedPreferences("jarvis_wpp", Context.MODE_PRIVATE).getString("endpoint", "") ?: ""
        if (!(endpoint.startsWith("http://") || endpoint.startsWith("https://"))) {
            return "Configure o endereço da IA nas configurações."
        }
        val modelo = ctx.getSharedPreferences("jarvis_wpp", Context.MODE_PRIVATE).getString("model", "") ?: ""
        val textoPedido: String
        val arq: File
        if (pedido != null) {
            textoPedido = pedido
            arq = Organizador.novoArquivoCodigo()
                ?: return "Ative o acesso a todos os arquivos do JARVIS para eu salvar o código."
            p.edit().putString("pedido", pedido).putString("arquivo", arq.absolutePath).putInt("partes", 0).apply()
        } else {
            textoPedido = p.getString("pedido", null) ?: return "Não há código para continuar."
            val caminho = p.getString("arquivo", null) ?: return "Não encontrei o arquivo do código anterior."
            arq = File(caminho)
            if (!arq.exists()) return "Não encontrei o arquivo do código anterior."
        }
        p.edit().putString("estado", "gerando").apply()
        pararPedido = false
        rodando = true
        val chave = Cofre.ler(ctx, "ai_key")
        Thread { gerar(ctx, endpoint, modelo, chave, textoPedido, arq) }.start()
        return "Comecei a gerar o código."
    }

    private fun gerar(ctx: Context, endpoint: String, modelo: String, chave: String, pedido: String, arq: File) {
        val p = prefs(ctx)
        val inicio = System.currentTimeMillis()
        var partes = p.getInt("partes", 0)
        var cauda = try { arq.readText().takeLast(3000) } catch (e: Exception) { "" }
        var estado = "concluido"
        try {
            while (true) {
                if (pararPedido) {
                    estado = "parado"
                    break
                }
                if (System.currentTimeMillis() - inicio > Codigo.TEMPO_MAXIMO_MS) {
                    estado = "com o tempo esgotado"
                    break
                }
                if (partes >= Codigo.MAX_PARTES) {
                    estado = "no limite de partes"
                    break
                }
                val msgs = JSONArray()
                    .put(JSONObject().put("role", "system").put("content", Codigo.promptSistema))
                    .put(JSONObject().put("role", "user").put("content", pedido))
                if (cauda.isNotEmpty()) {
                    // Manda só o fim do que já foi escrito, para não estourar o contexto do modelo.
                    msgs.put(JSONObject().put("role", "assistant").put("content", cauda))
                    msgs.put(JSONObject().put("role", "user").put("content", "Continue exatamente depois do trecho acima, sem repetir e sem explicar nada."))
                }
                val corpo = JSONObject()
                    .put("model", modelo)
                    .put("stream", false)
                    .put("max_tokens", Codigo.TOKENS_POR_PARTE)
                    .put("messages", msgs)
                val resposta = chamar(endpoint, chave, corpo)
                if (resposta == null) {
                    estado = "parado por erro na IA"
                    break
                }
                val (texto, motivo) = resposta
                if (texto.isEmpty()) break
                arq.appendText(Codigo.limparParte(texto))
                partes++
                cauda = (cauda + texto).takeLast(3000)
                p.edit().putInt("partes", partes).apply()
                if (motivo != "length") break
            }
        } catch (e: Exception) {
            estado = "parado por erro"
        } finally {
            p.edit().putString("estado", estado).apply()
            rodando = false
        }
    }

    /** Chamada à IA que devolve o texto e o motivo de parada ("stop" ou "length"). */
    private fun chamar(endpoint: String, chave: String, corpo: JSONObject): Pair<String, String>? {
        return try {
            val conn = (URL(endpoint).openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = 15_000
                readTimeout = 180_000
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
                if (chave.isNotEmpty()) setRequestProperty("Authorization", "Bearer $chave")
            }
            conn.outputStream.use { it.write(corpo.toString().toByteArray(Charsets.UTF_8)) }
            if (conn.responseCode !in 200..299) return null
            val resp = JSONObject(conn.inputStream.bufferedReader().use { it.readText() })
            val escolha = resp.getJSONArray("choices").getJSONObject(0)
            Pair(escolha.getJSONObject("message").getString("content"), escolha.optString("finish_reason", "stop"))
        } catch (e: Exception) {
            null
        }
    }

    private fun prefs(ctx: Context) = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
}
