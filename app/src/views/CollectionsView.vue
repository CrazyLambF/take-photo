<script setup lang="ts">
import { computed } from 'vue'
import PageContainer from '@/components/layout/PageContainer.vue'
import PoseWaterfall from '@/components/pose/PoseWaterfall.vue'
import { useFavoritesStore } from '@/stores/favorites'
import { usePosesStore } from '@/stores/poses'

/** 收藏与清单（§3.1）：默认「我的收藏」分组 ＋ 待拍清单（已拍打勾） */
const fav = useFavoritesStore()
const store = usePosesStore()

const favoritePoses = computed(() => fav.favorites.map((id) => store.get(id)).filter((p) => p !== undefined))
const listRows = computed(() => fav.list.map((r) => ({ ...r, pose: store.get(r.id) })))
const doneCount = computed(() => fav.list.filter((r) => r.done).length)
</script>

<template>
  <PageContainer>
    <header class="head">
      <h1>收藏与清单</h1>
      <span v-if="fav.list.length" class="count">清单完成度 {{ doneCount }}/{{ fav.list.length }}</span>
    </header>

    <section class="section" aria-labelledby="fav-h">
      <div class="sec-head"><h2 id="fav-h">我的收藏</h2><span class="n">{{ favoritePoses.length }}</span></div>
      <PoseWaterfall v-if="favoritePoses.length" :poses="favoritePoses" :finished="true" />
      <div v-else class="empty">
        <p>还没有收藏，去姿势库逛逛吧</p>
        <RouterLink to="/poses" class="cta">去姿势库</RouterLink>
      </div>
    </section>

    <section class="section" aria-labelledby="list-h">
      <div class="sec-head"><h2 id="list-h">待拍清单</h2><span class="n">{{ fav.list.length }}</span></div>
      <ul v-if="listRows.length" class="list">
        <li v-for="r in listRows" :key="r.id" :class="{ done: r.done }">
          <label class="check">
            <input type="checkbox" :checked="r.done" :aria-label="`标记 ${r.id} 已拍`" @change="fav.toggleDone(r.id)" />
            <span>{{ r.done ? '已拍' : '标记已拍' }}</span>
          </label>
          <RouterLink v-if="r.pose" :to="`/poses/${r.id}`" class="item-link">{{ r.pose.name }}<small>{{ r.id }}</small></RouterLink>
          <button type="button" class="rm" :aria-label="`从清单移除 ${r.id}`" @click="fav.removeFromList(r.id)">✕</button>
        </li>
      </ul>
      <p v-else class="empty-line">清单是空的 · 在详情页点「＋ 清单」把想拍的姿势存进来</p>
    </section>
  </PageContainer>
</template>
