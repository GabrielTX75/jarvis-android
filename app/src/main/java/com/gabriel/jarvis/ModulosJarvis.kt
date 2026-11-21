package com.gabriel.jarvis

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/** Recursos de projeto e segurança do APK. Atua somente na pasta privada do JARVIS. */
object ModulosJarvis {
    private const val MAX_FILE_BYTES = 1_000_000L
    private const val MAX_TOTAL_BYTES = 5_000_000L

    private fun root(ctx: Context): File {
        val base = ctx.getExternalFilesDir(null) ?: ctx.filesDir
        return File(base, "JARVIS/Projects").apply { mkdirs() }.canonicalFile
    }

    private fun safeName(raw: String): String {
        val name = raw.trim()
        require(name.matches(Regex("[A-Za-z0-9 _.-]{1,60}")) && name != "." && name != "..") {
            "Nome inválido. Use até 60 letras, números, espaços, ponto, hífen ou sublinhado."
        }
        return name
    }

    fun createProject(ctx: Context, rawName: String, filesJson: String): String = try {
        val name = safeName(rawName)
        val base = root(ctx)
        val dir = File(base, name).canonicalFile
        require(dir.parentFile == base) { "Caminho de projeto inválido." }
        val files = JSONArray(filesJson)
        require(files.length() in 1..80) { "Envie de 1 a 80 arquivos." }
        var total = 0L
        val written = mutableListOf<String>()
        for (i in 0 until files.length()) {
            val item = files.getJSONObject(i)
            val relative = item.optString("path").replace('\\\\', '/')
            require(relative.isNotBlank() && !relative.startsWith("/") &&
                relative.split('/').none { it.isBlank() || it == "." || it == ".." }) {
                "Caminho de arquivo inválido: $relative"
            }
            val target = File(dir, relative).canonicalFile
            require(target.path.startsWith(dir.path + File.separator)) { "Arquivo fora da pasta do projeto." }
            val bytes = item.optString("content").toByteArray(Charsets.UTF_8)
            require(bytes.size <= MAX_FILE_BYTES) { "Arquivo muito grande: $relative" }
            total += bytes.size
            require(total <= MAX_TOTAL_BYTES) { "Projeto excede o limite de 5 MB." }
            target.parentFile?.mkdirs()
            target.writeBytes(bytes)
            written.add(relative)
        }
        JSONObject().put("ok", true).put("project", name)
            .put("path", dir.absolutePath).put("files", JSONArray(written))
            .put("message", "Projeto criado com ${written.size} arquivo(s). Nenhum código foi executado.")
            .toString()
    } catch (e: Exception) {
        JSONObject().put("ok", false).put("message", e.message ?: "Não foi possível criar o projeto.").toString()
    }

    fun auditProject(ctx: Context, rawName: String): String = try {
        val name = safeName(rawName)
        val base = root(ctx)
        val dir = File(base, name).canonicalFile
        require(dir.path.startsWith(base.path + File.separator) && dir.isDirectory) {
            "Projeto não encontrado na pasta privada do JARVIS."
        }
        val patterns = listOf(
            Regex("(?i)\\beval\\s*\\(") to "Uso de eval: revise entrada não confiável.",
            Regex("(?i)\\b(exec|system|popen)\\s*\\(") to "Execução de comandos/processos: revise o contexto.",
            Regex("(?i)(api[_-]?key|secret|password|token)\\s*[:=]\\s*['\"][^'\"]{8,}['\"]") to "Possível segredo fixo no código.",
            Regex("(?i)0\\.0\\.0\\.0|Access-Control-Allow-Origin.{0,12}\\*") to "Configuração de exposição ampla: revise necessidade.",
            Regex("(?i)verify\\s*=\\s*false|CERT_NONE") to "Verificação TLS desativada: revise a segurança."
        )
        val findings = JSONArray()
        var scanned = 0
        var bytes = 0L
        dir.walkTopDown().filter { it.isFile && !it.isSymbolicLink() }.forEach { file ->
            if (scanned >= 500 || bytes >= 10_000_000L || file.length() > 1_000_000L) return@forEach
            if (file.extension.lowercase() !in setOf("py","js","ts","tsx","jsx","html","kt","java","php","json","xml","yml","yaml","env","txt","sql","sh")) return@forEach
            val source = runCatching { file.readText(Charsets.UTF_8) }.getOrNull() ?: return@forEach
            scanned++; bytes += file.length()
            patterns.forEach { (regex, message) ->
                if (regex.containsMatchIn(source)) findings.put(JSONObject()
                    .put("file", file.relativeTo(dir).path).put("finding", message))
            }
        }
        JSONObject().put("ok", true).put("project", name).put("files_scanned", scanned)
            .put("findings", findings)
            .put("notice", "Auditoria estática preliminar: achados precisam de revisão manual e não comprovam vulnerabilidade.")
            .toString()
    } catch (e: Exception) {
        JSONObject().put("ok", false).put("message", e.message ?: "Falha na auditoria.").toString()
    }

    fun projects(ctx: Context): String = JSONArray().apply {
        root(ctx).listFiles()?.filter { it.isDirectory && !it.isSymbolicLink() }?.sortedBy { it.name }
            ?.forEach { put(it.name) }
    }.toString()

    private fun File.isSymbolicLink(): Boolean =
        runCatching { canonicalFile != absoluteFile }.getOrDefault(true)
}
