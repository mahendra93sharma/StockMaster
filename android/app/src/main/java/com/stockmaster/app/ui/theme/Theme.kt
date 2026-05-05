package com.stockmaster.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

// Design System Colors from Stitch
object StockMasterColors {
    // Primary
    val Primary = Color(0xFF000666)
    val OnPrimary = Color(0xFFFFFFFF)
    val PrimaryContainer = Color(0xFF1A237E)
    val OnPrimaryContainer = Color(0xFF8690EE)
    val InversePrimary = Color(0xFFBDC2FF)

    // Secondary (Teal)
    val Secondary = Color(0xFF006A6A)
    val OnSecondary = Color(0xFFFFFFFF)
    val SecondaryContainer = Color(0xFF90EFEF)
    val OnSecondaryContainer = Color(0xFF006E6E)

    // Tertiary
    val Tertiary = Color(0xFF380B00)
    val OnTertiary = Color(0xFFFFFFFF)
    val TertiaryContainer = Color(0xFF5C1800)
    val OnTertiaryContainer = Color(0xFFE17C5A)

    // Surface
    val Surface = Color(0xFFFBF8FF)
    val SurfaceDim = Color(0xFFDBD9E1)
    val SurfaceBright = Color(0xFFFBF8FF)
    val SurfaceContainerLowest = Color(0xFFFFFFFF)
    val SurfaceContainerLow = Color(0xFFF5F2FB)
    val SurfaceContainer = Color(0xFFEFECF5)
    val SurfaceContainerHigh = Color(0xFFEAE7EF)
    val SurfaceContainerHighest = Color(0xFFE4E1EA)
    val OnSurface = Color(0xFF1B1B21)
    val OnSurfaceVariant = Color(0xFF454652)
    val SurfaceVariant = Color(0xFFE4E1EA)
    val SurfaceTint = Color(0xFF4C56AF)

    // Error
    val Error = Color(0xFFBA1A1A)
    val OnError = Color(0xFFFFFFFF)
    val ErrorContainer = Color(0xFFFFDAD6)
    val OnErrorContainer = Color(0xFF93000A)

    // Outline
    val Outline = Color(0xFF767683)
    val OutlineVariant = Color(0xFFC6C5D4)

    // Inverse
    val InverseSurface = Color(0xFF303036)
    val InverseOnSurface = Color(0xFFF2EFF8)

    // Semantic - Market colors
    val BuyGreen = Color(0xFF4CAF50)
    val SellRed = Color(0xFFF44336)
    val HoldOrange = Color(0xFFFF9800)
    val ProfitGreen = Color(0xFF2E7D32)
    val LossRed = Color(0xFFC62828)

    // Dark mode
    val DarkSurface = Color(0xFF121218)
    val DarkSurfaceContainer = Color(0xFF1E1E24)
    val DarkOnSurface = Color(0xFFE4E1EA)
}

private val LightColorScheme = lightColorScheme(
    primary = StockMasterColors.Primary,
    onPrimary = StockMasterColors.OnPrimary,
    primaryContainer = StockMasterColors.PrimaryContainer,
    onPrimaryContainer = StockMasterColors.OnPrimaryContainer,
    inversePrimary = StockMasterColors.InversePrimary,
    secondary = StockMasterColors.Secondary,
    onSecondary = StockMasterColors.OnSecondary,
    secondaryContainer = StockMasterColors.SecondaryContainer,
    onSecondaryContainer = StockMasterColors.OnSecondaryContainer,
    tertiary = StockMasterColors.Tertiary,
    onTertiary = StockMasterColors.OnTertiary,
    tertiaryContainer = StockMasterColors.TertiaryContainer,
    onTertiaryContainer = StockMasterColors.OnTertiaryContainer,
    surface = StockMasterColors.Surface,
    onSurface = StockMasterColors.OnSurface,
    onSurfaceVariant = StockMasterColors.OnSurfaceVariant,
    surfaceVariant = StockMasterColors.SurfaceVariant,
    error = StockMasterColors.Error,
    onError = StockMasterColors.OnError,
    errorContainer = StockMasterColors.ErrorContainer,
    onErrorContainer = StockMasterColors.OnErrorContainer,
    outline = StockMasterColors.Outline,
    outlineVariant = StockMasterColors.OutlineVariant,
    inverseSurface = StockMasterColors.InverseSurface,
    inverseOnSurface = StockMasterColors.InverseOnSurface,
    background = StockMasterColors.Surface,
    onBackground = StockMasterColors.OnSurface,
    surfaceTint = StockMasterColors.SurfaceTint,
)

private val DarkColorScheme = darkColorScheme(
    primary = StockMasterColors.InversePrimary,
    onPrimary = Color(0xFF1C2580),
    primaryContainer = Color(0xFF343D96),
    onPrimaryContainer = Color(0xFFE0E0FF),
    inversePrimary = StockMasterColors.Primary,
    secondary = Color(0xFF76D6D5),
    onSecondary = Color(0xFF003737),
    secondaryContainer = Color(0xFF004F4F),
    onSecondaryContainer = Color(0xFF93F2F2),
    tertiary = Color(0xFFFFB59D),
    onTertiary = Color(0xFF5C1800),
    tertiaryContainer = Color(0xFF7B2E12),
    onTertiaryContainer = Color(0xFFFFDBD0),
    surface = StockMasterColors.DarkSurface,
    onSurface = StockMasterColors.DarkOnSurface,
    onSurfaceVariant = Color(0xFFC6C5D4),
    surfaceVariant = Color(0xFF454652),
    error = Color(0xFFFFB4AB),
    onError = Color(0xFF690005),
    errorContainer = Color(0xFF93000A),
    onErrorContainer = Color(0xFFFFDAD6),
    outline = Color(0xFF908F9D),
    outlineVariant = Color(0xFF454652),
    inverseSurface = Color(0xFFE4E1EA),
    inverseOnSurface = Color(0xFF303036),
    background = StockMasterColors.DarkSurface,
    onBackground = StockMasterColors.DarkOnSurface,
    surfaceTint = Color(0xFFBDC2FF),
)

// Typography: Work Sans for headlines, Inter for body
private val WorkSans = FontFamily.Default // Fallback - would use Google Fonts in production
private val Inter = FontFamily.Default

private val StockMasterTypography = Typography(
    headlineLarge = TextStyle(
        fontFamily = WorkSans,
        fontWeight = FontWeight.SemiBold,
        fontSize = 32.sp,
        lineHeight = 40.sp,
        letterSpacing = (-0.02).sp,
    ),
    headlineMedium = TextStyle(
        fontFamily = WorkSans,
        fontWeight = FontWeight.SemiBold,
        fontSize = 24.sp,
        lineHeight = 32.sp,
    ),
    titleLarge = TextStyle(
        fontFamily = WorkSans,
        fontWeight = FontWeight.Medium,
        fontSize = 20.sp,
        lineHeight = 28.sp,
    ),
    titleMedium = TextStyle(
        fontFamily = Inter,
        fontWeight = FontWeight.Bold,
        fontSize = 18.sp,
        lineHeight = 24.sp,
        letterSpacing = 0.05.sp,
    ),
    bodyLarge = TextStyle(
        fontFamily = Inter,
        fontWeight = FontWeight.Normal,
        fontSize = 16.sp,
        lineHeight = 24.sp,
    ),
    bodyMedium = TextStyle(
        fontFamily = Inter,
        fontWeight = FontWeight.Normal,
        fontSize = 14.sp,
        lineHeight = 20.sp,
    ),
    labelSmall = TextStyle(
        fontFamily = Inter,
        fontWeight = FontWeight.Medium,
        fontSize = 11.sp,
        lineHeight = 16.sp,
    ),
    labelMedium = TextStyle(
        fontFamily = Inter,
        fontWeight = FontWeight.Medium,
        fontSize = 12.sp,
        lineHeight = 16.sp,
    ),
    labelLarge = TextStyle(
        fontFamily = Inter,
        fontWeight = FontWeight.Medium,
        fontSize = 14.sp,
        lineHeight = 20.sp,
    ),
)

@Composable
fun StockMasterTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme

    MaterialTheme(
        colorScheme = colorScheme,
        typography = StockMasterTypography,
        content = content
    )
}
