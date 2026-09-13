package com.thunder.app.data

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID

data class ChatMessage(
    val who: String,
    val text: String,
    val at: Long = System.currentTimeMillis()
)

data class Chat(
    val id: String,
    val title: String,
    val createdAt: Long,
    val updatedAt: Long,
    val messages: List<ChatMessage>
)

class ChatStore(context: Context) {
    private val file = File(context.applicationContext.filesDir, "thunder_chats.json")
    private val lock = Any()

    fun newId(): String = UUID.randomUUID().toString()

    fun list(): List<Chat> = synchronized(lock) {
        load().sortedByDescending { it.updatedAt }
    }

    fun get(id: String): Chat? = synchronized(lock) {
        load().find { it.id == id }
    }

    fun upsert(chat: Chat) = synchronized(lock) {
        val all = load().toMutableList()
        val index = all.indexOfFirst { it.id == chat.id }
        if (index >= 0) all[index] = chat else all.add(chat)
        persist(all)
    }

    fun delete(id: String) = synchronized(lock) {
        persist(load().filterNot { it.id == id })
    }

    fun rename(id: String, title: String) = synchronized(lock) {
        persist(
            load().map { chat ->
                if (chat.id == id) chat.copy(title = title.trim().ifBlank { chat.title }) else chat
            }
        )
    }

    private fun load(): List<Chat> {
        if (!file.exists()) return emptyList()
        return try {
            val root = JSONObject(file.readText())
            val arr = root.optJSONArray("chats") ?: return emptyList()
            buildList {
                for (i in 0 until arr.length()) {
                    val obj = arr.getJSONObject(i)
                    val msgs = obj.optJSONArray("messages") ?: JSONArray()
                    add(
                        Chat(
                            id = obj.getString("id"),
                            title = obj.optString("title", "New chat"),
                            createdAt = obj.optLong("createdAt"),
                            updatedAt = obj.optLong("updatedAt"),
                            messages = buildList {
                                for (j in 0 until msgs.length()) {
                                    val m = msgs.getJSONObject(j)
                                    add(
                                        ChatMessage(
                                            who = m.optString("who"),
                                            text = m.optString("text"),
                                            at = m.optLong("at")
                                        )
                                    )
                                }
                            }
                        )
                    )
                }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun persist(chats: List<Chat>) {
        val arr = JSONArray()
        chats.forEach { chat ->
            val msgs = JSONArray()
            chat.messages.forEach { message ->
                msgs.put(
                    JSONObject()
                        .put("who", message.who)
                        .put("text", message.text)
                        .put("at", message.at)
                )
            }
            arr.put(
                JSONObject()
                    .put("id", chat.id)
                    .put("title", chat.title)
                    .put("createdAt", chat.createdAt)
                    .put("updatedAt", chat.updatedAt)
                    .put("messages", msgs)
            )
        }
        val parent = file.parentFile ?: return
        val tmp = File(parent, "${file.name}.tmp")
        tmp.writeText(JSONObject().put("chats", arr).toString())
        if (!tmp.renameTo(file)) {
            tmp.copyTo(file, overwrite = true)
            tmp.delete()
        }
    }
}

fun titleFromMessage(text: String): String {
    val cleaned = text.trim().replace('\n', ' ').replace(Regex("\\s+"), " ")
    if (cleaned.isBlank()) return "New chat"
    return if (cleaned.length <= 36) cleaned else cleaned.take(33).trimEnd() + "…"
}
