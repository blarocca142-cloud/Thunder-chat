package com.thunder.app.data

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Seals the access token and the Odris password with a key that lives in the
 * phone's Android Keystore (the secure hardware on any recent phone) and
 * cannot be copied out of it.
 *
 * Before this they sat in plain text in SharedPreferences, and the app allows
 * backup - so they rode along into Google's cloud backup. Now a backup or a
 * copied prefs file holds ciphertext that only this install on this phone can
 * open. Restored onto a new phone it simply reads as empty and gets pasted
 * again, which is the right failure.
 *
 * The key is deliberately not tied to the fingerprint. The six-hourly digest
 * runs in the background with nobody there to touch the sensor, and it needs
 * the token. The fingerprint gates the app; this protects the file.
 */
object SecretBox {
    private const val KEYSTORE = "AndroidKeyStore"
    private const val ALIAS = "thunder_secrets"
    private const val PREFIX = "enc1:"
    private const val IV_BYTES = 12

    fun isSealed(stored: String) = stored.startsWith(PREFIX)

    fun seal(plain: String): String {
        if (plain.isEmpty()) return ""
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val out = cipher.iv + cipher.doFinal(plain.toByteArray(Charsets.UTF_8))
        return PREFIX + Base64.encodeToString(out, Base64.NO_WRAP)
    }

    /** Empty if it cannot be opened - wrong phone, wiped key, tampered text. */
    fun open(stored: String): String {
        if (!isSealed(stored)) return ""
        return runCatching {
            val raw = Base64.decode(stored.removePrefix(PREFIX), Base64.NO_WRAP)
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, raw, 0, IV_BYTES))
            String(cipher.doFinal(raw, IV_BYTES, raw.size - IV_BYTES), Charsets.UTF_8)
        }.getOrDefault("")
    }

    private fun key(): SecretKey {
        val ks = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        (ks.getKey(ALIAS, null) as? SecretKey)?.let { return it }
        val gen = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE)
        gen.init(
            KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build()
        )
        return gen.generateKey()
    }
}
