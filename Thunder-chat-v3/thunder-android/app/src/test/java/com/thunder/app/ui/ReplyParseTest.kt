package com.thunder.app.ui

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ReplyParseTest {
    private val reply = """
        [searching the web: fastapi lifespan]
        [reading https://fastapi.tiangolo.com/advanced/events/]
        [running code]
        Use a **lifespan** handler:

        ```python
        print("[reading not-a-status]")
        ```

        ---
        Check: Links I did not actually open this turn, so treat them as unverified: https://x.example

        Sources read: https://fastapi.tiangolo.com/advanced/events/
    """.trimIndent()

    @Test fun toolStepsAreLiftedOut() {
        val steps = parseReply(reply).filterIsInstance<Part.Steps>().single().steps
        assertEquals(3, steps.size)
        assertEquals("running code", steps.last())
    }

    @Test fun statusLookalikeInsideCodeIsLeftAlone() {
        val code = parseReply(reply).filterIsInstance<Part.Code>().single()
        assertEquals("python", code.language)
        assertTrue(code.text.contains("[reading not-a-status]"))
    }

    @Test fun checksAndSourcesBecomeTheirOwnParts() {
        val parts = parseReply(reply)
        assertEquals(1, parts.filterIsInstance<Part.Checks>().single().notes.size)
        assertEquals(listOf("https://fastapi.tiangolo.com/advanced/events/"),
            parts.filterIsInstance<Part.Sources>().single().urls)
        val prose = parts.filterIsInstance<Part.Markdown>().joinToString("\n") { it.text }
        assertTrue("rule above checks is dropped", !prose.trim().endsWith("---"))
        assertTrue(!prose.contains("Check:") && !prose.contains("Sources read"))
    }

    @Test fun speechSkipsStepsCodeAndMarkdown() {
        val spoken = spokenText(reply)
        assertTrue(spoken.contains("lifespan"))
        assertTrue(!spoken.contains("**") && !spoken.contains("print(") && !spoken.contains("running code"))
    }

    @Test fun plainReplyIsJustProse() {
        val parts = parseReply("Hey. All good here.")
        assertEquals(1, parts.size)
        assertTrue(parts[0] is Part.Markdown)
    }
}
