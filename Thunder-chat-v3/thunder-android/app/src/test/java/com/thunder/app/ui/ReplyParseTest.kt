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

    @Test fun plainReplyIsJustProse() {
        val parts = parseReply("Hey. All good here.")
        assertEquals(1, parts.size)
        assertTrue(parts[0] is Part.Markdown)
    }

    // Every bullet used to render twice: once as a bullet, then again as a
    // plain "- ..." paragraph (seen on the phone, 2026-09-29).
    @Test fun eachMarkdownLineRendersOnce() {
        val md = "**Atlantic Dance Hall**\n" +
            "- Closing at the end of September.\n" +
            "- Final weekend Sep 25-27.\n" +
            "1. First\n" +
            "## Heading\n" +
            "---\n" +
            "Plain text."
        val out = blocks(md)
        assertEquals(
            listOf(
                MdBlock.Para("**Atlantic Dance Hall**"),
                MdBlock.Item("•", "Closing at the end of September.", 0),
                MdBlock.Item("•", "Final weekend Sep 25-27.", 0),
                MdBlock.Item("1.", "First", 0),
                MdBlock.Heading(2, "Heading"),
                MdBlock.Rule,
                MdBlock.Para("Plain text.")
            ),
            out
        )
    }
}
