package com.gabriel.jarvis

import android.content.Context
import android.os.Build
import android.os.Environment
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Organiza os arquivos soltos da pasta Downloads em categorias.
 * Nunca apaga nada: só move. O registro da última organização fica salvo para "desfazer".
 * Depende do acesso a todos os arquivos, que o JARVIS já pede nas configurações.
 */
object Organizador {
    private const val PREFS = "jarvis_organizacao"
    private const val CHAVE = "movimentos"

    private val categorias = linkedMapOf(
        "Imagens" to setOf("jpg", "jpeg", "png", "gif", "webp", "heic", "bmp"),
        "Videos" to setOf("mp4", "mkv", "mov", "avi", "3gp", "webm"),
        "Audios" to setOf("mp3", "wav", "ogg", "m4a", "opus", "aac", "flac"),
        "Documentos" to setOf("pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "csv", "odt", "rtf"),
        "Apks" to setOf("apk"),
        "Compactados" to setOf("zip", "rar", "7z", "tar", "gz")
    )

    private const val SEM_ACESSO =
        "Ative o acesso a todos os arquivos do JARVIS nas configurações para eu organizar os Downloads."

    fun temAcesso(): Boolean = Build.VERSION.SDK_INT < 30 || Environment.isExternalStorageManager()

    private fun pastaDownloads(): File =
        Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)

    /** Move os arquivos soltos de Downloads para pastas por tipo e guarda o registro para desfazer. */
    fun organizar(ctx: Context): String {
        if (!temAcesso()) return SEM_ACESSO
        val pasta = pastaDownloads()
        val arquivos = pasta.listFiles { f -> f.isFile } ?: return "Não consegui ler a pasta Downloads."
        val movimentos = JSONArray()
        val pastasUsadas = HashSet<String>()
        for (f in arquivos) {
            val ext = f.extension.lowercase(Locale.ROOT)
            val categoria = categorias.entries.firstOrNull { ext in it.value }?.key ?: "Outros"
            val dir = File(pasta, categoria).apply { mkdirs() }
            val destino = destinoSemRepetir(dir, f.name)
            if (f.renameTo(destino)) {
                movimentos.put(JSONObject().put("de", f.absolutePath).put("para", destino.absolutePath))
                pastasUsadas.add(categoria)
            }
        }
        if (movimentos.length() == 0) return "Não encontrei arquivos soltos nos Downloads."
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(CHAVE, movimentos.toString()).apply()
        return "Organizei " + movimentos.length() + " arquivos em " + pastasUsadas.size +
            " pastas. Diga desfazer organização para voltar tudo como estava."
    }

    /** Devolve os arquivos ao lugar original, na ordem inversa, sem sobrescrever nada. */
    fun desfazer(ctx: Context): String {
        if (!temAcesso()) return SEM_ACESSO
        val prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val texto = prefs.getString(CHAVE, null) ?: return "Não há organização para desfazer."
        val lista = try { JSONArray(texto) } catch (e: Exception) { return "O registro da organização está corrompido." }
        var voltaram = 0
        for (i in lista.length() - 1 downTo 0) {
            val m = lista.getJSONObject(i)
            val para = File(m.getString("para"))
            val de = File(m.getString("de"))
            if (para.exists() && !de.exists() && para.renameTo(de)) voltaram++
        }
        prefs.edit().remove(CHAVE).apply()
        return "Desfiz a organização. $voltaram arquivos voltaram para os Downloads."
    }

    /** Guarda uma cópia do código gerado em Downloads/JARVIS. Devolve true se salvou. */
    fun salvarCodigo(codigo: String): Boolean {
        if (!temAcesso()) return false
        return try {
            val dir = File(pastaDownloads(), "JARVIS").apply { mkdirs() }
            val nome = "codigo_" + SimpleDateFormat("yyyyMMdd_HHmmss", Locale.ROOT).format(Date()) + ".py"
            File(dir, nome).writeText(codigo)
            true
        } catch (e: Exception) {
            false
        }
    }

    /** Pasta onde ficam os códigos gerados. */
    fun pastaCodigos(): File = File(pastaDownloads(), "JARVIS")

    /** Cria o arquivo vazio onde o código longo vai sendo gravado. Null se não houver acesso. */
    fun novoArquivoCodigo(): File? {
        if (!temAcesso()) return null
        return try {
            val dir = File(pastaDownloads(), "JARVIS").apply { mkdirs() }
            val nome = "codigo_" + SimpleDateFormat("yyyyMMdd_HHmmss", Locale.ROOT).format(Date()) + ".py"
            val arq = destinoSemRepetir(dir, nome)
            arq.createNewFile()
            arq
        } catch (e: Exception) {
            null
        }
    }

    private fun destinoSemRepetir(dir: File, nome: String): File {
        var alvo = File(dir, nome)
        val base = nome.substringBeforeLast('.', nome)
        val ext = if (nome.contains('.')) "." + nome.substringAfterLast('.') else ""
        var i = 1
        while (alvo.exists()) {
            alvo = File(dir, base + " (" + i + ")" + ext)
            i++
        }
        return alvo
    }
}
