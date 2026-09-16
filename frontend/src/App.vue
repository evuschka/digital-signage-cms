<script setup>
import { ref, onMounted } from 'vue';
import { useAuth } from './composables/useAuth.js';
import { useHelpers } from './composables/useHelpers.js';
import { useMedia } from './composables/useMedia.js';
import { usePlaylists } from './composables/usePlaylists.js';
import { useSchedules } from './composables/useSchedules.js';
import { useUsers } from './composables/useUsers.js';
import { useReports } from './composables/useReports.js';

import TabProfile from './components/TabProfile.vue';
import TabMonitoring from './components/TabMonitoring.vue';
import TabImport from './components/TabImport.vue';
import TabTrash from './components/TabTrash.vue';
import TabUsers from './components/TabUsers.vue';
import TabMedia from './components/TabMedia.vue';
import TabPlaylists from './components/TabPlaylists.vue';
import TabSchedules from './components/TabSchedules.vue';
import TabReports from './components/TabReports.vue';

const helpers = useHelpers();
const toasts = ref([]); 
let toastIdCounter = 0;

const showToast = (message, type = 'info') => {
    const id = toastIdCounter++;
    toasts.value.push({ id, message, type });
    setTimeout(() => { toasts.value = toasts.value.filter(t => t.id !== id); }, 4500);
};

const safeJson = async (res) => {
    try { return await res.json(); } 
    catch (e) { return { detail: "Ошибка сервера" }; }
};

const confirmDialog = ref({ show: false, x: 0, y: 0, text: '', onConfirm: null, isBelow: false });
const requestConfirm = (e, text, callback) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const posX = rect.left + rect.width / 2;
    const isNearTop = rect.top < 120;
    const posY = isNearTop ? rect.bottom : rect.top;
    confirmDialog.value = { show: true, x: posX, y: posY, text: text, onConfirm: callback, isBelow: isNearTop };
};

const auth = useAuth();
const users = useUsers(auth.authHeader, showToast, safeJson);
const media = useMedia(auth.authHeader, auth.login, showToast, safeJson);
const playlists = usePlaylists(auth.authHeader, showToast, helpers.isImage, helpers.isVideo, safeJson, () => media.files.value);
const schedules = useSchedules(auth.authHeader, showToast, requestConfirm, safeJson);
const reports = useReports(auth.authHeader, showToast, safeJson);

const currentTab = ref('media');

const loadAllData = async () => {
    if (auth.login.value === 'admin_main') {
        await users.fetchAdminUsers();
        if (users.adminRequests.value.length > 0) auth.showAdminAlertModal.value = true;
    }
    media.fetchFiles(); 
    media.fetchStats(); 
    media.fetchTrash();
    schedules.fetchScreens(); 
    schedules.fetchSchedules(); 
    reports.fetchMonitoring(); 
    if (auth.login.value === 'admin_main') playlists.fetchPlaylists();
};

onMounted(async () => {
    if (auth.isAuthenticated.value) await loadAllData();
});

const authenticate = async () => {
    const success = await auth.doLogin();
    if (success) await loadAllData();
};

const logoutHandler = () => {
    auth.doLogout();
    media.files.value = []; 
    media.trashFiles.value = []; 
    schedules.schedules.value = []; 
    playlists.playlists.value = [];
    currentTab.value = 'media'; 
    auth.showAdminAlertModal.value = false;
};

const switchTab = (tab) => {
    currentTab.value = tab;
    if (tab === 'reports') { reports.fetchAnalytics(); reports.fetchHistory(); reports.fetchStorageHistory(); }
    if (tab === 'users') users.fetchAdminUsers();
    if (tab === 'playlists' && auth.login.value === 'admin_main') playlists.fetchPlaylists();
    if (tab === 'schedule' && auth.login.value === 'admin_main') playlists.fetchPlaylists();
};

const changePasswordHandler = () => auth.updatePassword(logoutHandler);
</script>

<template>
<div class="bg-white text-emerald-950 min-h-screen flex flex-col font-sans">
    <div class="flex h-screen overflow-hidden relative">
        
        <!-- Уведомления -->
        <div class="fixed top-6 right-6 z-[9999] flex flex-col gap-3 pointer-events-none">
            <transition-group enter-active-class="transition duration-300 ease-out transform" enter-from-class="opacity-0 translate-x-8" enter-to-class="opacity-100 translate-x-0" leave-active-class="transition duration-200 ease-in transform" leave-from-class="opacity-100 translate-x-0" leave-to-class="opacity-0 translate-x-8">
                <div v-for="toast in toasts" :key="toast.id" class="px-4 py-3 rounded-lg shadow-xl border flex items-center gap-3 w-80 pointer-events-auto backdrop-blur-sm" :class="{'bg-emerald-50/90 text-emerald-900 border-emerald-200': toast.type === 'success', 'bg-red-50/90 text-red-900 border-red-200': toast.type === 'error', 'bg-amber-50/90 text-amber-900 border-amber-200': toast.type === 'warning' || toast.type === 'info'}">
                    <span v-if="toast.type === 'success'" class="text-emerald-500 text-lg shrink-0">✅</span>
                    <span v-if="toast.type === 'error'" class="text-red-500 text-lg shrink-0">❌</span>
                    <span v-if="toast.type === 'warning' || toast.type === 'info'" class="text-amber-500 text-lg shrink-0">⚠️</span>
                    <p class="text-sm font-medium leading-tight">{{ toast.message }}</p>
                </div>
            </transition-group>
        </div>

        <!-- Экран авторизации -->
        <div v-if="!auth.isAuthenticated.value" class="w-full max-w-md mx-auto mt-16 bg-emerald-50 p-8 rounded-xl border border-emerald-200 shadow-xl self-start">
            <h2 class="text-2xl font-bold mb-6 text-emerald-800 text-center">Вход в систему</h2>
            <div v-if="!auth.isResetMode.value">
                <input v-model="auth.login.value" type="text" placeholder="Логин (например, user_msk)" class="w-full mb-4 px-4 py-2 bg-white border border-emerald-300 rounded text-emerald-950 focus:outline-none focus:border-emerald-600 text-sm">
                <input v-model="auth.password.value" type="password" @keyup.enter="authenticate" placeholder="Пароль" class="w-full mb-4 px-4 py-2 bg-white border border-emerald-300 rounded text-emerald-950 focus:outline-none focus:border-emerald-600 text-sm">
                <button @click="authenticate" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 rounded transition text-sm mb-3">Войти</button>
                <div class="text-center"><button @click="auth.isResetMode.value = true; auth.resetForm.value.success = ''" class="text-xs text-emerald-700 hover:underline">Забыли пароль?</button></div>
            </div>
            <div v-else class="space-y-3">
                <p class="text-xs text-emerald-800">Введите логин для отправки запроса:</p>
                <input v-model="auth.resetForm.value.username" type="text" placeholder="Ваш логин" class="w-full px-4 py-2 bg-white border border-emerald-300 rounded text-sm focus:outline-none focus:border-emerald-600">
                <button @click="auth.requestReset" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white py-2 rounded text-sm font-medium">Отправить запрос</button>
                <button @click="auth.isResetMode.value = false" class="w-full bg-emerald-200 hover:bg-emerald-300 text-emerald-900 py-2 rounded text-sm">Назад ко входу</button>
                <p v-if="auth.resetForm.value.success" class="text-xs text-emerald-700 bg-emerald-100 p-2 rounded mt-2 text-center">{{ auth.resetForm.value.success }}</p>
            </div>
            <p v-if="auth.authError.value" class="mt-4 text-red-600 text-xs text-center">{{ auth.authError.value }}</p>
        </div>

        <!-- Основной интерфейс -->
        <template v-else>
            
            <div v-if="auth.showAdminAlertModal.value && auth.login.value === 'admin_main'" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                <div class="bg-white p-6 rounded-xl max-w-md w-full border border-emerald-200 shadow-2xl text-center">
                    <div class="text-amber-600 text-3xl mb-2">🔔</div>
                    <h3 class="text-lg font-bold text-emerald-900 mb-2">Внимание, запросы сброса!</h3>
                    <div class="bg-amber-50 p-3 rounded mb-6 text-left max-h-32 overflow-y-auto border border-amber-200">
                        <div v-for="req in users.adminRequests.value" :key="req.username" class="text-xs text-amber-900 mb-1">• Пользователь: <span class="font-semibold">{{ req.username }}</span> ({{ req.time }})</div>
                    </div>
                    <button @click="auth.showAdminAlertModal.value = false; switchTab('users')" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white py-2 rounded text-sm font-medium">Перейти к управлению</button>
                </div>
            </div>

            <!-- Сайдбар (без лишней кнопки плеера) -->
            <aside class="w-64 bg-emerald-50 border-r border-emerald-200 flex flex-col hidden md:flex h-full">
                <div class="p-4 border-b border-emerald-200 text-left">
                    <h1 class="text-xl font-bold tracking-tight text-emerald-800">DS CMS</h1>
                    <p class="text-emerald-700 text-xs mt-1">Роль: {{ auth.login.value === 'admin_main' ? 'Администратор' : 'Рег. пользователь' }}</p>
                </div>
                <nav class="flex-1 p-4 space-y-2 overflow-y-auto">
                    <a href="#" @click.prevent="switchTab('media')" :class="currentTab === 'media' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📁 Медиатека</a>
                    <a href="#" v-if="auth.login.value === 'admin_main'" @click.prevent="switchTab('playlists')" :class="currentTab === 'playlists' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📑 Плейлисты</a>
                    <a href="#" v-if="auth.login.value === 'admin_main'" @click.prevent="switchTab('import')" :class="currentTab === 'import' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📥 Импорт файлов</a>
                    <a href="#" v-if="auth.login.value === 'admin_main'" @click.prevent="switchTab('trash')" :class="currentTab === 'trash' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">🗑️ Корзина</a>
                    <a href="#" @click.prevent="switchTab('schedule')" :class="currentTab === 'schedule' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📅 Расписания</a>
                    <a href="#" @click.prevent="switchTab('monitoring')" :class="currentTab === 'monitoring' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">🖥️ Мониторинг сети</a>
                    <a href="#" v-if="auth.login.value === 'admin_main'" @click.prevent="switchTab('reports')" :class="currentTab === 'reports' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📊 Отчёты</a>
                    <a href="#" v-if="auth.login.value === 'admin_main'" @click.prevent="switchTab('users')" :class="currentTab === 'users' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">👥 Пользователи <span v-if="users.adminRequests.value.length > 0" class="bg-red-500 text-white text-[10px] px-1.5 py-0.5 rounded-full ml-1">{{ users.adminRequests.value.length }}</span></a>
                    <a href="#" @click.prevent="switchTab('profile')" :class="currentTab === 'profile' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">👤 Профиль</a>
                </nav>
                <div class="p-4 border-t border-emerald-200 bg-emerald-100/40 text-left">
                    <div class="mb-4">
                        <p class="text-xs text-emerald-800 font-semibold mb-1 flex justify-between"><span>Хранилище</span><span>{{ media.storageStats.value.percent }}%</span></p>
                        <div class="w-full bg-emerald-200 rounded-full h-1.5 mb-1"><div :class="media.storageStats.value.percent > 90 ? 'bg-red-500' : 'bg-emerald-500'" class="h-1.5 rounded-full" :style="{ width: media.storageStats.value.percent + '%' }"></div></div>
                        <p class="text-[10px] text-emerald-600">{{ helpers.formatSize(media.storageStats.value.used) }} из 100 ГБ</p>
                    </div>
                    <button @click="requestConfirm($event, 'Вы действительно хотите выйти из системы?', logoutHandler)" class="w-full bg-red-100 hover:bg-red-200 text-red-800 border border-red-300 px-4 py-2 rounded-lg text-sm transition font-medium">Выйти</button>
                </div>
            </aside>

            <!-- Основной контент -->
            <main class="flex-1 p-8 overflow-y-auto bg-white h-full text-sm text-left">
                <TabMedia v-if="currentTab === 'media'" :media="media" :auth="auth" :helpers="helpers" :requestConfirm="requestConfirm" />
                <TabPlaylists v-if="currentTab === 'playlists' && auth.login.value === 'admin_main'" :playlists="playlists" :media="media" :helpers="helpers" :requestConfirm="requestConfirm" :auth="auth" />
                <TabImport v-if="currentTab === 'import' && auth.login.value === 'admin_main'" :media="media" />
                <TabTrash v-if="currentTab === 'trash' && auth.login.value === 'admin_main'" :media="media" :helpers="helpers" :requestConfirm="requestConfirm" :showToast="showToast" />
                <TabSchedules v-if="currentTab === 'schedule'" :schedules="schedules" :playlists="playlists" :media="media" :auth="auth" :requestConfirm="requestConfirm" />
                <TabMonitoring v-if="currentTab === 'monitoring'" :reports="reports" />
                <TabReports v-if="currentTab === 'reports' && auth.login.value === 'admin_main'" :reports="reports" :helpers="helpers" />
                <TabUsers v-if="currentTab === 'users' && auth.login.value === 'admin_main'" :users="users" :auth="auth" :requestConfirm="requestConfirm" />
                <TabProfile v-if="currentTab === 'profile'" :auth="auth" :changePasswordHandler="changePasswordHandler" />
            </main>
        </template>
        
        <!-- Диалог подтверждения -->
        <div v-if="confirmDialog.show" class="fixed inset-0 z-[100]" @click="confirmDialog.show = false"></div>
        <transition enter-active-class="transition duration-200 ease-out origin-bottom" enter-from-class="opacity-0 scale-90" enter-to-class="opacity-100 scale-100" leave-active-class="transition duration-150 ease-in origin-bottom" leave-from-class="opacity-100 scale-100" leave-to-class="opacity-0 scale-90">
            <div v-if="confirmDialog.show" :style="{ top: confirmDialog.y + 'px', left: confirmDialog.x + 'px' }" class="fixed z-[101] transform -translate-x-1/2" :class="confirmDialog.isBelow ? 'mt-[10px]' : '-translate-y-full mt-[-10px]'">
                <div class="bg-white border border-emerald-300 shadow-2xl rounded-xl p-4 w-64 relative">
                    <p class="text-sm font-medium text-emerald-900 text-center mb-4 relative z-10">{{ confirmDialog.text }}</p>
                    <div class="flex justify-center gap-3 relative z-10">
                        <button @click.stop="confirmDialog.onConfirm(); confirmDialog.show = false" class="bg-emerald-600 text-white text-xs px-5 py-2 rounded-md font-medium">Да</button>
                        <button @click.stop="confirmDialog.show = false" class="bg-red-50 text-red-700 text-xs px-5 py-2 rounded-md font-medium border border-red-200">Нет</button>
                    </div>
                </div>
            </div>
        </transition>

    </div>
</div>
</template>