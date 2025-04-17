import {createRouter, createWebHistory} from "vue-router";

const routes = [
    {
        path: "/home",
        component: () => import("@/views/home/index.vue"),
    },
    {
        path: "/",
        redirect: "/home",
    },
    {
        path: "/:pathMatch(.*)*",
        component: () => import("@/views/error/404.vue"),
    },
];
const router = createRouter({
    history: createWebHistory(),
    routes,
});
router.beforeEach(async (to, from, next) => {
    next();
});
router.afterEach((to, from, next) => {

});
export default router;
