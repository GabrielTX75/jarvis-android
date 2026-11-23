package com.gabriel.jarvis

import android.Manifest
import android.media.AudioAttributes
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.webkit.CookieManager
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import android.net.Uri
import android.provider.Settings
import android.os.Environment
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.IOException
import java.net.HttpURLConnection
import java.net.SocketTimeoutException
import java.net.URL
import java.net.URI
import java.util.concurrent.CompletableFuture
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import org.json.JSONArray
import org.json.JSONObject
import androidx.core.content.ContextCompat
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import androidx.webkit.WebViewAssetLoader
import java.util.Locale

class MainActivity : Activity(), RecognitionListener, TextToSpeech.OnInitListener {
    private var pendingWake = false
    private lateinit var webView: WebView
    private lateinit var assetLoader: WebViewAssetLoader
    private var recognizer: SpeechRecognizer? = null
    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private var ttsInitDone = false
    private var ttsFailure: String? = null
    private var pendingSpeak: (() -> Unit)? = null
    private var pendingPermissionStart = false
    private var listening = false
    private var lastUtteranceId = ""
    private var aiConfigPromptOpen = false
    @Volatile private var callbacksEnabled = true

    private class AiRequest {
        val cancelled = AtomicBoolean(false)
        @Volatile var connection: HttpURLConnection? = null
    }

    private val aiExecutor = Executors.newFixedThreadPool(2)
    private val aiRequests = ConcurrentHashMap<String, AiRequest>()

    companion object {
        private const val REQ_AUDIO = 4102
        private const val REQ_NOTIF = 4103
        private const val APP_HOST = "appassets.androidplatform.net"
        private const val APP_URL = "https://appassets.androidplatform.net/assets/index.html"
        private val SECRET_NAMES = setOf("busca_url", "busca_token", "ai_key", "pin_hash", "picovoice_key")
    }

    private val secretPrefs by lazy {
        val masterKey = MasterKey.Builder(this).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build()
        EncryptedSharedPreferences.create(
            this, "jarvis_segredos", masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        pendingWake = intent?.getBooleanExtra("wake", false) == true
        iniciarOuvirSeAtivo()
        window.statusBarColor = android.graphics.Color.rgb(10, 6, 4)
        window.navigationBarColor = android.graphics.Color.rgb(10, 6, 4)
        tts = TextToSpeech(this, this)
        assetLoader = WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()

        webView = WebView(this)
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = false
            allowContentAccess = false
            allowFileAccessFromFileURLs = false
            allowUniversalAccessFromFileURLs = false
            mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
            javaScriptCanOpenWindowsAutomatically = false
            setSupportMultipleWindows(false)
            safeBrowsingEnabled = true
        }
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, false)
        // The legacy bridge is retained for existing voice, screen, WhatsApp and code tools.
        // Navigation and resource loading are now confined to the bundled appassets origin.
        webView.addJavascriptInterface(NativeBridge(), "JarvisAndroid")
        webView.webViewClient = object : WebViewClient() {
            override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? {
                val uri = request.url
                if (uri.host?.equals(APP_HOST, ignoreCase = true) == true) {
                    if (!isTrustedAssetOrigin(uri)) return notFoundResponse()
                    return assetLoader.shouldInterceptRequest(uri) ?: notFoundResponse()
                }
                return null
            }

            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val uri = request.url
                if (isAppDocument(uri)) return false
                // No other document, including a different page on the privileged origin, may load here.
                if (isTrustedAssetOrigin(uri)) return true

                // Only external HTTPS links may leave the app; HTTP and custom schemes are blocked.
                if (uri.scheme == "https") {
                    return try {
                        startActivity(Intent(Intent.ACTION_VIEW, uri))
                        true
                    } catch (_: Exception) {
                        true
                    }
                }
                return true
            }
        }
        setContentView(webView)
        webView.loadUrl(APP_URL)
    }

    private fun isTrustedAssetOrigin(uri: Uri): Boolean =
        uri.scheme == "https" &&
            uri.host?.equals(APP_HOST, ignoreCase = true) == true &&
            uri.userInfo == null &&
            (uri.port == -1 || uri.port == 443)

    private fun isAppDocument(uri: Uri): Boolean =
        isTrustedAssetOrigin(uri) &&
            uri.path == "/assets/index.html" &&
            uri.query == null &&
            uri.fragment == null

    private fun notFoundResponse(): WebResourceResponse =
        WebResourceResponse(
            "text/plain",
            "UTF-8",
            404,
            "Not Found",
            emptyMap(),
            ByteArrayInputStream(ByteArray(0))
        )

    private data class ValidatedAiEndpoint(
        val normalized: String,
        val local: Boolean,
        val display: String
    )

    /**
     * Valida e normaliza o endpoint completo da IA.
     * A aprovação é vinculada à URL exata, não apenas ao host.
     * Query, fragmento e credenciais embutidas na URL são recusados.
     */
    private fun validateAiEndpoint(raw: String): ValidatedAiEndpoint? {
        if (raw.isBlank() || raw.length > 2048) return null
        val parsed = try { URI(raw.trim()).normalize() } catch (_: Exception) { return null }
        if (!parsed.isAbsolute || parsed.isOpaque ||
            parsed.rawUserInfo != null || parsed.rawQuery != null || parsed.rawFragment != null) {
            return null
        }

        val scheme = parsed.scheme?.lowercase(Locale.ROOT) ?: return null
        val host = parsed.host?.lowercase(Locale.ROOT) ?: return null
        val local = host == "localhost" || host == "127.0.0.1"
        if (!(scheme == "https" || (scheme == "http" && local))) return null
        if (parsed.port !in -1..65535 || parsed.port == 0) return null

        val path = parsed.rawPath?.takeIf { it.isNotEmpty() } ?: "/"
        if (!path.startsWith("/")) return null
        val authorityHost = if (host.contains(":") && !host.startsWith("[")) "[$host]" else host
        val defaultPort = if (scheme == "https") 443 else 80
        val portSuffix = if (parsed.port == -1 || parsed.port == defaultPort) "" else ":${parsed.port}"
        val normalized = "$scheme://$authorityHost$portSuffix$path"
        if (normalized.length > 2048) return null
        try { URL(normalized) } catch (_: Exception) { return null }

        return ValidatedAiEndpoint(normalized, local, "$authorityHost$portSuffix$path")
    }

    inner class NativeBridge {
        @JavascriptInterface fun startListening() { runOnUiThread { beginListening() } }
        @JavascriptInterface fun stopListening() { runOnUiThread { stopRecognition() } }
        @JavascriptInterface fun speak(text: String, id: String, rate: Float, pitch: Float) { runOnUiThread { speakNative(text, id, rate, pitch) } }
        @JavascriptInterface fun stopSpeaking() { runOnUiThread { tts?.stop() } }
        @JavascriptInterface fun platform(): String = "android-native"
        @JavascriptInterface fun openAppByName(query: String, requestId: String) {
            runOnUiThread {
                val r = AbrirApp.abrir(this@MainActivity, query)
                actionResult(requestId, r.ok, r.mensagem)
            }
        }
        @JavascriptInterface fun versao(): String = try {
            packageManager.getPackageInfo(packageName, 0).versionName ?: "desconhecida"
        } catch (e: Exception) {
            "desconhecida"
        }
        @JavascriptInterface fun codigos(): String = try {
            GeradorCodigo.listar(this@MainActivity).toString()
        } catch (e: Exception) {
            "[]"
        }
        /** Copia o código de um arquivo de Downloads/JARVIS para a área de transferência. */
        @JavascriptInterface fun copiarCodigo(caminho: String): Boolean = try {
            val arq = java.io.File(caminho).canonicalFile
            val pasta = Organizador.pastaCodigos().canonicalFile
            if (!arq.path.startsWith(pasta.path + java.io.File.separator)) {
                false
            } else {
                val cb = getSystemService(android.content.Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
                cb.setPrimaryClip(android.content.ClipData.newPlainText("JARVIS", arq.readText()))
                true
            }
        } catch (e: Exception) {
            false
        }
        @JavascriptInterface fun acessibilidadeLigada(): Boolean = JarvisAcessibilidade.ligada(this@MainActivity)
        @JavascriptInterface fun abrirAcessibilidade() {
            runOnUiThread {
                startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            }
        }
        @JavascriptInterface fun replyWhatsapp(key: String, text: String): Boolean =
            WhatsAppBridge.reply(this@MainActivity, key, text.take(600))
        @JavascriptInterface fun notificationAccessEnabled(): Boolean {
            val flat = Settings.Secure.getString(contentResolver, "enabled_notification_listeners") ?: return false
            return flat.contains(packageName)
        }
        @JavascriptInterface fun openNotificationAccess() {
            runOnUiThread {
                startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            }
        }
        @JavascriptInterface fun getSecret(name: String): String {
            // A chave da IA é lida apenas pelo transporte nativo; nunca retorna ao JavaScript.
            if (name !in SECRET_NAMES || name == "ai_key") return ""
            return try { secretPrefs.getString(name, "") ?: "" } catch (e: Exception) { "" }
        }
        @JavascriptInterface fun requestAI(messagesJson: String, requestId: String) {
            submitAiRequest(messagesJson, requestId)
        }
        @JavascriptInterface fun cancelAI(requestId: String) {
            cancelAiRequest(requestId)
        }
        @JavascriptInterface fun allFilesAccessEnabled(): Boolean =
            Build.VERSION.SDK_INT < 30 || Environment.isExternalStorageManager()
        @JavascriptInterface fun openAllFilesAccess() {
            runOnUiThread {
                val i = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, Uri.parse("package:$packageName"))
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                startActivity(i)
            }
        }
        @JavascriptInterface fun transcribeLatestVoiceNote(sinceMs: String, requestId: String) {
            val since = sinceMs.toLongOrNull() ?: (System.currentTimeMillis() - 90_000L)
            Thread {
                val result: Pair<Boolean, String> = try {
                    if (!(Build.VERSION.SDK_INT < 30 || Environment.isExternalStorageManager())) {
                        Pair(false, "Ative o acesso a todos os arquivos para o JARVIS ouvir áudios.")
                    } else {
                        val ready = CompletableFuture<Boolean>()
                        runOnUiThread { AudioTranscriber.ensureModel(this@MainActivity) { ready.complete(it) } }
                        if (!ready.get(60, TimeUnit.SECONDS)) {
                            Pair(false, "O modelo de voz não carregou.")
                        } else {
                            var file: File? = null
                            val deadline = System.currentTimeMillis() + 20_000L
                            while (file == null && System.currentTimeMillis() < deadline) {
                                file = AudioTranscriber.newestVoiceNote(since)
                                if (file == null) Thread.sleep(1000)
                            }
                            if (file == null) {
                                Pair(false, "Não achei o áudio no celular.")
                            } else {
                                Thread.sleep(1500)
                                Pair(true, AudioTranscriber.transcribe(file))
                            }
                        }
                    }
                } catch (e: Exception) {
                    Pair(false, "Não consegui ouvir o áudio.")
                }
                js("jarvisAudioTranscript", "${JSONObjectQuote(requestId)}, ${result.first}, ${JSONObjectQuote(result.second)}")
            }.start()
        }
        @JavascriptInterface fun salvarWpp(auto: Boolean, nome: String, endpoint: String, model: String) {
            runOnUiThread { configureWppAndAiEndpoint(auto, nome, endpoint, model) }
        }
        @JavascriptInterface fun picovoiceConfigurada(): Boolean = Cofre.ler(this@MainActivity, "picovoice_key").isNotEmpty()
        @JavascriptInterface fun ouvirSegundoPlanoAtivo(): Boolean = ouvirAtivo()
        @JavascriptInterface fun setOuvirSegundoPlano(on: Boolean): Boolean {
            getSharedPreferences("jarvis_ouvir", MODE_PRIVATE).edit().putBoolean("ativo", on).apply()
            runOnUiThread {
                if (on) {
                    if (Build.VERSION.SDK_INT >= 33 &&
                        checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                        requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), REQ_NOTIF)
                    }
                    if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                        requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), REQ_AUDIO)
                    }
                    iniciarOuvirSeAtivo()
                } else {
                    stopService(Intent(this@MainActivity, JarvisOuvidoService::class.java))
                }
            }
            return true
        }
        @JavascriptInterface fun overlayPermitida(): Boolean = Settings.canDrawOverlays(this@MainActivity)
        @JavascriptInterface fun abrirPermissaoOverlay() {
            runOnUiThread {
                startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName"))
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            }
        }
        @JavascriptInterface fun clearSecrets(): Boolean =
            try { secretPrefs.edit().clear().commit() } catch (e: Exception) { false }
        @JavascriptInterface fun setSecret(name: String, value: String): Boolean {
            if (name !in SECRET_NAMES || value.length > 4000) return false
            return try { secretPrefs.edit().putString(name, value).commit() } catch (e: Exception) { false }
        }

        // Lista fechada: o conteúdo da página não pode escolher pacotes arbitrários.
        @JavascriptInterface fun openApp(key: String, requestId: String) {
            val packages = mapOf(
                "youtube" to "com.google.android.youtube",
                "spotify" to "com.spotify.music",
                "chrome" to "com.android.chrome",
                "whatsapp" to "com.whatsapp",
                "maps" to "com.google.android.apps.maps",
                "playstore" to "com.android.vending",
                "youtubemusic" to "com.google.android.apps.youtube.music"
            )
            val packageName = packages[key.lowercase(Locale.ROOT)]
            runOnUiThread {
                if (packageName == null) {
                    actionResult(requestId, false, "Aplicativo não permitido nesta versão.")
                    return@runOnUiThread
                }
                try {
                    val launch = packageManager.getLaunchIntentForPackage(packageName)
                    if (launch == null) actionResult(requestId, false, "Esse aplicativo não está instalado ou não pode ser aberto.")
                    else {
                        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        startActivity(launch)
                        actionResult(requestId, true, "Aplicativo iniciado.")
                    }
                } catch (_: Exception) {
                    actionResult(requestId, false, "O Android não conseguiu abrir esse aplicativo.")
                }
            }
        }

        @JavascriptInterface fun searchWeb(query: String, requestId: String) {
            val clean = query.trim().take(240)
            runOnUiThread {
                if (clean.length < 2) {
                    actionResult(requestId, false, "Digite um termo de pesquisa maior.")
                    return@runOnUiThread
                }
                try {
                    val uri = Uri.parse("https://www.google.com/search?q=" + Uri.encode(clean))
                    startActivity(Intent(Intent.ACTION_VIEW, uri))
                    actionResult(requestId, true, "Pesquisa encaminhada ao navegador.")
                } catch (_: Exception) {
                    actionResult(requestId, false, "Não encontrei um navegador disponível para abrir a pesquisa.")
                }
            }
        }
    }

    private fun configureWppAndAiEndpoint(auto: Boolean, nome: String, endpoint: String, model: String) {
        val prefs = getSharedPreferences("jarvis_wpp", MODE_PRIVATE)
        prefs.edit()
            .putBoolean("auto", auto)
            .putString("nome", nome.take(60))
            .apply()

        val currentEndpoint = prefs.getString("endpoint", "") ?: ""
        val currentModel = prefs.getString("model", "") ?: ""
        val candidate = endpoint.trim()
        val cleanModel = model.trim()

        fun notifyConfig(ok: Boolean, savedEndpoint: String, savedModel: String, message: String) {
            js(
                "jarvisNativeAiConfigResult",
                "$ok, ${JSONObject.quote(savedEndpoint)}, ${JSONObject.quote(savedModel)}, ${JSONObject.quote(message)}"
            )
        }

        if (candidate.isBlank() || candidate.length > 2048 || cleanModel.isBlank() ||
            cleanModel.length > 120 || cleanModel.any { Character.isISOControl(it) }) {
            notifyConfig(false, currentEndpoint, currentModel, "Endpoint ou modelo inválido.")
            return
        }

        val validatedEndpoint = validateAiEndpoint(candidate)
        if (validatedEndpoint == null) {
            notifyConfig(false, currentEndpoint, currentModel, "Endpoint inválido. Use HTTPS remoto ou HTTP somente em localhost/127.0.0.1, sem usuário, senha, query ou fragmento.")
            return
        }
        val normalizedEndpoint = validatedEndpoint.normalized

        fun saveConfig() {
            prefs.edit()
                .putString("endpoint", normalizedEndpoint)
                .putString("model", cleanModel)
                .apply()
            notifyConfig(true, normalizedEndpoint, cleanModel, "Servidor de IA configurado.")
        }

        if (validatedEndpoint.local) {
            try {
                secretPrefs.edit()
                    .remove("ai_approved_origin")
                    .remove("ai_approved_endpoint")
                    .apply()
            } catch (_: Exception) {}
            saveConfig()
            return
        }

        val approvedEndpoint = try {
            secretPrefs.getString("ai_approved_endpoint", "") ?: ""
        } catch (_: Exception) { "" }
        if (approvedEndpoint == normalizedEndpoint) {
            saveConfig()
            return
        }
        if (aiConfigPromptOpen) return

        aiConfigPromptOpen = true
        try {
            android.app.AlertDialog.Builder(this)
                .setTitle("Autorizar servidor de IA")
                .setMessage("O JARVIS enviará suas mensagens e a chave da IA para ${validatedEndpoint.display}. Só autorize se você confia nesse endpoint completo.")
                .setPositiveButton("Autorizar") { _, _ ->
                    aiConfigPromptOpen = false
                    val saved = try {
                        secretPrefs.edit()
                            .putString("ai_approved_endpoint", normalizedEndpoint)
                            .remove("ai_approved_origin")
                            .commit()
                    } catch (_: Exception) { false }
                    if (saved) saveConfig()
                    else notifyConfig(false, currentEndpoint, currentModel, "Não foi possível salvar a autorização do servidor.")
                }
                .setNegativeButton("Cancelar") { _, _ ->
                    aiConfigPromptOpen = false
                    notifyConfig(false, currentEndpoint, currentModel, "Alteração do servidor cancelada.")
                }
                .setOnCancelListener {
                    aiConfigPromptOpen = false
                    notifyConfig(false, currentEndpoint, currentModel, "Alteração do servidor cancelada.")
                }
                .show()
        } catch (_: Exception) {
            aiConfigPromptOpen = false
            notifyConfig(false, currentEndpoint, currentModel, "Não foi possível confirmar o servidor.")
        }
    }

    private fun submitAiRequest(messagesJson: String, requestId: String) {
        val id = requestId.take(80)
        if (!Regex("[A-Za-z0-9_-]{1,80}").matches(id)) {
            nativeAiResult(id, false, "", "Identificador de requisição inválido.")
            return
        }
        if (messagesJson.length > 200_000) {
            nativeAiResult(id, false, "", "A solicitação ultrapassou o limite permitido.")
            return
        }
        if (aiRequests.size >= 4) {
            nativeAiResult(id, false, "", "O JARVIS já está processando outras solicitações.")
            return
        }

        val pending = AiRequest()
        if (aiRequests.putIfAbsent(id, pending) != null) {
            nativeAiResult(id, false, "", "Identificador de requisição repetido.")
            return
        }
        try {
            aiExecutor.execute { performAiRequest(id, pending, messagesJson) }
        } catch (_: Exception) {
            aiRequests.remove(id, pending)
            nativeAiResult(id, false, "", "Não foi possível iniciar a solicitação à IA.")
        }
    }

    private fun cancelAiRequest(requestId: String) {
        val id = requestId.take(80)
        aiRequests[id]?.let {
            it.cancelled.set(true)
            try { it.connection?.disconnect() } catch (_: Exception) {}
        }
    }

    private fun performAiRequest(id: String, pending: AiRequest, messagesJson: String) {
        var connection: HttpURLConnection? = null
        try {
            if (pending.cancelled.get()) return
            val prefs = getSharedPreferences("jarvis_wpp", MODE_PRIVATE)
            val endpoint = prefs.getString("endpoint", "")?.trim().orEmpty()
            val model = prefs.getString("model", "")?.trim().orEmpty()
            if (endpoint.isBlank() || model.isBlank()) {
                throw IllegalArgumentException("Configure o endereço e o modelo da IA.")
            }

            val validatedEndpoint = validateAiEndpoint(endpoint)
                ?: throw IllegalArgumentException("O endereço da IA não passou pela validação de segurança.")
            if (validatedEndpoint.normalized != endpoint) {
                throw IllegalArgumentException("Reconfigure o endpoint da IA para confirmar seu endereço normalizado.")
            }
            if (!validatedEndpoint.local) {
                val approved = try {
                    secretPrefs.getString("ai_approved_endpoint", "") ?: ""
                } catch (_: Exception) { "" }
                if (approved != validatedEndpoint.normalized) {
                    throw IllegalArgumentException("Confirme o endpoint completo da IA nas configurações.")
                }
            }

            val messages = JSONArray(messagesJson)
            if (messages.length() !in 1..60) {
                throw IllegalArgumentException("Quantidade de mensagens inválida.")
            }
            var totalChars = 0
            for (index in 0 until messages.length()) {
                val item = messages.optJSONObject(index)
                    ?: throw IllegalArgumentException("Formato de mensagem inválido.")
                if (item.optString("role") !in setOf("system", "user", "assistant")) {
                    throw IllegalArgumentException("Papel de mensagem não permitido.")
                }
                val content = item.opt("content") as? String
                    ?: throw IllegalArgumentException("O conteúdo das mensagens deve ser texto.")
                totalChars += content.length
                if (totalChars > 150_000) {
                    throw IllegalArgumentException("O contexto ultrapassou o limite permitido.")
                }
            }

            val body = JSONObject()
                .put("model", model)
                .put("messages", messages)
                .put("stream", false)

            connection = URL(validatedEndpoint.normalized).openConnection() as? HttpURLConnection
                ?: throw IOException("Tipo de conexão não permitido.")
            pending.connection = connection
            if (pending.cancelled.get()) return

            connection.instanceFollowRedirects = false
            connection.connectTimeout = 15_000
            connection.readTimeout = 45_000
            connection.requestMethod = "POST"
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
            connection.setRequestProperty("Accept", "application/json")
            val apiKey = try { secretPrefs.getString("ai_key", "") ?: "" } catch (_: Exception) { "" }
            if (apiKey.isNotBlank()) connection.setRequestProperty("Authorization", "Bearer $apiKey")

            connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            if (pending.cancelled.get()) return
            val status = connection.responseCode
            if (status !in 200..299) {
                if (status in 300..399) throw IOException("O servidor redirecionou a solicitação. Configure o endereço final.")
                throw IOException("Servidor de IA respondeu HTTP $status.")
            }

            val responseText = connection.inputStream.use { input ->
                val output = ByteArrayOutputStream()
                val buffer = ByteArray(8192)
                var total = 0
                while (true) {
                    val count = input.read(buffer)
                    if (count < 0) break
                    total += count
                    if (total > 2_000_000) throw IOException("A resposta da IA ultrapassou o limite permitido.")
                    output.write(buffer, 0, count)
                }
                output.toString("UTF-8")
            }

            val rawContent = JSONObject(responseText)
                .optJSONArray("choices")
                ?.optJSONObject(0)
                ?.optJSONObject("message")
                ?.opt("content")
            val answer = when (rawContent) {
                is String -> rawContent
                is JSONArray -> buildString {
                    for (index in 0 until rawContent.length()) {
                        when (val part = rawContent.opt(index)) {
                            is String -> append(part)
                            is JSONObject -> append(part.optString("text", ""))
                        }
                    }
                }
                else -> ""
            }
            if (answer.isBlank()) throw IOException("O modelo não retornou texto.")
            if (!pending.cancelled.get()) nativeAiResult(id, true, answer, null)
        } catch (_: SocketTimeoutException) {
            if (!pending.cancelled.get()) nativeAiResult(id, false, "", "A IA demorou mais de 45 segundos para responder.")
        } catch (e: IllegalArgumentException) {
            if (!pending.cancelled.get()) nativeAiResult(id, false, "", e.message ?: "Configuração da IA inválida.")
        } catch (_: Exception) {
            if (!pending.cancelled.get()) nativeAiResult(id, false, "", "Não foi possível concluir a solicitação à IA.")
        } finally {
            try { connection?.disconnect() } catch (_: Exception) {}
            pending.connection = null
            aiRequests.remove(id, pending)
        }
    }

    private fun nativeAiResult(id: String, ok: Boolean, text: String, error: String?) {
        val errorArg = if (error == null) "null" else JSONObject.quote(error.take(240))
        js(
            "jarvisNativeAIResult",
            "${JSONObject.quote(id)}, $ok, ${JSONObject.quote(text)}, $errorArg"
        )
    }

    private fun cancelAllAiRequests(reason: String?) {
        val pendingRequests = aiRequests.entries.toList()
        for ((id, request) in pendingRequests) {
            request.cancelled.set(true)
            try { request.connection?.disconnect() } catch (_: Exception) {}
            if (reason != null) nativeAiResult(id, false, "", reason)
        }
    }

    private fun actionResult(requestId: String, ok: Boolean, message: String) {
        val id = org.json.JSONObject.quote(requestId.take(80))
        val msg = org.json.JSONObject.quote(message.take(240))
        js("jarvisNativeActionResult", "$id, $ok, $msg")
    }

    private fun js(name: String, args: String) {
        if (!callbacksEnabled || !::webView.isInitialized) return
        runOnUiThread {
            if (callbacksEnabled) {
                try { webView.evaluateJavascript("window.$name($args)", null) } catch (_: Exception) {}
            }
        }
    }

    private fun beginListening() {
        if (isFinishing) return
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            pendingPermissionStart = true
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), REQ_AUDIO)
            return
        }
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            js("jarvisNativeError", "'Nenhum serviço de reconhecimento de voz está instalado.' , 'unavailable'")
            return
        }
        stopRecognition()
        recognizer = try {
            if (Build.VERSION.SDK_INT >= 31 && SpeechRecognizer.isOnDeviceRecognitionAvailable(this))
                SpeechRecognizer.createOnDeviceSpeechRecognizer(this)
            else SpeechRecognizer.createSpeechRecognizer(this)
        } catch (_: Exception) { SpeechRecognizer.createSpeechRecognizer(this) }
        recognizer?.setRecognitionListener(this)
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "pt-BR")
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "pt-BR")
            putExtra(RecognizerIntent.EXTRA_ONLY_RETURN_LANGUAGE_PREFERENCE, false)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
            putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, packageName)
        }
        try { recognizer?.startListening(intent); listening = true }
        catch (_: Exception) { listening = false; js("jarvisNativeError", "'Falha ao iniciar o microfone.' , 'start'" ) }
    }

    private fun stopRecognition() {
        listening = false
        try { recognizer?.cancel() } catch (_: Exception) {}
        try { recognizer?.destroy() } catch (_: Exception) {}
        recognizer = null
    }

    private fun speakNative(text: String, id: String, rate: Float, pitch: Float) {
        lastUtteranceId = id
        val engine = tts
        if (engine == null) { finishSpeech(id, "O motor de voz não está disponível."); return }
        if (!ttsInitDone) {
            // O TTS ainda está iniciando: guarda a fala e toca quando onInit terminar.
            pendingSpeak = { speakNative(text, id, rate, pitch) }
            return
        }
        if (!ttsReady) { finishSpeech(id, ttsFailure ?: "O motor de voz não está pronto."); return }
        engine.setSpeechRate(rate.coerceIn(0.5f, 2.0f))
        engine.setPitch(pitch.coerceIn(0.1f, 1.5f))
        val result = engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "jarvis-$id")
        if (result == TextToSpeech.ERROR) finishSpeech(id, "Falha na síntese de voz.")
    }

    private fun finishSpeech(id: String, error: String?) {
        val errArg = if (error == null) "null" else org.json.JSONObject.quote(error)
        js("jarvisNativeTtsDone", "${JSONObjectQuote(id)}, $errArg")
    }

    private fun JSONObjectQuote(value: String): String = org.json.JSONObject.quote(value)
    override fun onInit(status: Int) {
        ttsInitDone = true
        val engine = tts
        if (status != TextToSpeech.SUCCESS || engine == null) {
            ttsFailure = "O motor de voz do Android não iniciou. Confira em Configurações > Idiomas > Saída de voz."
        } else {
            val languageOk = listOf(Locale("pt", "BR"), Locale("pt")).any { locale ->
                val r = engine.setLanguage(locale)
                r != TextToSpeech.LANG_MISSING_DATA && r != TextToSpeech.LANG_NOT_SUPPORTED
            }
            if (!languageOk) {
                ttsFailure = "Português não está instalado no motor de voz. Em Configurações > Idiomas > Saída de voz, baixe os dados de português do Brasil."
            }
            engine.setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ASSISTANT)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build()
            )
            engine.setSpeechRate(0.95f)
            engine.setPitch(0.85f)
            engine.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) {}
                override fun onDone(utteranceId: String?) {
                    val id = utteranceId?.removePrefix("jarvis-") ?: return
                    finishSpeech(id, null)
                }
                @Deprecated("Deprecated in Java")
                override fun onError(utteranceId: String?) {
                    val id = utteranceId?.removePrefix("jarvis-") ?: return
                    finishSpeech(id, "Erro na reprodução da voz.")
                }
                override fun onError(utteranceId: String?, errorCode: Int) {
                    val id = utteranceId?.removePrefix("jarvis-") ?: return
                    finishSpeech(id, "Erro na reprodução da voz (código $errorCode).")
                }
            })
        }
        ttsReady = status == TextToSpeech.SUCCESS && ttsFailure == null
        pendingSpeak?.invoke()
        pendingSpeak = null
    }

    override fun onReadyForSpeech(params: Bundle?) { listening = true }
    override fun onBeginningOfSpeech() {}
    override fun onRmsChanged(rmsdB: Float) {}
    override fun onBufferReceived(buffer: ByteArray?) {}
    override fun onEndOfSpeech() { listening = false }
    override fun onError(error: Int) {
        listening = false
        val (message, code) = when (error) {
            SpeechRecognizer.ERROR_NETWORK, SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "Falha de rede no reconhecimento." to "network"
            SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Permissão do microfone negada." to "permission"
            SpeechRecognizer.ERROR_AUDIO -> "Erro ao capturar áudio." to "audio"
            SpeechRecognizer.ERROR_NO_MATCH, SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "Não entendi. Pode repetir?" to "nomatch"
            SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "Reconhecimento ocupado; tentando novamente." to "busy"
            else -> "Reconhecimento de voz falhou (código $error)." to "voice"
        }
        js("jarvisNativeError", "${JSONObjectQuote(message)}, ${JSONObjectQuote(code)}")
    }
    override fun onResults(results: Bundle?) {
        listening = false
        val text = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty()
        js("jarvisNativeResult", "${JSONObjectQuote(text)}, true")
    }
    override fun onPartialResults(partialResults: Bundle?) {
        val text = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty()
        if (text.isNotBlank()) js("jarvisNativeResult", "${JSONObjectQuote(text)}, false")
    }
    override fun onEvent(eventType: Int, params: Bundle?) {}

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQ_AUDIO && pendingPermissionStart) {
            pendingPermissionStart = false
            if (grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) beginListening()
            else js("jarvisNativeError", "'Permissão do microfone negada. Libere nas configurações do Android.' , 'permission'")
        }
    }

    override fun onResume() {
        super.onResume()
        if (::webView.isInitialized) webView.evaluateJavascript("window.jarvisNativeResume && window.jarvisNativeResume()", null)
        JarvisOuvidoService.telaAtiva(true)
        if (pendingWake && ::webView.isInitialized) { pendingWake = false; js("jarvisWake", "") }
    }
    override fun onPause() {
        cancelAllAiRequests("Consulta interrompida porque o JARVIS foi para segundo plano.")
        stopRecognition()
        JarvisOuvidoService.telaAtiva(false)
        super.onPause()
    }
    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        if (intent?.getBooleanExtra("wake", false) == true && ::webView.isInitialized) js("jarvisWake", "")
    }

    private fun ouvirAtivo(): Boolean =
        getSharedPreferences("jarvis_ouvir", MODE_PRIVATE).getBoolean("ativo", false)

    private fun iniciarOuvirSeAtivo() {
        if (!ouvirAtivo()) return
        try { ContextCompat.startForegroundService(this, Intent(this, JarvisOuvidoService::class.java)) } catch (_: Exception) {}
    }

    override fun onDestroy() {
        callbacksEnabled = false
        cancelAllAiRequests(null)
        aiExecutor.shutdownNow()
        stopRecognition()
        tts?.stop(); tts?.shutdown(); tts = null
        if (::webView.isInitialized) { webView.removeJavascriptInterface("JarvisAndroid"); webView.destroy() }
        super.onDestroy()
    }
}
