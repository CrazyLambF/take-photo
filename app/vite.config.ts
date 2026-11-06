import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import Components from 'unplugin-vue-components/vite'
import { VantResolver } from '@vant/auto-import-resolver'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  // 部署基准路径。GitHub Pages 项目站点在 /<repo>/ 子路径下，
  // 由 CI 注入 VITE_BASE_PATH=/take-photo/；本地开发默认根路径。
  // 注意：路由用 createWebHistory(BASE_URL)，改这里会同时影响路由前缀。
  base: process.env.VITE_BASE_PATH || '/',
  plugins: [
    vue(),
    Components({
      resolvers: [VantResolver()],
      // 只为 Vant 原语做按需注册；业务组件显式 import，保持数据流可读
      include: [/\.vue$/, /\.vue\?vue/],
      dts: 'src/components.d.ts',
    }),
  ],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
    // 让 Vant auto-import 注入的 .css 走 Vite 管线（否则 node 加载器报 Unknown extension）
    css: true,
    // vant 是 external 依赖，其内部相对导入 .css 会逃出 Vite 管线 → 内联处理
    server: { deps: { inline: [/vant/] } },
  },
})
