package com.gabriel.jarvis

import android.Manifest
import android.media.AudioAttributes
import android.app.Activity
import android.app.PendingIntent
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.net.Uri
import android.provider.Settings
import android.os.Environment
import java.io.File
import java.util.concurrent.CompletableFuture
import java.util.concurrent.TimeUnit
import androidx.core.content.ContextCompat
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import androidx.webkit.WebViewAssetLoader
import java.util.Locale
import java.net.HttpURLConnection
import java.net.URL
import org.json.JSONObject

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

    companion object {
        private const val REQ_AUDIO = 4102
        private const val REQ_NOTIF = 4103
        private val SECRET_NAMES = setOf("busca_url", "busca_token", "ai_key", "groq_key", "gemini_key", "tavily_key", "brapi_key", "pin_hash", "picovoice_key")
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
        window.statusBarColor = android.graphics.Color.rgb(7, 17, 31)
        window.navigationBarColor = android.graphics.Color.rgb(7, 17, 31)
        tts = TextToSpeech(this, this)
        assetLoader = WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()

        webView = WebView(this)
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.allowFileAccess = false
        webView.settings.allowContentAccess = false
        webView.settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
        webView.settings.javaScriptCanOpenWindowsAutomatically = false
        webView.addJavascriptInterface(NativeBridge(), "JarvisAndroid")
        webView.webViewClient = object : WebViewClient() {
            override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest) =
                assetLoader.shouldInterceptRequest(request.url)

            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val uri = request.url
                if (uri.host == "appassets.androidplatform.net") return false
                if (uri.scheme == "https" || uri.scheme == "http") {
                    startActivity(Intent(Intent.ACTION_VIEW, uri))
                    return true
                }
                return true
            }
        }
        setContentView(webView)
        webView.loadUrl("https://appassets.androidplatform.net/assets/index.html")
    }

    inner class NativeBridge {
        @JavascriptInterface fun scheduleReminder(title: String, eventTimeMillis: Long): String {
            if (Build.VERSION.SDK_INT >= 33 &&
                checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                runOnUiThread { requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), REQ_NOTIF) }
                return "permission"
            }
            if (eventTimeMillis <= System.currentTimeMillis()) return "past"
            return try {
                val alarmManager = getSystemService(ALARM_SERVICE) as android.app.AlarmManager
                val safeTitle = title.take(160).ifBlank { "Compromisso" }
                val requestCode = (safeTitle + eventTimeMillis).hashCode()
                val intent = Intent(this@MainActivity, ReminderReceiver::class.java)
                    .putExtra("title", safeTitle)
                    .putExtra("event_time", eventTimeMillis)
                val pending = PendingIntent.getBroadcast(
                    this@MainActivity, requestCode, intent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )
                val triggerAt = maxOf(System.currentTimeMillis(), eventTimeMillis - 10 * 60 * 1000L)
                val exactAllowed = Build.VERSION.SDK_INT < 31 || alarmManager.canScheduleExactAlarms()
                if (exactAllowed) {
                    alarmManager.setExactAndAllowWhileIdle(android.app.AlarmManager.RTC_WAKEUP, triggerAt, pending)
                    "exact"
                } else {
                    alarmManager.setAndAllowWhileIdle(android.app.AlarmManager.RTC_WAKEUP, triggerAt, pending)
                    "approximate"
                }
            } catch (_: Exception) {
                "error"
            }
        }
        @JavascriptInterface fun openExactAlarmSettings() {
            if (Build.VERSION.SDK_INT >= 31) {
                runOnUiThread {
                    try {
                        startActivity(Intent(android.provider.Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM,
                            Uri.parse("package:$packageName")))
                    } catch (_: Exception) {}
                }
            }
        }
        @JavascriptInterface fun openDialer(number: String): Boolean {
            val clean = number.filter { it.isDigit() || it == '+' }
            if (clean.isBlank()) return false
            return try {
                runOnUiThread {
                    startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:$clean")))
                }
                true
            } catch (_: Exception) { false }
        }
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
            if (name !in SECRET_NAMES) return ""
            return try { secretPrefs.getString(name, "") ?: "" } catch (e: Exception) { "" }
        }

        @JavascriptInterface fun testApi(name: String): String {
            val secretName = when (name) {
                "groq" -> "groq_key"
                "gemini" -> "gemini_key"
                "tavily" -> "tavily_key"
                "brapi" -> "brapi_key"
                else -> return "Serviço não reconhecido."
            }
            val key = try { secretPrefs.getString(secretName, "") ?: "" } catch (_: Exception) { "" }
            if (key.isBlank()) return "Chave não cadastrada."
            var connection: HttpURLConnection? = null
            return try {
                val target = when (name) {
                    "groq" -> "https://api.groq.com/openai/v1/models"
                    "gemini" -> "https://generativelanguage.googleapis.com/v1beta/models?key=" + Uri.encode(key)
                    "tavily" -> "https://api.tavily.com/search"
                    else -> "https://brapi.dev/api/quote/PETR4?token=" + Uri.encode(key)
                }
                val conn = (URL(target).openConnection() as HttpURLConnection)
                connection = conn
                conn.connectTimeout = 10000
                conn.readTimeout = 10000
                conn.requestMethod = if (name == "tavily") "POST" else "GET"
                conn.setRequestProperty("Accept", "application/json")
                if (name == "groq") conn.setRequestProperty("Authorization", "Bearer $key")
                if (name == "tavily") {
                    conn.doOutput = true
                    conn.setRequestProperty("Content-Type", "application/json")
                    val body = JSONObject().put("api_key", key).put("query", "teste de conexão").put("max_results", 1)
                    conn.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
                }
                val code = conn.responseCode
                if (code in 200..299) "Conexão confirmada." else "A API respondeu HTTP $code."
            } catch (_: java.net.SocketTimeoutException) {
                "Tempo esgotado. Verifique a internet e tente novamente."
            } catch (_: Exception) {
                "Não foi possível conectar. Verifique a chave e a internet."
            } finally {
                connection?.disconnect()
            }
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
            getSharedPreferences("jarvis_wpp", MODE_PRIVATE).edit()
                .putBoolean("auto", auto)
                .putString("nome", nome.take(60))
                .putString("endpoint", endpoint.take(300))
                .putString("model", model.take(120))
                .apply()
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

    private fun actionResult(requestId: String, ok: Boolean, message: String) {
        val id = org.json.JSONObject.quote(requestId.take(80))
        val msg = org.json.JSONObject.quote(message.take(240))
        js("jarvisNativeActionResult", "$id, $ok, $msg")
    }

    private fun js(name: String, args: String) {
        if (!::webView.isInitialized) return
        runOnUiThread { webView.evaluateJavascript("window.$name($args)", null) }
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
    override fun onPause() { stopRecognition(); JarvisOuvidoService.telaAtiva(false); super.onPause() }
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
        stopRecognition()
        tts?.stop(); tts?.shutdown(); tts = null
        if (::webView.isInitialized) { webView.removeJavascriptInterface("JarvisAndroid"); webView.destroy() }
        super.onDestroy()
    }
}
