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
 *
 * A porcentagem só existe quando o pedido tem uma meta de linhas ("faz com 3 mil linhas").
 * Sem meta, o gerador mostra o total de linhas e para quando o modelo termina.
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
        if (p.getString("pedido", null) == null) return "Não há código sendo gerado."
        val linhas = p.getInt("linhas", 0)
        val alvo = p.getInt("alvo", 0)
        val estado = when {
            rodando -> "sendo gerado"
            p.getString("estado", "") == "gerando" -> "interrompido. Diga continua o código para retomar"
            else -> p.getString("estado", "") ?: ""
        }
        val meta = if (alvo > 0) " de " + alvo + " linhas, " + (linhas * 100 / alvo).coerceAtMost(100) + " por cento" else ""
        return "O código tem " + linhas + " linhas" + meta + ", e está " + estado + "."
    }

    /** Começa um código novo ([pedido] não nulo) ou retoma o último ([pedido] nulo). Devolve a frase para falar. */
    fun iniciar(ctx: Context, pedido: String?): String {
        if (rodando) return "Já estou gerando o código. Diga como está o código para ver o andamento."
        val p = prefs(ctx)
        val cfg = ctx.getSharedPreferences("jarvis_wpp", Context.MODE_PRIVATE)
        val endpoint = cfg.getString("endpoint", "") ?: ""
        if (!(endpoint.startsWith("http://") || endpoint.startsWith("https://"))) {
            return "Configure o endereço da IA nas configurações."
        }
        val modelo = cfg.getString("model", "") ?: ""
        val textoPedido: String
        val arq: File
        if (pedido != null) {
            textoPedido = pedido
            arq = Organizador.novoArquivoCodigo()
                ?: return "Ative o acesso a todos os arquivos do JARVIS para eu salvar o código."
            p.edit()
                .putString("pedido", pedido)
                .putString("arquivo", arq.absolutePath)
                .putInt("partes", 0)
                .putInt("linhas", 0)
                .putInt("alvo", alvoDoPedido(pedido))
                .apply()
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

    /** Lista os códigos guardados em Downloads/JARVIS, com linhas, porcentagem e se estão prontos. */
    fun listar(ctx: Context): JSONArray {
        val p = prefs(ctx)
        val atual = p.getString("arquivo", null)
        val alvoAtual = p.getInt("alvo", 0)
        val concluido = p.getString("estado", "") == "concluido" && !rodando
        val arr = JSONArray()
        val arquivos = Organizador.pastaCodigos()
            .listFiles { f -> f.isFile && f.name.endsWith(".py") }
            ?.sortedByDescending { it.lastModified() }
            ?: emptyList()
        for (f in arquivos) {
            val ehAtual = f.absolutePath == atual
            val linhas = try { f.readText().count { it == '\n' } } catch (e: Exception) { 0 }
            val alvo = if (ehAtual) alvoAtual else 0
            val pronto = if (ehAtual) concluido else true
            val pct = when {
                alvo > 0 -> (linhas * 100 / alvo).coerceAtMost(100)
                pronto -> 100
                else -> -1
            }
            arr.put(
                JSONObject()
                    .put("nome", f.name)
                    .put("caminho", f.absolutePath)
                    .put("linhas", linhas)
                    .put("percentual", pct)
                    .put("pronto", pronto && pct >= 100)
            )
        }
        return arr
    }

    /** Meta de linhas no pedido, como "3 mil linhas" ou "500 linhas". 0 se não tiver meta. */
    private fun alvoDoPedido(pedido: String): Int {
        val m = Regex("(\\d[\\d.]*)\\s*(mil\\s+)?linhas").find(pedido.lowercase()) ?: return 0
        val n = m.groupValues[1].replace(".", "").toLongOrNull() ?: return 0
        val total = if (m.groupValues[2].isNotEmpty()) n * 1000 else n
        return total.coerceAtMost(1_000_000L).toInt()
    }

    private fun gerar(ctx: Context, endpoint: String, modelo: String, chave: String, pedido: String, arq: File) {
        val p = prefs(ctx)
        val inicio = System.currentTimeMillis()
        val alvo = p.getInt("alvo", 0)
        var partes = p.getInt("partes", 0)
        var linhas = p.getInt("linhas", 0)
        var cauda = try { arq.readText().takeLast(3000) } catch (e: Exception) { "" }
        var estado = "concluido"
        var vazias = 0
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
                    val falta = if (alvo > 0) " Ainda faltam " + (alvo - linhas).coerceAtLeast(0) + " linhas." else ""
                    msgs.put(JSONObject().put("role", "user").put("content", "Continue exatamente depois do trecho acima, sem repetir e sem explicar nada." + falta))
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
                val (texto, _) = resposta
                val bruto = Codigo.limparParte(texto)
                val terminou = bruto.contains("FIM_DO_CODIGO")
                val parte = bruto.replace("FIM_DO_CODIGO", "")
                if (parte.isBlank()) {
                    vazias++
                    if (vazias >= 3) break
                    continue
                }
                vazias = 0
                arq.appendText(parte)
                partes++
                linhas += parte.count { it == '\n' }
                cauda = (cauda + parte).takeLast(3000)
                p.edit().putInt("partes", partes).putInt("linhas", linhas).apply()
                if (alvo > 0 && linhas >= alvo) break
                if (alvo <= 0 && terminou) break
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
