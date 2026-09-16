package com.thunder.app.ui

/**
 * Splits a reply into plain prose and blocks worth acting on.
 *
 * Thunder is asked for video prompts constantly, and re-selecting one out of a
 * paragraph on a phone is miserable. Fenced code and `Prompt: "..."` lines get
 * lifted out so they can be copied - or sent straight to the generator - in one
 * tap.
 */
sealed interface Segment {
    data class Prose(val text: String) : Segment
    /**
     * [isPrompt] marks a block the Studio can generate from directly.
     * [language] is the fence tag (```python), kept because it is what names
     * the file when the block is saved - a kotlin block should not land as .txt.
     */
    data class Block(val text: String, val isPrompt: Boolean, val language: String = "") : Segment
}

private val FENCE = Regex("```([a-zA-Z0-9_+-]*)\\n?([\\s\\S]*?)```")
private val PROMPT_LINE = Regex("""(?im)^\s*prompt\s*:\s*["“]?(.+?)["”]?\s*$""")

fun parseSegments(reply: String): List<Segment> {
    val out = mutableListOf<Segment>()
    var cursor = 0

    fun addProse(raw: String) {
        // A prompt line inside prose becomes its own block; the rest stays text.
        var at = 0
        for (m in PROMPT_LINE.findAll(raw)) {
            val before = raw.substring(at, m.range.first)
            if (before.isNotBlank()) out.add(Segment.Prose(before.trim()))
            val body = m.groupValues[1].trim()
            if (body.isNotEmpty()) out.add(Segment.Block(body, isPrompt = true))
            at = m.range.last + 1
        }
        val tail = raw.substring(at)
        if (tail.isNotBlank()) out.add(Segment.Prose(tail.trim()))
    }

    for (m in FENCE.findAll(reply)) {
        addProse(reply.substring(cursor, m.range.first))
        val body = m.groupValues[2].trim()
        if (body.isNotEmpty()) {
            out.add(Segment.Block(body, isPrompt = false, language = m.groupValues[1].trim()))
        }
        cursor = m.range.last + 1
    }
    addProse(reply.substring(cursor))
    return out
}
