<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import { showToast } from 'vant'
import 'vant/es/toast/style'
import PageContainer from '@/components/layout/PageContainer.vue'
import CameraCard from '@/components/pose/CameraCard.vue'
import StepList from '@/components/pose/StepList.vue'
import TipsBlock from '@/components/pose/TipsBlock.vue'
import RecommendList from '@/components/pose/RecommendList.vue'
import PoseAnnotatedFigure from '@/components/pose/PoseAnnotatedFigure.vue'
import annotationsData from '@/data/pose-annotations.json'
import { usePosesStore } from '@/stores/poses'
import { useFavoritesStore } from '@/stores/favorites'
import { useCompareStore } from '@/stores/compare'
import { recommendPoses } from '@/lib/recommend'
import { asset, placeholder } from '@/utils/asset'
import type { PoseAnnotation, PoseAnnotationsData } from '@/types/pose'

/**
 * 姿势详情（§3.1 / §5.2）：图集四帧 → 机位卡 → 分步要点 → 避坑 → 小贴士 → 相关推荐
 * ＋底部操作栏（移动固定 / 桌面右栏 sticky，§3.3）。
 *
 * 图集四帧（2026-11-05 决议）：
 *   示例图（必有）/ 线稿示意（有 lineArt 才显示）/ 取景示意（CLOSE 类及无人物姿势）
 *   / 易错标注（有 annotation 才显示）。缺失一律诚实空态，不用占位图冒充。
 */
defineOptions({ name: 'PoseDetailView' })

const route = useRoute()
const store = usePosesStore()
const fav = useFavoritesStore()
const compare = useCompareStore()

const annotations = (annotationsData as unknown as PoseAnnotationsData).poses

const pose = computed(() => store.get(String(route.params.id)))

/** 当前姿势的标注（无则 undefined） */
const annotation = computed<PoseAnnotation | undefined>(() =>
  pose.value ? annotations[pose.value.id] : undefined,
)

/**
 * 专属取景示意的类目：CLOSE 特写画面里只有脸，画人体线稿语义不成立；
 * 依此用画框/三分线/裁切线表达"取景"而非"姿态"。
 */
const FRAMING_CATEGORIES = new Set(['CLOSE'])

/** 同类上一个/下一个（§3.2 详情左右滑切换的按钮等价实现） */
const neighbors = computed(() => {
  if (!pose.value) return { prev: undefined, next: undefined }
  const pool = store.byCategory(pose.value.category)
  const i = pool.findIndex((p) => p.id === pose.value?.id)
  return {
    prev: i > 0 ? pool[i - 1] : pool[pool.length - 1],
    next: i < pool.length - 1 ? pool[i + 1] : pool[0],
  }
})

const recommendations = computed(() =>
  pose.value ? recommendPoses(pose.value, store.all, { limit: 6 }) : [],
)

export type FrameKey = 'cover' | 'lineart' | 'framing' | 'annotation'

interface Frame {
  key: FrameKey
  label: string
  /** 图片地址（annotation/framing 帧复用封面） */
  src: string
  /** 空态提示文案（该帧内容尚未制作时提示，不显示假图） */
  empty?: string
}

/**
 * 四帧智能生成：
 * - 示例图恒有；封面缺失时才降级占位。
 * - 线稿示意：只在该姿势真有 lineArt 文件时给出；否则给空态说明。
 * - 取景示意：CLOSE 类（画面里只有脸）与无人物姿势才有意义。
 * - 易错标注：只在该姿势有 annotation 时出现。
 */
const frames = computed<Frame[]>(() => {
  const p = pose.value
  if (!p) return []
  const cover = p.images.cover ? asset(p.images.cover) : placeholder()
  const isFraming = FRAMING_CATEGORIES.has(p.category)
  const list: Frame[] = [{ key: 'cover', label: '示例图', src: cover }]

  if (isFraming) {
    // 特写类：用「取景示意」替代「线稿示意」，复用封面叠画框/三分线
    list.push({ key: 'framing', label: '取景示意', src: cover })
  } else if (p.images.lineArt) {
    list.push({ key: 'lineart', label: '线稿示意', src: asset(p.images.lineArt) })
  } else {
    list.push({
      key: 'lineart',
      label: '线稿示意',
      src: cover,
      empty: '这套线稿还在制作中 · 先看示例图，按机位卡与分步要点照样能拍',
    })
  }

  if (annotation.value) {
    list.push({ key: 'annotation', label: '易错标注', src: cover })
  }
  return list
})

const frame = shallowRef<FrameKey>('cover')
const active = computed<Frame | undefined>(() =>
  frames.value.find((f) => f.key === frame.value) ?? frames.value[0],
)

watch(() => route.params.id, () => {
  frame.value = 'cover'
  lightbox.value = false
})

/** 灯箱：用 van-popup 复用同一渲染组件，避免 ImagePreview 丢标注层 */
const lightbox = shallowRef(false)

function openLightbox(): void {
  if (active.value?.empty) {
    showToast('该帧内容制作中')
    return
  }
  lightbox.value = true
}

/** 取景示意：三分线 + 画框边距（CLOSE 类专用） */
const FRAME_LINES = [0.333, 0.667]

/** 操作栏 */
function onCompare(): void {
  if (!pose.value) return
  const r = compare.toggle(pose.value.id)
  if (r.full) showToast('对比最多选 3 个')
  else showToast(r.added ? `已加入对比（${compare.ids.length}/3）` : '已移出对比')
}

function onShare(): void {
  showToast('分享卡片即将上线')
}
</script>

<template>
  <PageContainer>
    <div v-if="pose" class="detail">
      <nav class="crumbs" aria-label="返回">
        <RouterLink to="/poses" class="back">‹ 姿势库</RouterLink>
        <span class="pid">{{ pose.id }}</span>
      </nav>

      <div class="layout">
        <section class="gallery-col" aria-label="图集">
          <div class="frames" role="tablist" aria-label="图集切换">
            <button
              v-for="f in frames"
              :key="f.key"
              type="button"
              role="tab"
              class="frame-tab"
              :class="{ on: frame === f.key }"
              :aria-selected="frame === f.key"
              @click="frame = f.key"
            >{{ f.label }}<i v-if="f.empty" class="dot" aria-hidden="true" /></button>
          </div>

          <!-- 诚实空态：该帧内容尚未制作，不用占位图冒充 -->
          <div v-if="active?.empty" class="stage-empty">
            <svg viewBox="0 0 24 24" width="34" height="34" aria-hidden="true">
              <path d="M4 6h16v12H4z" fill="none" stroke="currentColor" stroke-width="1.6" />
              <path d="M4 16l4.5-4.5 3 3L15 11l5 5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
            </svg>
            <p>{{ active.empty }}</p>
            <span class="stage-empty-hint">当前展示：示例图</span>
          </div>

          <!-- 易错标注帧：原图 + 矢量标注层 -->
          <PoseAnnotatedFigure
            v-else-if="frame === 'annotation' && annotation"
            class="stage-figure"
            :src="active!.src"
            :alt="`${pose.name} · 易错标注`"
            :annotation="annotation"
            @click="openLightbox"
          />

          <!-- 取景示意帧：封面 + 三分线 / 画框边距 -->
          <button
            v-else-if="frame === 'framing'"
            type="button"
            class="stage stage-framing"
            aria-label="点击放大取景示意"
            @click="openLightbox"
          >
            <img :src="active!.src" :alt="`${pose.name} · 取景示意`" width="720" height="960" decoding="async" />
            <svg class="framing-lines" viewBox="0 0 75 100" aria-hidden="true" preserveAspectRatio="none">
              <line
                v-for="y in FRAME_LINES"
                :key="`h${y}`"
                :x1="0"
                :x2="75"
                :y1="y * 100"
                :y2="y * 100"
                class="grid-line"
              />
              <line
                v-for="x in FRAME_LINES"
                :key="`v${x}`"
                :y1="0"
                :y2="100"
                :x1="x * 75"
                :x2="x * 75"
                class="grid-line"
              />
              <rect x="1.5" y="2" width="72" height="96" class="safe-area" />
            </svg>
          </button>

          <!-- 常规帧：示例图 / 线稿示意 -->
          <button v-else type="button" class="stage" aria-label="点击放大图片" @click="openLightbox">
            <img
              :src="active?.src"
              :alt="`${pose.name} · ${active?.label ?? ''}`"
              width="720"
              height="960"
              decoding="async"
            />
          </button>

          <p v-if="active?.key === 'framing'" class="frame-note">
            白色框 = 安全取景边界，虚线 = 三分构图线；特写类不画人体线稿，看画框与裁切位置。
          </p>
          <p v-else-if="active?.key === 'annotation'" class="frame-note">
            {{ annotation?.caption ?? '示例图 + 易错点标注' }}：图上是正确姿势，标注指出容易踩的坑。
          </p>
          <div class="neighbor">
            <RouterLink v-if="neighbors.prev" :to="`/poses/${neighbors.prev.id}`" class="nb">‹ {{ neighbors.prev.name }}</RouterLink>
            <RouterLink v-if="neighbors.next" :to="`/poses/${neighbors.next.id}`" class="nb">{{ neighbors.next.name }} ›</RouterLink>
          </div>
        </section>

        <section class="info-col">
          <header class="title">
            <h1>{{ pose.name }}</h1>
            <div class="meta">
              <span class="cat">{{ store.categoryName(pose.category) }}</span>
              <span class="diff">难度 {{ ['入门', '进阶', '挑战'][pose.difficulty - 1] }}</span>
              <span v-for="l in pose.light" :key="l" class="light">{{ l }}</span>
            </div>
          </header>

          <section aria-labelledby="cam-h" class="block">
            <h2 id="cam-h">机位卡</h2>
            <CameraCard :camera="pose.camera" />
          </section>

          <section aria-labelledby="step-h" class="block">
            <h2 id="step-h">分步要点</h2>
            <StepList :steps="pose.steps" />
          </section>

          <section aria-labelledby="miss-h" class="block">
            <h2 id="miss-h">避坑</h2>
            <ul class="mistakes">
              <li v-for="(m, i) in pose.mistakes" :key="i">✕ {{ m }}</li>
            </ul>
          </section>

          <TipsBlock :category="pose.category" />

          <section aria-labelledby="rec-h" class="block">
            <h2 id="rec-h">相关推荐</h2>
            <RecommendList :poses="recommendations" />
          </section>
        </section>
      </div>

      <!-- 操作栏：移动端底部固定；桌面端位于右栏末尾（CSS sticky） -->
      <div class="actions" role="toolbar" aria-label="操作">
        <button
          type="button"
          class="act"
          :class="{ on: fav.has(pose.id) }"
          :aria-pressed="fav.has(pose.id)"
          @click="fav.toggleFavorite(pose.id)"
        >{{ fav.has(pose.id) ? '♥ 已收藏' : '♡ 收藏' }}</button>
        <button type="button" class="act" @click="fav.inList(pose.id) ? showToast('已在清单中') : (fav.addToList(pose.id), showToast('已加入待拍清单'))">
          ＋ 清单
        </button>
        <button type="button" class="act" :class="{ on: compare.has(pose.id) }" @click="onCompare">
          {{ compare.has(pose.id) ? '✓ 已选对比' : '⇄ 对比' }}
        </button>
        <button type="button" class="act share" @click="onShare">分享</button>
      </div>
    </div>

    <div v-else class="missing">
      <p>没有找到这个姿势</p>
      <RouterLink to="/poses" class="back">回姿势库</RouterLink>
    </div>

    <!-- 灯箱：用 van-popup 复用同一渲染组件，标注层不丢（ImagePreview 只接图片 URL） -->
    <van-popup
      :show="lightbox"
      round
      closeable
      :style="{ width: 'min(560px, 94vw)', maxHeight: '92dvh', background: 'var(--c-bg)' }"
      @update:show="lightbox = $event"
    >
      <div v-if="pose && active" class="lightbox">
        <h3 class="lb-title">{{ pose.name }}<small>{{ active.label }}</small></h3>
        <PoseAnnotatedFigure
          v-if="active.key === 'annotation' && annotation"
          :src="active.src"
          :alt="`${pose.name} · 易错标注（放大）`"
          :annotation="annotation"
          enlarged
        />
        <img v-else :src="active.src" :alt="`${pose.name} · ${active.label}`" class="lb-img" />
      </div>
    </van-popup>
  </PageContainer>
</template>

<style scoped>
.detail {
  /* 移动端底部固定操作栏（~61px）悬浮在 Tabbar 之上，而 .app-main 只预留了
     Tabbar 高度 → 再让出一段，避免滚到底时「相关推荐」最后几像素被操作栏压住 */
  padding-bottom: var(--sp-6);
}

.crumbs {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--sp-3);
}

.back {
  color: var(--c-ink-2);
  text-decoration: none;
  font-size: var(--fs-14);
  min-height: 44px;
  display: inline-flex;
  align-items: center;
}

.pid {
  font-size: var(--fs-12);
  color: var(--c-ink-3);
  letter-spacing: .08em;
}

@media (min-width: 1200px) {
  .layout {
    display: grid;
    grid-template-columns: minmax(0, 58%) 1fr;
    gap: var(--sp-8);
    align-items: start;
  }

  .gallery-col {
    position: sticky;
    top: calc(var(--topnav-h) + var(--sp-4));
  }
}

.frames {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  margin-bottom: var(--sp-2);
}

.frame-tab {
  position: relative;
  border: 1px solid var(--c-line);
  background: var(--c-surface);
  border-radius: var(--r-full);
  padding: 4px var(--sp-3);
  font-size: var(--fs-12);
  color: var(--c-ink-2);
  min-height: 36px;
  cursor: pointer;
}

/* 制作中的帧：右上角小圆点提示，不打假图 */
.frame-tab .dot {
  position: absolute;
  top: 4px;
  right: 5px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--c-gold);
}

.frame-tab.on {
  background: var(--c-ink);
  color: var(--c-bg);
  border-color: var(--c-ink);
  font-weight: 600;
}

.stage {
  border: none;
  padding: 0;
  background: var(--c-bg-soft);
  border-radius: var(--r-lg);
  overflow: hidden;
  cursor: zoom-in;
  width: 100%;
  display: block;
}

.stage img {
  width: 100%;
  aspect-ratio: 3 / 4;
  object-fit: cover;
  display: block;
}

/* 取景示意：叠三分线与安全取景框 */
.stage-framing {
  position: relative;
}

.framing-lines {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.grid-line {
  stroke: color-mix(in srgb, #fff 72%, transparent);
  stroke-width: 0.32;
  stroke-dasharray: 1.6 1.2;
}

.safe-area {
  fill: none;
  stroke: color-mix(in srgb, #fff 88%, transparent);
  stroke-width: 0.5;
}

.stage-figure {
  cursor: zoom-in;
}

/* 诚实空态：缺内容时的说明卡，不出现假图 */
.stage-empty {
  aspect-ratio: 3 / 4;
  border-radius: var(--r-lg);
  background: var(--c-bg-soft);
  border: 1px dashed var(--c-line-strong);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--sp-3);
  padding: var(--sp-6);
  text-align: center;
  color: var(--c-ink-3);
}

.stage-empty p {
  margin: 0;
  font-size: var(--fs-13);
  line-height: 1.6;
  max-width: 24ch;
}

.stage-empty-hint {
  font-size: var(--fs-11);
  color: var(--c-ink-3);
  opacity: .8;
}

.frame-note {
  margin: var(--sp-2) 0 0;
  font-size: var(--fs-12);
  color: var(--c-ink-3);
  line-height: 1.6;
}

/* 灯箱内容 */
.lightbox {
  padding: var(--sp-4);
}

.lb-title {
  margin: 0 0 var(--sp-3);
  font-size: var(--fs-16);
  font-family: var(--font-serif);
}

.lb-title small {
  margin-left: var(--sp-2);
  font-size: var(--fs-12);
  font-family: var(--font-sans);
  color: var(--c-ink-3);
  font-weight: 400;
}

.lb-img {
  width: 100%;
  border-radius: var(--r-md);
  display: block;
}

.neighbor {
  display: flex;
  justify-content: space-between;
  gap: var(--sp-3);
  margin-top: var(--sp-3);
}

.nb {
  font-size: var(--fs-13);
  color: var(--c-ink-2);
  text-decoration: none;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
}

.title h1 {
  font-family: var(--font-serif);
  font-size: var(--fs-28);
  margin: 0 0 var(--sp-2);
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  margin-bottom: var(--sp-2);
}

.meta span {
  font-size: var(--fs-12);
  border-radius: var(--r-full);
  padding: 2px var(--sp-2);
  background: var(--c-bg-soft);
  color: var(--c-ink-2);
}

.meta .cat {
  background: var(--c-accent-soft);
  color: var(--c-accent-deep);
  font-weight: 600;
}

.block { margin-top: var(--sp-6); }

.block h2 {
  font-family: var(--font-serif);
  font-size: var(--fs-18);
  margin: 0 0 var(--sp-3);
}

.mistakes {
  list-style: none;
  margin: 0;
  padding: var(--sp-3) var(--sp-4);
  background: var(--c-danger-soft);
  border-radius: var(--r-md);
  display: grid;
  gap: var(--sp-2);
}

.mistakes li {
  color: var(--c-danger);
  font-size: var(--fs-14);
  line-height: 1.6;
}

.actions {
  position: fixed;
  inset-inline: 0;
  bottom: calc(var(--tabbar-h) + env(safe-area-inset-bottom));
  z-index: var(--z-drawer);
  display: flex;
  gap: var(--sp-2);
  padding: var(--sp-2) var(--sp-4);
  background: color-mix(in srgb, var(--c-surface) 92%, transparent);
  backdrop-filter: blur(10px);
  border-top: 1px solid var(--c-line);
}

@media (min-width: 768px) {
  .detail { padding-bottom: 0; }

  .actions {
    position: sticky;
    bottom: var(--sp-4);
    border: 1px solid var(--c-line);
    border-radius: var(--r-lg);
  }
}

.act {
  flex: 1;
  min-height: 44px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-full);
  background: var(--c-surface);
  color: var(--c-ink);
  font-size: var(--fs-13);
  cursor: pointer;
}

.act.on {
  background: var(--c-accent-soft);
  border-color: var(--c-accent);
  color: var(--c-accent-deep);
  font-weight: 700;
}

.act.share { flex: 0 0 72px; }

.missing {
  text-align: center;
  padding: var(--sp-16) 0;
  color: var(--c-ink-3);
}
</style>
