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
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.net.Uri
import androidx.core.content.ContextCompat
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import androidx.webkit.WebViewAssetLoader
import java.util.Locale

class MainActivity : Activity(), RecognitionListener, TextToSpeech.OnInitListener {
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
        private val SECRET_NAMES = setOf("busca_url", "busca_token", "ai_key")
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
        window.statusBarColor = android.graphics.Color.rgb(10, 6, 4)
        window.navigationBarColor = android.graphics.Color.rgb(10, 6, 4)
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
        @JavascriptInterface fun startListening() { runOnUiThread { beginListening() } }
        @JavascriptInterface fun stopListening() { runOnUiThread { stopRecognition() } }
        @JavascriptInterface fun speak(text: String, id: String, rate: Float, pitch: Float) { runOnUiThread { speakNative(text, id, rate, pitch) } }
        @JavascriptInterface fun stopSpeaking() { runOnUiThread { tts?.stop() } }
        @JavascriptInterface fun platform(): String = "android-native"
        @JavascriptInterface fun getSecret(name: String): String {
            if (name !in SECRET_NAMES) return ""
            return try { secretPrefs.getString(name, "") ?: "" } catch (e: Exception) { "" }
        }
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

    override fun onResume() { super.onResume(); if (::webView.isInitialized) webView.evaluateJavascript("window.jarvisNativeResume && window.jarvisNativeResume()", null) }
    override fun onPause() { stopRecognition(); super.onPause() }
    override fun onDestroy() {
        stopRecognition()
        tts?.stop(); tts?.shutdown(); tts = null
        if (::webView.isInitialized) { webView.removeJavascriptInterface("JarvisAndroid"); webView.destroy() }
        super.onDestroy()
    }
}
