import vue from '@vitejs/plugin-vue'
import createSvgIcon from './svgIcon.js'


export default function createVitePlugins(viteEnv, isBuild = false) {
    const vitePlugins = [vue()]
    vitePlugins.push(createSvgIcon(isBuild))
    return vitePlugins
}