package com.thunder.app.ui

import android.annotation.SuppressLint
import android.util.Base64
import android.view.ViewGroup
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView

/**
 * The real Odris dashboard, embedded rather than reimplemented.
 *
 * Odris already has a full ops dashboard - node health, hardware findings with
 * expandable readings, job review, errors, the security log, maintenance mode -
 * and it was only reachable by typing an IP into a browser. Rebuilding all of
 * that in Compose would mean two dashboards drifting apart, and the one on the
 * phone would always be the poorer copy.
 *
 * So this is a WebView pointed at the genuine article. Two things make that work:
 *
 * **Logging in without a prompt.** Odris is the one service on the fleet that
 * really authenticates, and that stays true - proxying it through Main would have
 * put a dashboard that can deploy code onto the LAN behind Main's auth, which
 * defaults to off. Instead the Authorization header is set on the initial load;
 * the dashboard answers with a session cookie, and every `fetch()` the page makes
 * afterwards carries the cookie by itself. That is exactly the path the dashboard
 * was built for - its own source notes that several mobile browsers refuse to
 * re-send Basic credentials on same-origin fetch, so Basic gets you in and the
 * cookie keeps you in.
 *
 * **The page had no viewport tag.** It has a mobile breakpoint in its CSS that
 * never fired, because a phone without a viewport meta reports a 980px width.
 * Fixed on the Odris side; this screen depends on that fix, which is why it
 * renders as one column instead of a zoomed-out desktop page.
 */
@SuppressLint("SetJavaScriptEnabled")
@Composable
fun OdrisDashboard(
    url: String,
    password: String,
    modifier: Modifier = Modifier,
    onOpenSettings: () -> Unit = {}
) {
    if (url.isBlank()) {
        Hint("No dashboard address set.",
             "Settings has a field for it. The default is Odris on port 9005.",
             onOpenSettings, modifier)
        return
    }
    if (password.isBlank()) {
        Hint(
            "Odris needs its password.",
            "The dashboard is the one service on the fleet that actually locks " +
            "its door, so it will not open without it. Paste it in Settings - " +
            "it is on Odris at ~/dashboard_password.txt.",
            onOpenSettings, modifier
        )
        return
    }

    var progress by remember { mutableStateOf(0) }
    var error by remember { mutableStateOf<String?>(null) }
    var webView by remember { mutableStateOf<WebView?>(null) }
    var canGoBack by remember { mutableStateOf(false) }

    // The dashboard has expandable panels, so Back should collapse the page's
    // own history before it leaves the tab.
    BackHandler(enabled = canGoBack) { webView?.goBack() }

    DisposableEffect(Unit) {
        onDispose { webView?.destroy() }
    }

    Column(modifier.fillMaxSize()) {
        if (progress in 1..99) {
            LinearProgressIndicator(
                progress = { progress / 100f },
                modifier = Modifier.fillMaxWidth(),
                color = ThunderInk.Gold,
                trackColor = ThunderInk.Surface
            )
        }
        error?.let { message ->
            Column(Modifier.fillMaxWidth().padding(14.dp)) {
                Text("Could not reach the dashboard", color = ThunderInk.Ink,
                     fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(4.dp))
                Text(message, color = ThunderInk.Mute, fontSize = 12.sp)
                TextButton(onClick = {
                    error = null
                    webView?.loadUrl(url.trimEnd('/') + "/", authHeader(password))
                }) { Text("Try again", color = ThunderInk.Gold) }
            }
        }
        Box(Modifier.fillMaxSize()) {
            AndroidView(
                modifier = Modifier.fillMaxSize(),
                factory = { ctx ->
                    WebView(ctx).apply {
                        layoutParams = ViewGroup.LayoutParams(
                            ViewGroup.LayoutParams.MATCH_PARENT,
                            ViewGroup.LayoutParams.MATCH_PARENT
                        )
                        settings.javaScriptEnabled = true      // the whole page is fetch()
                        settings.domStorageEnabled = true
                        // The page is responsive now, so let it lay out at the
                        // real device width rather than as a shrunken desktop.
                        settings.useWideViewPort = false
                        settings.loadWithOverviewMode = false
                        settings.textZoom = 100
                        setBackgroundColor(android.graphics.Color.TRANSPARENT)

                        webViewClient = object : WebViewClient() {
                            override fun onPageFinished(view: WebView, finishedUrl: String) {
                                progress = 100
                                canGoBack = view.canGoBack()
                            }

                            /** Keep everything inside the dashboard. A stray link
                             *  should not hand the whole tab to some other page,
                             *  and an external URL would arrive without the
                             *  Authorization header anyway. */
                            override fun shouldOverrideUrlLoading(
                                view: WebView, request: WebResourceRequest
                            ): Boolean {
                                val target = request.url.toString()
                                if (!target.startsWith(url.trimEnd('/'))) return true
                                view.loadUrl(target, authHeader(password))
                                return true
                            }

                            override fun onReceivedError(
                                view: WebView,
                                request: WebResourceRequest,
                                err: WebResourceError
                            ) {
                                // Only the main document. A failed favicon is not
                                // worth an error banner over a working dashboard.
                                if (request.isForMainFrame) {
                                    error = err.description?.toString()
                                        ?: "the dashboard did not answer"
                                }
                            }
                        }

                        webChromeClient = object : android.webkit.WebChromeClient() {
                            override fun onProgressChanged(view: WebView, newProgress: Int) {
                                progress = newProgress
                            }
                        }

                        loadUrl(url.trimEnd('/') + "/", authHeader(password))
                        webView = this
                    }
                }
            )
            if (progress < 100 && error == null) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(
                        Modifier.size(28.dp), color = ThunderInk.Gold, strokeWidth = 3.dp
                    )
                }
            }
        }
    }
}

/**
 * Basic auth on the first request only.
 *
 * NO_WRAP matters: the default encoder inserts a newline every 76 characters,
 * and a newline inside an HTTP header value is not a header any more - the whole
 * request would be rejected and it would look like a wrong password.
 */
private fun authHeader(password: String): Map<String, String> = mapOf(
    "Authorization" to "Basic " + Base64.encodeToString(
        "blayne:$password".toByteArray(), Base64.NO_WRAP
    )
)

@Composable
private fun Hint(
    title: String,
    body: String,
    onOpenSettings: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier
            .fillMaxSize()
            .padding(22.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text(title, color = ThunderInk.Ink, fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
        Text(body, color = ThunderInk.Mute, fontSize = 13.sp)
        TextButton(onClick = onOpenSettings) {
            Text("Open Settings", color = ThunderInk.Gold, fontSize = 14.sp)
        }
    }
}
