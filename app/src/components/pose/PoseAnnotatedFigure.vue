<script setup lang="ts">
/**
 * 带标注的姿势封面：img + SVG 图元层 + HTML 标签层。
 *
 * 关键约束：
 * 1. 文字只走 HTML 绝对定位，不进 SVG —— viewBox 缩放会把 12px 文案压成 8px 糊字。
 * 2. viewBox 用 75×100（=3:4），单位两侧等长，箭头/刻度不会被拉伸变形。
 * 3. 容器固定 aspect-ratio 3/4，图片 absolute 铺满，首屏无布局位移（CLS=0）。
 * 4. <768px 只显示 ①②③ 序号徽标，标注全文落到图下列表。
 * 5. 模板里不对判别联合做窄化，全部用 computed 分组，规避 vue-tsc 收窄报错。
 */
import { computed } from 'vue'
import type {
  ArrowMark,
  HLineMark,
  PoseAnnotation,
  PoseMark,
  RectMark,
  RulerMark,
} from '@/types/pose'

const props = defineProps<{
  src: string
  alt: string
  annotation?: PoseAnnotation
  /** 灯箱放大态：隐藏图下列表（空间有限），标签层始终展开 */
  enlarged?: boolean
}>()

/** 归一化 → viewBox 单位（75 宽 / 100 高），保留 3 位小数避免浮点尾巴 */
const u = (n: number) => Math.round(n * 75 * 1000) / 1000
const v = (n: number) => Math.round(n * 100 * 1000) / 1000
/** 归一化 → CSS 百分比，两位小数 */
const pct = (n: number) => `${Math.round(n * 10000) / 100}%`

const marks = computed<PoseMark[]>(() => props.annotation?.marks ?? [])
const hasMarks = computed(() => marks.value.length > 0)

const rects = computed(() => marks.value.filter((m): m is RectMark => m.type === 'rect'))
const hlines = computed(() => marks.value.filter((m): m is HLineMark => m.type === 'hline'))
const rulers = computed(() => marks.value.filter((m): m is RulerMark => m.type === 'ruler'))

/** 构图参考线也先算成标量，模板里不做联合类型收窄 */
const axisXU = computed(() => {
  const g = props.annotation?.guides
  return g?.axisX === undefined ? null : u(g.axisX)
})
const horizonYV = computed(() => {
  const g = props.annotation?.guides
  return g?.horizonY === undefined ? null : v(g.horizonY)
})

/** 量尺画在右侧安全区，避开人物；刻度向左伸出 */
const RULER_X = 0.94
const TICK = 4

const rulerTicks = computed(() =>
  rulers.value.map((r) => {
    const step = (r.to - r.from) / Math.max(1, r.divisions)
    return {
      id: r.id,
      y: v(r.from),
      to: v(r.to),
      x: u(RULER_X),
      xTick: u(RULER_X - TICK / 75),
      ticks: Array.from({ length: r.divisions + 1 }, (_, i) => v(r.from + step * i)),
    }
  }),
)

/** 箭头：线 + 三角头一起算好。viewBox 单位等长（75×100），三角不会被拉伸 */
const arrowItems = computed(() =>
  marks.value
    .filter((m): m is ArrowMark => m.type === 'arrow')
    .map((a) => {
      const x1 = u(a.from[0])
      const y1 = v(a.from[1])
      const x2 = u(a.to[0])
      const y2 = v(a.to[1])
      const dx = x2 - x1
      const dy = y2 - y1
      const len = Math.hypot(dx, dy) || 1
      const ux = dx / len
      const uy = dy / len
      const head = Math.min(4.2, len * 0.45)
      const half = head * 0.46
      const bx = x2 - ux * head
      const by = y2 - uy * head
      return {
        id: a.id,
        tone: `tone-${a.tone ?? 'guide'}`,
        x1,
        y1,
        x2,
        y2,
        points: `${x2},${y2} ${Math.round((bx - uy * half) * 1000) / 1000},${
          Math.round((by + ux * half) * 1000) / 1000
        } ${Math.round((bx + uy * half) * 1000) / 1000},${Math.round((by - ux * half) * 1000) / 1000}`,
      }
    }),
)

interface LabelItem {
  id: string
  n: number
  text: string
  tone: string
  x: number
  y: number
}

/** 标签锚点：优先显式 labelAt，否则按图元类型取默认点 */
function anchorOf(m: PoseMark): [number, number] {
  if (m.labelAt) return m.labelAt
  switch (m.type) {
    case 'rect':
      return [m.x, m.y]
    case 'arrow':
      return m.to
    case 'hline':
      return [m.x1 ?? 0.02, m.y]
    case 'vline':
      return [m.x, m.y1 ?? 0.02]
    case 'circle':
      return [m.cx, m.cy - m.r]
    case 'ruler':
      return [0.02, (m.from + m.to) / 2]
    default:
      return [0.5, 0.5]
  }
}

const labels = computed<LabelItem[]>(() =>
  marks.value.map((m, i) => {
    const [x, y] = anchorOf(m)
    return { id: m.id, n: i + 1, text: m.label, tone: m.tone ?? 'guide', x, y }
  }),
)

const CIRCLED = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩', '⑪', '⑫']
const badgeChar = (n: number) => CIRCLED[n - 1] ?? String(n)
</script>

<template>
  <figure class="paf" :class="{ 'is-enlarged': props.enlarged }">
    <div class="paf-frame">
      <img class="paf-img" :src="props.src" :alt="props.alt" width="1728" height="2304" loading="lazy" decoding="async" />

      <template v-if="hasMarks">
        <svg class="paf-svg" viewBox="0 0 75 100" preserveAspectRatio="none" aria-hidden="true" focusable="false">
          <g v-if="axisXU !== null" class="guides">
            <line :x1="axisXU" y1="0" :x2="axisXU" y2="100" />
          </g>
          <g v-if="horizonYV !== null" class="guides">
            <line x1="0" :y1="horizonYV" x2="75" :y2="horizonYV" />
          </g>

          <g class="l-rect">
            <rect
              v-for="r in rects"
              :key="r.id"
              :x="u(r.x)"
              :y="v(r.y)"
              :width="u(r.w)"
              :height="v(r.h)"
              :rx="u(r.rx ?? 0.01)"
              :class="`tone-${r.tone ?? 'guide'}`"
            />
          </g>

          <g class="l-line">
            <line
              v-for="l in hlines"
              :key="l.id"
              :x1="u(l.x1 ?? 0)"
              :y1="v(l.y)"
              :x2="u(l.x2 ?? 1)"
              :y2="v(l.y)"
              :class="`tone-${l.tone ?? 'guide'}`"
            />
          </g>

          <g class="l-arrow">
            <template v-for="a in arrowItems" :key="a.id">
              <line :x1="a.x1" :y1="a.y1" :x2="a.x2" :y2="a.y2" :class="a.tone" />
              <polygon :points="a.points" :class="a.tone" />
            </template>
          </g>

          <g class="l-ruler">
            <template v-for="r in rulerTicks" :key="r.id">
              <line :x1="r.x" :y1="r.y" :x2="r.x" :y2="r.to" />
              <line
                v-for="(t, ti) in r.ticks"
                :key="`${r.id}-t${ti}`"
                :x1="r.x"
                :y1="t"
                :x2="r.xTick"
                :y2="t"
                :class="ti === 0 || ti === r.ticks.length - 1 ? 'tick-end' : ''"
              />
            </template>
          </g>
        </svg>

        <span
          v-for="l in labels"
          :key="`b-${l.id}`"
          class="paf-badge"
          :class="`tone-${l.tone}`"
          :style="{ left: pct(l.x), top: pct(l.y) }"
          aria-hidden="true"
          >{{ badgeChar(l.n) }}</span
        >

        <span
          v-for="l in labels"
          :key="`l-${l.id}`"
          class="paf-label"
          :class="`tone-${l.tone}`"
          :style="{ left: pct(l.x), top: pct(l.y) }"
        >
          <i class="idx" aria-hidden="true">{{ l.n }}</i>{{ l.text }}
        </span>
      </template>
    </div>

    <figcaption v-if="props.annotation?.caption" class="paf-caption">
      {{ props.annotation.caption }}
    </figcaption>

    <ol v-if="hasMarks && !props.enlarged" class="paf-list">
      <li v-for="l in labels" :key="`li-${l.id}`">{{ l.text }}</li>
    </ol>
  </figure>
</template>

<style scoped>
.paf {
  margin: 0;
  display: grid;
  gap: var(--sp-2);
}

.paf-frame {
  position: relative;
  aspect-ratio: 3 / 4;
  width: 100%;
  overflow: hidden;
  border-radius: var(--r-md, 14px);
  background: var(--c-surface-2);
  /* 容器自带比例，图片加载前后高度不变 */
  contain: layout paint;
}

.paf-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.paf-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.paf-svg line,
.paf-svg rect,
.paf-svg polygon {
  vector-effect: non-scaling-stroke;
  fill: none;
  stroke-width: 2;
  stroke-linecap: round;
}

.paf-svg rect {
  fill: color-mix(in srgb, var(--c-accent) 10%, transparent);
}

.paf-svg polygon {
  fill: currentColor;
  stroke: none;
}

.paf-svg .guides line {
  stroke: var(--c-line-strong);
  stroke-width: 1;
  stroke-dasharray: 5 5;
  opacity: 0.75;
}

.paf-svg .l-rect rect.tone-danger,
.paf-svg .l-line line.tone-danger,
.paf-svg .l-arrow line.tone-danger,
.paf-svg .l-arrow polygon.tone-danger {
  stroke: var(--c-accent-deep);
  color: var(--c-accent-deep);
}

.paf-svg .l-rect rect.tone-danger {
  fill: color-mix(in srgb, var(--c-accent) 16%, transparent);
}

.paf-svg .tone-guide {
  stroke: var(--c-ink);
  color: var(--c-ink);
  opacity: 0.9;
}

.paf-svg .l-ruler line {
  stroke: var(--c-ink-2);
  stroke-width: 1.5;
  opacity: 0.85;
}

.paf-svg .l-ruler line.tick-end {
  stroke-width: 2.5;
  opacity: 1;
}

.paf-label,
.paf-badge {
  position: absolute;
  transform: translate(-50%, -50%);
  max-width: 46%;
}

.paf-label {
  display: none;
  background: var(--c-surface);
  color: var(--c-ink);
  border: 1px solid var(--c-line);
  border-radius: var(--r-sm, 10px);
  padding: 5px 9px;
  font-size: var(--fs-12, 12px);
  line-height: 1.35;
  font-weight: 600;
  box-shadow: 0 2px 10px rgb(0 0 0 / 12%);
  white-space: normal;
}

.paf-label .idx {
  display: inline-grid;
  place-items: center;
  width: 15px;
  height: 15px;
  margin-right: 4px;
  border-radius: var(--r-full);
  background: var(--c-accent-soft);
  color: var(--c-accent-deep);
  font-style: normal;
  font-size: 10px;
  font-weight: 700;
  vertical-align: 1px;
}

.paf-label.tone-danger {
  border-color: color-mix(in srgb, var(--c-accent) 45%, var(--c-line));
}

.paf-badge {
  display: grid;
  place-items: center;
  min-width: 26px;
  height: 26px;
  padding: 0 4px;
  border-radius: var(--r-full);
  background: var(--c-surface);
  color: var(--c-ink);
  border: 1.5px solid var(--c-accent);
  font-size: 13px;
  font-weight: 700;
  line-height: 1;
  box-shadow: 0 2px 8px rgb(0 0 0 / 18%);
}

.paf-badge.tone-danger {
  border-color: var(--c-accent-deep);
  background: var(--c-accent-soft);
  color: var(--c-accent-deep);
}

.paf-caption {
  font-size: var(--fs-13, 13px);
  color: var(--c-ink-2);
  line-height: 1.5;
}

.paf-list {
  margin: 0;
  padding-left: 1.35em;
  display: grid;
  gap: 4px;
  font-size: var(--fs-13, 13px);
  line-height: 1.55;
  color: var(--c-ink-2);
}

@media (min-width: 768px) {
  .paf-label {
    display: block;
  }

  .paf-badge {
    display: none;
  }

  .paf-list {
    display: none;
  }
}

/* 灯箱放大态：无论视口都展开全文标签，徽标仅作编号没意义 */
.paf.is-enlarged .paf-label {
  display: block;
}

.paf.is-enlarged .paf-badge {
  display: none;
}
</style>
