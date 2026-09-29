package com.thunder.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Bolt
import androidx.compose.material.icons.outlined.Fingerprint
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** Stands in for a locked screen until the fingerprint (or the phone's own
 *  PIN) is given. */
@Composable
fun LockScreen(title: String, message: String?, onUnlock: () -> Unit, modifier: Modifier = Modifier) {
    Box(
        modifier
            .fillMaxSize()
            .background(ThunderInk.SlateMid)
            .clickable(remember { MutableInteractionSource() }, indication = null) {},
        contentAlignment = Alignment.Center
    ) {
        Column(
            Modifier.padding(horizontal = 32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Box(
                Modifier
                    .size(52.dp)
                    .clip(RoundedCornerShape(14.dp))
                    .background(ThunderInk.GoldSoft),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Outlined.Bolt, contentDescription = null, tint = ThunderInk.Gold,
                     modifier = Modifier.size(28.dp))
            }
            Spacer(Modifier.height(18.dp))
            Text(title, color = ThunderInk.Ink, fontSize = 24.sp,
                 fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(6.dp))
            Text(
                message ?: "Touch the sensor to open it.",
                color = ThunderInk.Mute, fontSize = 15.sp, lineHeight = 21.sp,
                textAlign = TextAlign.Center
            )
            Spacer(Modifier.height(40.dp))
            Box(
                Modifier
                    .size(76.dp)
                    .clip(CircleShape)
                    .background(ThunderInk.GoldSoft)
                    .clickable(onClick = onUnlock),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Outlined.Fingerprint, contentDescription = "Unlock with fingerprint",
                     tint = ThunderInk.Gold, modifier = Modifier.size(40.dp))
            }
            Spacer(Modifier.height(12.dp))
            Text("Tap to unlock", color = ThunderInk.Mute, fontSize = 13.sp)
        }
    }
}
