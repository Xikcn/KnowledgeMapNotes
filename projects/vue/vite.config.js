import {defineConfig, loadEnv} from 'vite'
import path from 'path'
import createVitePlugins from "./vite/plugins/index.js";

// https://vite.dev/config/
export default defineConfig(({mode, command}) => {
    const env = loadEnv(mode, process.cwd());
    return {
        plugins: createVitePlugins(env, command === 'build'),
        server: {
            open: true,
            port: 80,
            proxy: {
                '/api': {
                    target: 'http://127.0.0.1:8000',
                    changeOrigin: true,
                    rewrite: (path) => path.replace(/^\/api/, '')
                }
            }
        },
        resolve: {
            alias: {
                "@": path.resolve(__dirname, "./src")
            }
        }
    }
})
