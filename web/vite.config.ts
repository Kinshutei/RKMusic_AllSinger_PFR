import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const REPO_NAME = '/RKMusic_AllSinger_PFR/'

export default defineConfig({
  plugins: [react()],
  base: REPO_NAME,
  resolve: {
    alias: {
      'plotly.js/dist/plotly': 'plotly.js-dist-min',
    },
  },
})
