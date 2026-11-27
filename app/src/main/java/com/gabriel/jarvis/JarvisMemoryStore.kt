package com.gabriel.jarvis

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import org.json.JSONArray

/**
 * Memória factual local do Android.
 *
 * Migra "fatos" do SharedPreferences antigo para armazenamento criptografado.
 * A cópia antiga só é removida depois que a gravação criptografada confirma sucesso.
 */
internal object JarvisMemoryStore {
    private const val LEGACY_PREFERENCES = "jarvis_memoria"
    private const val SECURE_PREFERENCES = "jarvis_memoria_secure"
    private const val FACTS_KEY = "fatos"

    @Synchronized
    fun facts(context: Context): List<String> {
        val app = context.applicationContext
        val secure = encryptedPreferences(app) ?: return readLegacy(app)
        return readOrMigrate(app, secure) ?: readLegacy(app)
    }

    @Synchronized
    fun add(context: Context, fact: String): Boolean {
        if (fact.isBlank()) return false
        val app = context.applicationContext
        val secure = encryptedPreferences(app) ?: return false
        val current = readOrMigrate(app, secure) ?: return false
        val updated = MemoryFactsPolicy.append(current, fact)
        return try {
            secure.edit().putString(FACTS_KEY, JSONArray(updated).toString()).commit()
        } catch (_: Exception) {
            false
        }
    }

    @Synchronized
    fun clear(context: Context): Boolean {
        val app = context.applicationContext
        val secure = encryptedPreferences(app) ?: return false
        val secureCleared = try {
            secure.edit().remove(FACTS_KEY).commit()
        } catch (_: Exception) {
            false
        }
        if (!secureCleared) return false
        return try {
            app.getSharedPreferences(LEGACY_PREFERENCES, Context.MODE_PRIVATE)
                .edit().remove(FACTS_KEY).commit()
        } catch (_: Exception) {
            false
        }
    }

    /**
     * Retorna null quando o cofre não pode ser lido ou os dados estão inválidos.
     * Nesse caso, a cópia legada é preservada e nenhuma migração destrutiva ocorre.
     */
    private fun readOrMigrate(context: Context, secure: SharedPreferences): List<String>? {
        val secureRaw = try {
            secure.getString(FACTS_KEY, null)
        } catch (_: Exception) {
            return null
        }

        if (secureRaw != null) {
            val secureFacts = decode(secureRaw) ?: return null
            // Se uma execução anterior gravou o novo formato mas falhou ao limpar o antigo,
            // a cópia legada só é removida agora que a cópia segura foi validada.
            try {
                context.getSharedPreferences(LEGACY_PREFERENCES, Context.MODE_PRIVATE)
                    .edit().remove(FACTS_KEY).commit()
            } catch (_: Exception) {
                // A memória criptografada continua válida; a cópia antiga fica preservada.
            }
            return secureFacts
        }

        val legacy = context.getSharedPreferences(LEGACY_PREFERENCES, Context.MODE_PRIVATE)
        val legacyRaw = try {
            legacy.getString(FACTS_KEY, null)
        } catch (_: Exception) {
            return null
        } ?: return emptyList()

        val legacyFacts = decode(legacyRaw) ?: return null
        val normalized = MemoryFactsPolicy.normalize(legacyFacts)
        val saved = try {
            secure.edit().putString(FACTS_KEY, JSONArray(normalized).toString()).commit()
        } catch (_: Exception) {
            false
        }
        if (saved) {
            try {
                legacy.edit().remove(FACTS_KEY).commit()
            } catch (_: Exception) {
                // Não apagar nem invalidar a cópia legada quando a limpeza falhar.
            }
        }
        return normalized
    }

    private fun readLegacy(context: Context): List<String> {
        val raw = try {
            context.getSharedPreferences(LEGACY_PREFERENCES, Context.MODE_PRIVATE)
                .getString(FACTS_KEY, null)
        } catch (_: Exception) {
            null
        } ?: return emptyList()
        return decode(raw) ?: emptyList()
    }

    private fun decode(raw: String): List<String>? = try {
        val array = JSONArray(raw)
        val values = ArrayList<String>(array.length())
        for (index in 0 until array.length()) {
            val value = array.opt(index)
            if (value is String) values.add(value)
        }
        MemoryFactsPolicy.normalize(values)
    } catch (_: Exception) {
        null
    }

    private fun encryptedPreferences(context: Context): SharedPreferences? = try {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            SECURE_PREFERENCES,
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    } catch (_: Exception) {
        null
    }
}
