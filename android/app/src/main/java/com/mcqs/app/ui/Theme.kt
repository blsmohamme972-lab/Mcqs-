package com.mcqs.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

// Dark neon palette: ink background, pink→violet brand gradient, cyan for "revealed".
val Ink = Color(0xFF0B0B12)
val Panel = Color(0xFF15151F)
val Panel2 = Color(0xFF1E1E2B)
val Line = Color(0xFF2E2E42)
val Pink = Color(0xFFFF3D7F)
val Violet = Color(0xFF8B5CF6)
val Cyan = Color(0xFF22D3EE)
val Amber = Color(0xFFFBBF24)
val TextHi = Color(0xFFF2F2F7)
val TextLo = Color(0xFFA1A1B5)

val BrandGradient = Brush.linearGradient(listOf(Pink, Violet))
val CoolGradient = Brush.linearGradient(listOf(Violet, Cyan))

/** Occlusion colours: muted masks for the other regions, glowing pink for the one being asked. */
val MaskOther = Color(0xFF34344A)
val MaskTarget = Pink
val RevealOutline = Cyan
val CorrectGreen = Color(0xFF34D399)
val WrongRed = Color(0xFFF43F5E)

private val scheme = darkColorScheme(
    primary = Pink, onPrimary = Color.White,
    secondary = Violet, onSecondary = Color.White,
    tertiary = Cyan, onTertiary = Ink,
    background = Ink, onBackground = TextHi,
    surface = Ink, onSurface = TextHi,
    surfaceVariant = Panel2, onSurfaceVariant = TextLo,
    surfaceContainerLowest = Ink, surfaceContainerLow = Panel, surfaceContainer = Panel,
    surfaceContainerHigh = Panel2, surfaceContainerHighest = Panel2,
    outline = Line, outlineVariant = Color(0xFF23233A),
    secondaryContainer = Panel2, onSecondaryContainer = TextHi,
    error = WrongRed,
)

private val base = Typography()
private val typography = base.copy(
    headlineLarge = base.headlineLarge.copy(fontWeight = FontWeight.Black, letterSpacing = (-0.5).sp),
    headlineSmall = base.headlineSmall.copy(fontWeight = FontWeight.ExtraBold),
    titleLarge = base.titleLarge.copy(fontWeight = FontWeight.Bold),
    titleMedium = base.titleMedium.copy(fontWeight = FontWeight.SemiBold, lineHeight = 24.sp),
    labelLarge = base.labelLarge.copy(fontWeight = FontWeight.Bold),
)

@Composable
fun McqsTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = scheme, typography = typography) {
        // Default text colour outside Surfaces (Compose otherwise falls back to black).
        CompositionLocalProvider(LocalContentColor provides TextHi, content = content)
    }
}

/** Text filled with the brand gradient. */
fun TextStyle.brand() = copy(brush = BrandGradient)

/** Pill button filled with a gradient. */
@Composable
fun GradientButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    brush: Brush = BrandGradient,
    enabled: Boolean = true,
    contentPadding: PaddingValues = PaddingValues(horizontal = 22.dp, vertical = 12.dp),
    content: @Composable () -> Unit,
) {
    Box(
        modifier
            .alpha(if (enabled) 1f else 0.35f)
            .clip(RoundedCornerShape(50))
            .background(brush)
            .clickable(enabled = enabled, onClick = onClick)
            .padding(contentPadding),
        contentAlignment = Alignment.Center,
    ) { content() }
}
