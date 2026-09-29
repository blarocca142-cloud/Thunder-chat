package com.thunder.app.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Build
import androidx.compose.material.icons.outlined.Code
import androidx.compose.material.icons.outlined.FactCheck
import androidx.compose.material.icons.outlined.ContentCopy
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.ExpandLess
import androidx.compose.material.icons.outlined.ExpandMore
import androidx.compose.material.icons.outlined.Language
import androidx.compose.material.icons.outlined.Memory
import androidx.compose.material.icons.outlined.PlayArrow
import androidx.compose.material.icons.outlined.Save
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material.icons.outlined.WarningAmber
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.LinkAnnotation
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextLinkStyles
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.withLink
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * How a Thunder reply is drawn.
 *
 * The server's replies now carry more than prose: status lines for each tool
 * the model used ("[running code]"), honesty notes under a rule ("Check: ..."),
 * and a list of pages it actually read. Shown raw they are noise; shown the way
 * frontier chat apps show them, they are the evidence that an answer was
 * checked rather than guessed - which is the point of having them.
 */
sealed interface Part {
    data class Steps(val steps: List<String>) : Part
    data class Markdown(val text: String) : Part
    data class Code(val text: String, val language: String) : Part
    data class Prompt(val text: String) : Part
    data class Checks(val notes: List<String>) : Part
    data class Sources(val urls: List<String>) : Part
}

private val STATUS_LINE = Regex(
    """^\[(searching the web|reading |running code|saving |checking |medical content)[^\]]*]\s*$""",
    RegexOption.IGNORE_CASE
)
private val CHECK_LINE = Regex("""^Check:\s*(.+)$""")
private val SOURCES_LINE = Regex("""^Sources read:\s*(.+)$""")

fun parseReply(reply: String): List<Part> {
    val out = mutableListOf<Part>()
    val steps = mutableListOf<String>()
    val checks = mutableListOf<String>()
    val sources = mutableListOf<String>()
    val body = StringBuilder()

    // Status lines, checks and sources are line-shaped and never inside code
    // fences in practice, but fences are respected anyway so a code block that
    // happens to print "[reading x]" is left alone.
    var inFence = false
    for (line in reply.split("\n")) {
        val trimmed = line.trim()
        if (trimmed.startsWith("```")) inFence = !inFence
        if (!inFence) {
            if (STATUS_LINE.matches(trimmed)) {
                steps.add(trimmed.removePrefix("[").removeSuffix("]"))
                continue
            }
            val check = CHECK_LINE.matchEntire(trimmed)
            if (check != null) {
                checks.add(check.groupValues[1])
                continue
            }
            val src = SOURCES_LINE.matchEntire(trimmed)
            if (src != null) {
                sources.addAll(src.groupValues[1].split("·").map { it.trim() }.filter { it.isNotEmpty() })
                continue
            }
        }
        body.append(line).append('\n')
    }

    if (steps.isNotEmpty()) out.add(Part.Steps(steps))
    var text = body.toString().trimEnd()
    if (checks.isNotEmpty()) text = text.removeSuffix("---").trimEnd()
    for (seg in parseSegments(text)) {
        when (seg) {
            is Segment.Prose -> out.add(Part.Markdown(seg.text))
            is Segment.Block -> out.add(
                if (seg.isPrompt) Part.Prompt(seg.text) else Part.Code(seg.text, seg.language)
            )
        }
    }
    if (checks.isNotEmpty()) out.add(Part.Checks(checks))
    if (sources.isNotEmpty()) out.add(Part.Sources(sources))
    return out
}

/** What should be read aloud: the prose, without steps, code or checks. */
fun spokenText(reply: String): String =
    parseReply(reply).filterIsInstance<Part.Markdown>()
        .joinToString(" ") { stripMarkdown(it.text) }
        .ifBlank { reply }

private fun stripMarkdown(s: String): String =
    s.replace(Regex("""[*_`#>]+"""), "").replace(Regex("""\[([^\]]+)]\([^)]+\)"""), "$1")

// ---- drawing ----------------------------------------------------------------

@Composable
fun ReplyView(
    reply: String,
    streaming: Boolean,
    onCopy: (String) -> Unit,
    onSaveCode: (String, String) -> Unit,
    onSendToStudio: ((String) -> Unit)?
) {
    val parts = parseReply(reply)
    Column(Modifier.fillMaxWidth()) {
        parts.forEachIndexed { i, part ->
            when (part) {
                is Part.Steps -> StepsStrip(part.steps, working = streaming && i == parts.lastIndex)
                is Part.Markdown -> MarkdownText(part.text)
                is Part.Code -> CodeCard(part.text, part.language,
                    onCopy = { onCopy(part.text) }, onSave = { onSaveCode(part.text, part.language) })
                is Part.Prompt -> CodeCard(part.text, "prompt",
                    onCopy = { onCopy(part.text) }, onSave = null,
                    onStudio = onSendToStudio?.let { f -> { f(part.text) } })
                is Part.Checks -> ChecksCard(part.notes)
                is Part.Sources -> SourcesRow(part.urls)
            }
            if (i != parts.lastIndex) Spacer(Modifier.height(10.dp))
        }
    }
}

private fun stepIcon(step: String): ImageVector {
    val s = step.lowercase()
    return when {
        s.startsWith("searching") -> Icons.Outlined.Search
        s.startsWith("reading github") -> Icons.Outlined.Code
        s.startsWith("reading http") -> Icons.Outlined.Language
        s.startsWith("reading") -> Icons.Outlined.Description
        s.startsWith("running") -> Icons.Outlined.PlayArrow
        s.startsWith("saving") -> Icons.Outlined.Save
        s.startsWith("checking memory") -> Icons.Outlined.Memory
        s.startsWith("checking the official code list") -> Icons.Outlined.FactCheck
        s.startsWith("medical") -> Icons.Outlined.Shield
        else -> Icons.Outlined.Build
    }
}

private fun stepsSummary(steps: List<String>): String {
    val kinds = linkedMapOf<String, Int>()
    for (s in steps) {
        val l = s.lowercase()
        val k = when {
            l.startsWith("searching") -> "searched"
            l.startsWith("reading github") -> "read GitHub"
            l.startsWith("reading http") -> "read pages"
            l.startsWith("reading") -> "read files"
            l.startsWith("running") -> "ran code"
            l.startsWith("saving") -> "saved files"
            l.startsWith("checking memory") -> "checked memory"
            l.startsWith("checking the official code list") -> "checked codes"
            l.startsWith("checking") -> "checked hardware"
            l.startsWith("medical") -> "medical model"
            else -> "tools"
        }
        kinds[k] = (kinds[k] ?: 0) + 1
    }
    return kinds.entries.joinToString(" · ") { (k, n) -> if (n > 1) "$k ×$n" else k }
}

@Composable
private fun StepsStrip(steps: List<String>, working: Boolean) {
    var open by remember { mutableStateOf(false) }
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .background(ThunderInk.SlateDeep)
            .border(1.dp, ThunderInk.Hairline, RoundedCornerShape(10.dp))
            .clickable { open = !open }
            .padding(horizontal = 12.dp, vertical = 9.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(stepIcon(steps.last()), null, tint = ThunderInk.Gold, modifier = Modifier.size(15.dp))
            Spacer(Modifier.width(8.dp))
            Text(
                if (working) steps.last().replaceFirstChar { it.uppercase() } + "…"
                else "Worked · " + stepsSummary(steps),
                color = if (working) ThunderInk.Ink else ThunderInk.Mute,
                fontSize = 12.5.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f)
            )
            Icon(if (open) Icons.Outlined.ExpandLess else Icons.Outlined.ExpandMore, null,
                tint = ThunderInk.Mute, modifier = Modifier.size(16.dp))
        }
        AnimatedVisibility(open) {
            Column(Modifier.padding(top = 8.dp)) {
                steps.forEach { s ->
                    Row(Modifier.padding(vertical = 3.dp), verticalAlignment = Alignment.CenterVertically) {
                        Icon(stepIcon(s), null, tint = ThunderInk.Mute, modifier = Modifier.size(13.dp))
                        Spacer(Modifier.width(8.dp))
                        Text(s, color = ThunderInk.Mute, fontSize = 12.sp, maxLines = 2,
                            overflow = TextOverflow.Ellipsis)
                    }
                }
            }
        }
    }
}

@Composable
private fun ChecksCard(notes: List<String>) {
    val amber = if (LocalThunderPalette.current.isDark) Color(0xFFE3B341) else Color(0xFF8A6212)
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .background(amber.copy(alpha = 0.10f))
            .border(1.dp, amber.copy(alpha = 0.45f), RoundedCornerShape(10.dp))
            .padding(12.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Outlined.WarningAmber, null, tint = amber, modifier = Modifier.size(16.dp))
            Spacer(Modifier.width(8.dp))
            Text("Thunder's own check", color = amber, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
        }
        notes.forEach {
            Spacer(Modifier.height(6.dp))
            Text(it, color = ThunderInk.Ink, fontSize = 13.sp, lineHeight = 18.sp)
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun SourcesRow(urls: List<String>) {
    val uri = LocalUriHandler.current
    FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        urls.forEach { url ->
            val host = Regex("""^https?://(?:www\.)?([^/]+)""").find(url)?.groupValues?.get(1) ?: url
            Row(
                Modifier
                    .clip(RoundedCornerShape(50))
                    .background(ThunderInk.SlateDeep)
                    .border(1.dp, ThunderInk.Hairline, RoundedCornerShape(50))
                    .clickable { runCatching { uri.openUri(url) } }
                    .padding(horizontal = 10.dp, vertical = 5.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(Icons.Outlined.Language, null, tint = ThunderInk.Gold, modifier = Modifier.size(12.dp))
                Spacer(Modifier.width(5.dp))
                Text(host, color = ThunderInk.Ink, fontSize = 11.5.sp, maxLines = 1)
            }
        }
    }
}

@Composable
private fun CodeCard(
    text: String,
    language: String,
    onCopy: () -> Unit,
    onSave: (() -> Unit)?,
    onStudio: (() -> Unit)? = null
) {
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .background(ThunderInk.SlateDeep)
            .border(1.dp, ThunderInk.Hairline, RoundedCornerShape(10.dp))
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .background(ThunderInk.Hairline.copy(alpha = 0.35f))
                .padding(start = 12.dp, end = 4.dp, top = 2.dp, bottom = 2.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(language.ifBlank { "code" }, color = ThunderInk.Mute, fontSize = 11.5.sp,
                fontFamily = FontFamily.Monospace, modifier = Modifier.weight(1f))
            if (onStudio != null) HeaderAction(Icons.Outlined.PlayArrow, "Studio", onStudio)
            if (onSave != null) HeaderAction(Icons.Outlined.Save, "Save", onSave)
            HeaderAction(Icons.Outlined.ContentCopy, "Copy", onCopy)
        }
        SelectionContainer {
            Text(
                highlight(text, language),
                fontFamily = FontFamily.Monospace,
                fontSize = 12.5.sp,
                lineHeight = 18.sp,
                color = ThunderInk.Ink,
                softWrap = false,
                modifier = Modifier
                    .horizontalScroll(rememberScrollState())
                    .padding(12.dp)
            )
        }
    }
}

@Composable
private fun HeaderAction(icon: ImageVector, label: String, onClick: () -> Unit) {
    Row(
        Modifier
            .clip(RoundedCornerShape(6.dp))
            .clickable { onClick() }
            .padding(horizontal = 8.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, contentDescription = label, tint = ThunderInk.Mute, modifier = Modifier.size(14.dp))
        Spacer(Modifier.width(4.dp))
        Text(label, color = ThunderInk.Mute, fontSize = 11.sp)
    }
}

// ---- syntax colour ------------------------------------------------------------

private val KEYWORDS = setOf(
    // python
    "def", "class", "return", "if", "elif", "else", "for", "while", "in", "not", "and", "or", "import",
    "from", "as", "with", "try", "except", "finally", "raise", "lambda", "yield", "pass", "break",
    "continue", "None", "True", "False", "async", "await", "is", "global", "assert",
    // c-family / kotlin / js / java
    "fun", "val", "var", "const", "let", "function", "new", "this", "null", "true", "false", "public",
    "private", "protected", "static", "void", "int", "String", "when", "object", "interface", "package",
    "export", "default", "switch", "case", "throw", "catch", "override", "suspend", "data", "enum",
    "struct", "impl", "fn", "mut", "use", "pub", "match", "type",
    // shell
    "then", "fi", "do", "done", "esac", "echo", "sudo", "export"
)
private val TOKEN = Regex(
    """(#[^\n]*|//[^\n]*)|("(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')|(\b\d+(?:\.\d+)?\b)|(\b[A-Za-z_][A-Za-z0-9_]*\b)"""
)

@Composable
private fun highlight(code: String, language: String): AnnotatedString {
    val dark = LocalThunderPalette.current.isDark
    val kw = if (dark) Color(0xFFC4A35A) else Color(0xFF8A6212)
    val str = if (dark) Color(0xFF8FCB9B) else Color(0xFF2F7A4A)
    val num = if (dark) Color(0xFF9DB7E0) else Color(0xFF2D5B9A)
    val com = ThunderInk.Mute
    val plainLang = language.lowercase() in setOf("", "text", "txt", "prompt", "output", "log")
    return buildAnnotatedString {
        if (plainLang || code.length > 30_000) {
            append(code); return@buildAnnotatedString
        }
        var at = 0
        for (m in TOKEN.findAll(code)) {
            append(code.substring(at, m.range.first))
            val t = m.value
            val style = when {
                m.groups[1] != null -> SpanStyle(color = com, fontStyle = FontStyle.Italic)
                m.groups[2] != null -> SpanStyle(color = str)
                m.groups[3] != null -> SpanStyle(color = num)
                t in KEYWORDS -> SpanStyle(color = kw, fontWeight = FontWeight.SemiBold)
                else -> null
            }
            if (style != null) withStyle(style) { append(t) } else append(t)
            at = m.range.last + 1
        }
        append(code.substring(at))
    }
}

// ---- markdown ---------------------------------------------------------------

private val INLINE = Regex(
    """(\*\*(.+?)\*\*)|(`([^`]+)`)|(\[([^\]]+)]\((https?://[^)\s]+)\))|((?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\w))|((?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_]))|(https?://[^\s)]+)"""
)

@Composable
private fun inline(text: String, base: SpanStyle = SpanStyle()): AnnotatedString {
    val link = TextLinkStyles(SpanStyle(color = ThunderInk.Gold, textDecoration = TextDecoration.Underline))
    val codeBg = ThunderInk.SlateDeep
    return buildAnnotatedString {
        withStyle(base) {
            var at = 0
            for (m in INLINE.findAll(text)) {
                append(text.substring(at, m.range.first))
                when {
                    m.groups[1] != null -> withStyle(SpanStyle(fontWeight = FontWeight.Bold)) { append(m.groupValues[2]) }
                    m.groups[3] != null -> withStyle(
                        SpanStyle(fontFamily = FontFamily.Monospace, background = codeBg, fontSize = 13.5.sp)
                    ) { append(" ${m.groupValues[4]} ") }
                    m.groups[5] != null -> withLink(LinkAnnotation.Url(m.groupValues[7], link)) { append(m.groupValues[6]) }
                    m.groups[8] != null -> withStyle(SpanStyle(fontStyle = FontStyle.Italic)) { append(m.groupValues[9]) }
                    m.groups[10] != null -> withStyle(SpanStyle(fontStyle = FontStyle.Italic)) { append(m.groupValues[11]) }
                    m.groups[12] != null -> {
                        val url = m.value.trimEnd('.', ',', ';', ':')
                        withLink(LinkAnnotation.Url(url, link)) { append(url) }
                        append(m.value.removePrefix(url))
                    }
                }
                at = m.range.last + 1
            }
            append(text.substring(at))
        }
    }
}

internal sealed interface MdBlock {
    data class Heading(val level: Int, val text: String) : MdBlock
    data class Para(val text: String) : MdBlock
    data class Item(val marker: String, val text: String, val indent: Int) : MdBlock
    data class Quote(val text: String) : MdBlock
    data object Rule : MdBlock
}

private val HEADING = Regex("""^(#{1,6})\s+(.*)$""")
private val BULLET = Regex("""^(\s*)([-*+•])\s+(.*)$""")
private val NUMBERED = Regex("""^(\s*)(\d+[.)])\s+(.*)$""")

internal fun blocks(md: String): List<MdBlock> {
    val out = mutableListOf<MdBlock>()
    val para = StringBuilder()
    fun flush() {
        if (para.isNotBlank()) out.add(MdBlock.Para(para.toString().trim()))
        para.clear()
    }
    for (raw in md.lines()) {
        val line = raw.trimEnd()
        val t = line.trim()
        // One branch per line. This was an elvis chain whose lets returned
        // null, so every heading, bullet and numbered line fell through and
        // was added a second time as plain paragraph text.
        val heading = HEADING.matchEntire(t)
        val bullet = BULLET.matchEntire(line)
        val numbered = NUMBERED.matchEntire(line)
        when {
            heading != null -> { flush(); out.add(MdBlock.Heading(heading.groupValues[1].length, heading.groupValues[2])) }
            // Checked before bullets: "---" also matches the bullet pattern.
            t == "---" || t == "***" || t == "___" -> { flush(); out.add(MdBlock.Rule) }
            bullet != null -> { flush(); out.add(MdBlock.Item("•", bullet.groupValues[3], bullet.groupValues[1].length / 2)) }
            numbered != null -> { flush(); out.add(MdBlock.Item(numbered.groupValues[2], numbered.groupValues[3], numbered.groupValues[1].length / 2)) }
            t.startsWith(">") -> { flush(); out.add(MdBlock.Quote(t.removePrefix(">").trim())) }
            t.isEmpty() -> flush()
            else -> { if (para.isNotEmpty()) para.append(' '); para.append(t) }
        }
    }
    flush()
    return out
}

@Composable
fun MarkdownText(md: String) {
    SelectionContainer {
        Column(verticalArrangement = Arrangement.spacedBy(7.dp)) {
            for (b in blocks(md)) {
                when (b) {
                    is MdBlock.Heading -> Text(
                        inline(b.text),
                        color = ThunderInk.Ink,
                        fontSize = when (b.level) { 1 -> 20.sp; 2 -> 18.sp; else -> 16.sp },
                        fontWeight = FontWeight.SemiBold,
                        lineHeight = 26.sp,
                        modifier = Modifier.padding(top = 4.dp)
                    )
                    is MdBlock.Para -> Text(inline(b.text), color = ThunderInk.Ink, fontSize = 15.sp, lineHeight = 23.sp)
                    is MdBlock.Item -> Row(Modifier.padding(start = (b.indent * 14).dp)) {
                        Text(
                            b.marker, color = ThunderInk.Gold, fontSize = 15.sp, lineHeight = 23.sp,
                            modifier = Modifier.width(if (b.marker == "•") 16.dp else 24.dp)
                        )
                        Text(inline(b.text), color = ThunderInk.Ink, fontSize = 15.sp, lineHeight = 23.sp)
                    }
                    is MdBlock.Quote -> Row {
                        Spacer(
                            Modifier
                                .width(3.dp)
                                .height(22.dp)
                                .background(ThunderInk.Gold.copy(alpha = 0.6f))
                        )
                        Spacer(Modifier.width(10.dp))
                        Text(inline(b.text), color = ThunderInk.Mute, fontSize = 15.sp, lineHeight = 23.sp,
                            fontStyle = FontStyle.Italic)
                    }
                    MdBlock.Rule -> Spacer(
                        Modifier
                            .fillMaxWidth()
                            .height(1.dp)
                            .background(ThunderInk.Hairline)
                    )
                }
            }
        }
    }
}
