<script setup lang="ts">
import { computed } from 'vue'
import { usePosesStore } from '@/stores/poses'
import {
  GEAR_LABELS, GEAR_OPTIONS, LIGHT_OPTIONS,
  type PoseFilters,
} from '@/composables/usePoseFilter'
import type { CategoryId } from '@/types/pose'

/**
 * 筛选面板：维度内 OR、维度间 AND（§5.3）。
 * 形态由父级控制（移动端抽屉 / 桌面侧栏），本组件只管选项与状态。
 */
const model = defineModel<PoseFilters>({ required: true })

const store = usePosesStore()

const categories = computed(() => store.categories)
const propOptions = computed(() => store.allProps)

function toggleIn<T>(arr: T[], v: T): T[] {
  return arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]
}

function setCategory(id: CategoryId | ''): void {
  model.value = { ...model.value, category: model.value.category === id ? '' : id }
}

function reset(): void {
  model.value = { category: '', light: [], difficulty: [], gear: [], props: [] }
}
</script>

<template>
  <div class="filter-panel">
    <section class="group">
      <h4>类别</h4>
      <div class="chips">
        <button
          type="button"
          class="chip"
          :class="{ on: model.category === '' }"
          @click="setCategory('')"
        >全部</button>
        <button
          v-for="c in categories"
          :key="c.id"
          type="button"
          class="chip"
          :class="{ on: model.category === c.id }"
          :aria-pressed="model.category === c.id"
          @click="setCategory(c.id)"
        >{{ c.name.split(' ·')[0] }}</button>
      </div>
    </section>

    <section class="group">
      <h4>光线</h4>
      <div class="chips">
        <button
          v-for="l in LIGHT_OPTIONS"
          :key="l"
          type="button"
          class="chip"
          :class="{ on: model.light.includes(l) }"
          :aria-pressed="model.light.includes(l)"
          @click="model = { ...model, light: toggleIn(model.light, l) }"
        >{{ l }}</button>
      </div>
    </section>

    <section class="group">
      <h4>难度</h4>
      <div class="chips">
        <button
          v-for="d in [1, 2, 3]"
          :key="d"
          type="button"
          class="chip"
          :class="{ on: model.difficulty.includes(d) }"
          :aria-pressed="model.difficulty.includes(d)"
          @click="model = { ...model, difficulty: toggleIn(model.difficulty, d) }"
        >{{ ['入门', '进阶', '挑战'][d - 1] }}</button>
      </div>
    </section>

    <section class="group">
      <h4>器材</h4>
      <div class="chips">
        <button
          v-for="g in GEAR_OPTIONS"
          :key="g"
          type="button"
          class="chip"
          :class="{ on: model.gear.includes(g) }"
          :aria-pressed="model.gear.includes(g)"
          @click="model = { ...model, gear: toggleIn(model.gear, g) }"
        >{{ GEAR_LABELS[g] }}</button>
      </div>
    </section>

    <section v-if="propOptions.length" class="group">
      <h4>道具</h4>
      <div class="chips">
        <button
          v-for="t in propOptions"
          :key="t"
          type="button"
          class="chip"
          :class="{ on: model.props.includes(t) }"
          :aria-pressed="model.props.includes(t)"
          @click="model = { ...model, props: toggleIn(model.props, t) }"
        >{{ t }}</button>
      </div>
    </section>

    <div class="actions">
      <button type="button" class="reset" @click="reset">重置</button>
    </div>
  </div>
</template>

<style scoped>
.filter-panel {
  display: grid;
  gap: var(--sp-5);
}

.group h4 {
  margin: 0 0 var(--sp-2);
  font-size: var(--fs-13);
  color: var(--c-ink-2);
  font-weight: 600;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
}

.chip {
  border: 1px solid var(--c-line);
  background: var(--c-surface);
  color: var(--c-ink-2);
  border-radius: var(--r-full);
  padding: 6px var(--sp-3);
  font-size: var(--fs-13);
  min-height: 32px;
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease-out);
}

.chip.on {
  background: var(--c-accent-soft);
  border-color: var(--c-accent);
  color: var(--c-accent-deep);
  font-weight: 600;
}

.actions {
  display: flex;
  justify-content: flex-end;
}

.reset {
  border: none;
  background: none;
  color: var(--c-ink-3);
  font-size: var(--fs-13);
  cursor: pointer;
  text-decoration: underline;
  min-height: 44px;
}
</style>
