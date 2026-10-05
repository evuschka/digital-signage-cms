<script setup>
import { inject, computed } from 'vue';

const auth = inject('auth');
const media = inject('media');
const users = inject('users');
const schedules = inject('schedules');
const { formatSize } = inject('helpers');
const { isAdmin, isModerator, isRegional } = inject('roles');

const props = defineProps({
    currentTab: String
});

const emit = defineEmits(['switchTab', 'requestConfirm', 'logout']);

const roleName = computed(() => {
    if (isAdmin.value) return 'Администратор';
    if (isModerator.value) return 'Модератор';
    return 'Рег. пользователь';
});
</script>

<template>
<aside class="w-64 bg-emerald-50 border-r border-emerald-200 flex flex-col hidden md:flex h-full relative z-20">
    <div class="p-4 border-b border-emerald-200 text-left">
        
        <!-- Обновленный логотип с авто-высотой и адаптивной шириной -->
        <svg class="w-full h-auto max-w-full mb-4" viewBox="0 0 1144 320" fill="none" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
            <rect width="1144" height="320" fill="url(#pattern0_684_2)"/>
            <defs>
                <pattern id="pattern0_684_2" patternContentUnits="objectBoundingBox" width="1" height="1">
                    <use xlink:href="#image0_684_2" transform="matrix(0.00333333 0 0 0.0119167 0 -1.27969)"/>
                </pattern>
                <image id="image0_684_2" width="300" height="300" preserveAspectRatio="none" xlink:href="data:image/png;base64,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"/>
            </defs>
        </svg>

        <p class="text-emerald-700 text-xs mt-1 font-bold tracking-wide uppercase">{{ roleName }}</p>
    </div>
    
    <nav class="flex-1 p-4 space-y-2 overflow-y-auto pb-12">
        
        <!-- ВКЛАДКИ РЕГИОНАЛА -->
        <template v-if="isRegional">
            <a href="#" @click.prevent="emit('switchTab', 'broadcasts')" :class="currentTab === 'broadcasts' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm flex items-center justify-between">
                <span>▶ Трансляции</span>
                <span v-if="schedules.schedules.value.some(s => s.status === 'Активен')" class="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
            </a>
            <a href="#" @click.prevent="emit('switchTab', 'media')" :class="currentTab === 'media' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📁 Медиатека</a>
            <a href="#" @click.prevent="emit('switchTab', 'playlists')" :class="currentTab === 'playlists' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📑 Плейлисты</a>
            <a href="#" @click.prevent="emit('switchTab', 'import')" :class="currentTab === 'import' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📥 Импорт файлов</a>
            <a href="#" @click.prevent="emit('switchTab', 'schedule')" :class="currentTab === 'schedule' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📅 Расписания</a>
        </template>

        <!-- ВКЛАДКИ МОДЕРАТОРА -->
        <template v-if="isModerator">
            <a href="#" @click.prevent="emit('switchTab', 'media')" :class="currentTab === 'media' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">🛡️ Модерация контента</a>
        </template>

        <!-- ВКЛАДКИ АДМИНИСТРАТОРА -->
        <template v-if="isAdmin">
            <a href="#" @click.prevent="emit('switchTab', 'media')" :class="currentTab === 'media' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📁 Медиатека</a>
            <a href="#" @click.prevent="emit('switchTab', 'playlists')" :class="currentTab === 'playlists' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📑 Плейлисты</a>
            <a href="#" @click.prevent="emit('switchTab', 'import')" :class="currentTab === 'import' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📥 Импорт файлов</a>
            <a href="#" @click.prevent="emit('switchTab', 'schedule')" :class="currentTab === 'schedule' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📅 Расписания</a>
            <a href="#" @click.prevent="emit('switchTab', 'trash')" :class="currentTab === 'trash' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">🗑 Корзина</a>
            <a href="#" @click.prevent="emit('switchTab', 'monitoring')" :class="currentTab === 'monitoring' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">🖥️ Мониторинг сети</a>
            <a href="#" @click.prevent="emit('switchTab', 'reports')" :class="currentTab === 'reports' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">📊 Отчёты</a>
            <a href="#" @click.prevent="emit('switchTab', 'users')" :class="currentTab === 'users' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm">👥 Пользователи <span v-if="users.adminRequests.value.length > 0" class="bg-red-500 text-white text-[10px] px-1.5 py-0.5 rounded-full ml-1">{{ users.adminRequests.value.length }}</span></a>
        </template>
        
        <!-- Доступно всем -->
        <a href="#" @click.prevent="emit('switchTab', 'profile')" :class="currentTab === 'profile' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-emerald-900 hover:bg-emerald-100/60'" class="block w-full text-left px-4 py-2 rounded-lg transition text-sm border-t border-emerald-200 mt-2 pt-2">👤 Профиль</a>
    </nav>
    
    <div class="p-4 border-t border-emerald-200 bg-emerald-100/40 text-left bg-emerald-50">
        <div class="mb-4" v-if="!isModerator">
            <p class="text-xs text-emerald-800 font-semibold mb-1 flex justify-between"><span>Хранилище</span><span>{{ media.storageStats.value.percent }}%</span></p>
            <div class="w-full bg-emerald-200 rounded-full h-1.5 mb-1">
                <div :class="media.storageStats.value.percent > 90 ? 'bg-red-500' : 'bg-emerald-500'" class="h-1.5 rounded-full" :style="{ width: media.storageStats.value.percent + '%' }"></div>
            </div>
            <p class="text-[10px] text-emerald-600">{{ formatSize(media.storageStats.value.used) }} из 100 ГБ</p>
        </div>
        <button @click="emit('requestConfirm', $event, 'Вы действительно хотите выйти из системы?', () => emit('logout'))" class="w-full bg-red-100 hover:bg-red-200 text-red-800 border border-red-300 px-4 py-2 rounded-lg text-sm transition font-medium text-center cursor-pointer border-0">Выйти</button>
    </div>
</aside>
</template>