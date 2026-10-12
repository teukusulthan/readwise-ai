/**
 * Unified icon renderer.
 *
 * Rule: Phosphor Web (CSS) is the ONLY allowed icon source in application code.
 * svg-code is a secondary option for custom/brand icons only —
 * never use it for user-supplied input (XSS risk).
 *
 * Usage:
 *   renderIcon({ icon: 'house' })                        → regular
 *   renderIcon({ icon: 'house', weight: 'fill' })        → fill
 *   renderIcon({ icon: 'house', weight: 'bold' })        → bold
 *
 * CSS weight class mapping:
 *   regular  → ph ph-{icon}
 *   fill     → ph-fill ph-{icon}
 *   bold     → ph-bold ph-{icon}
 *   light    → ph-light ph-{icon}
 *   duotone  → ph-duotone ph-{icon}
 */

import { cn } from '@/utils/cn'

// ─── Types ───────────────────────────────────────────────────────────────────

export type IconType = 'phosphor' | 'svg-code'
export type IconWeight = 'regular' | 'fill' | 'bold' | 'light' | 'duotone'

export interface RenderIconOptions {
  /** Phosphor icon slug, e.g. "house", "fire", "chart-line" */
  icon: string
  iconType?: IconType
  weight?: IconWeight
  size?: number
  className?: string
}

// ─── Weight → CSS class prefix ───────────────────────────────────────────────

const WEIGHT_CLASS: Record<IconWeight, string> = {
  regular:  'ph',
  fill:     'ph-fill',
  bold:     'ph-bold',
  light:    'ph-light',
  duotone:  'ph-duotone',
}

// ─── Renderer ────────────────────────────────────────────────────────────────

export function renderIcon({
  icon,
  iconType = 'phosphor',
  weight = 'regular',
  size,
  className,
}: RenderIconOptions): React.ReactElement | null {
  if (iconType === 'svg-code') {
    // Only use with trusted internal SVG strings — never render user input here.
    return (
      <span
        role="img"
        aria-hidden="true"
        className={className}
        style={size ? { width: size, height: size, display: 'inline-flex', alignItems: 'center' } : undefined}
        dangerouslySetInnerHTML={{ __html: icon }}
      />
    )
  }

  // phosphor web — renders via CSS font
  const weightClass = WEIGHT_CLASS[weight] ?? 'ph'
  return (
    <i
      className={cn(weightClass, `ph-${icon}`, className)}
      style={size ? { fontSize: size } : undefined}
      aria-hidden="true"
    />
  )
}
