<script setup>
import { ref, onMounted, inject } from 'vue';

const { isImage, isVideo } = inject('helpers');
const getFileUrl = inject('getFileUrl');

const urlParams = new URLSearchParams(window.location.search);
const viewerId = urlParams.get('viewer_id');
const viewerHash = urlParams.get('hash');

const mobileData = ref(null);
const mobileError = ref('');
const mobileIndex = ref(0);
let mobileTimer = null;
const isMuted = ref(true);

const safeJson = async (res) => {
    try { return await res.json(); } catch (e) { return { detail: "Ошибка сервера" }; }
};

const loadMobileViewer = async () => {
    try {
        const res = await fetch(`/public-broadcast/${viewerId}?hash=${encodeURIComponent(viewerHash)}`);
        if (!res.ok) {
            const err = await safeJson(res);
            mobileError.value = err.detail || 'Доступ запрещен';
            return;
        }
        mobileData.value = await safeJson(res);
        playMobileItem();
    } catch (e) {
        mobileError.value = 'Ошибка подключения к эфиру';
    }
};

const playMobileItem = () => {
    if (!mobileData.value || !mobileData.value.items.length) return;
    const item = mobileData.value.items[mobileIndex.value];
    if (isImage(item.file)) {
        mobileTimer = setTimeout(nextMobileItem, (item.duration || 10) * 1000);
    }
};

const nextMobileItem = () => {
    mobileIndex.value = (mobileIndex.value + 1) % mobileData.value.items.length;
    playMobileItem();
};

onMounted(() => {
    loadMobileViewer();
});
</script>

<template>
    <div class="h-screen w-screen bg-black flex flex-col items-center justify-center text-white fixed inset-0 z-[99999]">
        <div v-if="mobileError" class="text-red-500 flex flex-col items-center gap-4 text-center px-6">
            <span class="text-6xl">🔒</span>
            <h2 class="text-xl font-bold">{{ mobileError }}</h2>
            <p class="text-sm text-gray-400">Попробуйте отсканировать код заново.</p>
        </div>
        <div v-else-if="!mobileData" class="animate-pulse text-emerald-400 flex flex-col items-center gap-3">
            <span class="text-4xl animate-spin">⏳</span>
            Подключение к эфиру...
        </div>
        <div v-else class="w-full h-full relative flex items-center justify-center" @click="isMuted = false">
            <video v-if="isVideo(mobileData.items[mobileIndex].file)" 
                   :src="getFileUrl(mobileData.items[mobileIndex].file)" 
                   autoplay :muted="isMuted" playsinline class="w-full h-full object-contain" 
                   @ended="nextMobileItem"></video>
                   
            <img v-else 
                 :src="getFileUrl(mobileData.items[mobileIndex].file)" 
                 class="w-full h-full object-contain">
                 
            <div v-if="isVideo(mobileData.items[mobileIndex].file) && isMuted" 
                 class="absolute bottom-16 bg-white/20 backdrop-blur-md px-5 py-3 rounded-full text-white text-xs font-bold tracking-wide border border-white/30 animate-bounce shadow-lg">
                👆 Коснитесь экрана, чтобы включить звук
            </div>
                 
            <div class="absolute top-4 left-4 bg-black/60 px-3 py-1 rounded-full text-[10px] uppercase font-bold flex items-center gap-2 tracking-widest backdrop-blur-md border border-white/10 pointer-events-none">
                <span class="w-2 h-2 rounded-full bg-red-500 animate-pulse shadow-[0_0_8px_rgba(239,68,68,1)]"></span>
                Прямой эфир
            </div>
        </div>
    </div>
</template>