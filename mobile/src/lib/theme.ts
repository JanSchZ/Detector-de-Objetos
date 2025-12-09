/**
 * VisionMind Mobile - Premium Theme
 */

export const colors = {
    // Base
    background: '#09090b',
    surface: '#18181b',
    surfaceElevated: '#27272a',

    // Text
    textPrimary: '#fafafa',
    textSecondary: '#a1a1aa',
    textMuted: '#71717a',

    // Brand
    primary: '#10b981',
    primaryLight: '#34d399',
    primaryDark: '#059669',

    // Accent
    accent: '#06b6d4',
    accentLight: '#22d3ee',

    // Status
    success: '#22c55e',
    warning: '#f59e0b',
    danger: '#ef4444',
    dangerLight: '#fca5a5',

    // Borders
    border: '#27272a',
    borderLight: '#3f3f46',

    // Gradients (as arrays for LinearGradient)
    gradientPrimary: ['#10b981', '#06b6d4'],
    gradientDanger: ['#ef4444', '#dc2626'],
    gradientDark: ['#18181b', '#09090b'],
};

export const spacing = {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    xxl: 48,
};

export const fontSize = {
    xs: 11,
    sm: 13,
    base: 15,
    lg: 17,
    xl: 20,
    xxl: 28,
    xxxl: 36,
};

export const borderRadius = {
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24,
    full: 9999,
};

export const shadows = {
    sm: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.2,
        shadowRadius: 2,
        elevation: 2,
    },
    md: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 8,
        elevation: 5,
    },
    lg: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.4,
        shadowRadius: 16,
        elevation: 10,
    },
};
