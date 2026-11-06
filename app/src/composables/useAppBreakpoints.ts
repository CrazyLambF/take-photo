import { useBreakpoints } from '@vueuse/core'

/** 断点常量唯一来源（§3.3）：CSS 媒体查询与 JS 共享同一数值 */
export const BREAKPOINTS = { mobile: 0, tablet: 768, desktop: 1200 } as const

export function useAppBreakpoints() {
  const bp = useBreakpoints(BREAKPOINTS)
  return {
    bp,
    /** < 768px：底部 Tabbar 形态 */
    isMobile: bp.smaller('tablet'),
    /** ≥ 1200px：桌面增强（侧栏常驻、双栏详情） */
    isDesktop: bp.greaterOrEqual('desktop'),
  }
}
