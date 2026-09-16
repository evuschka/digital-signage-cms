<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';

const urlParams = new URLSearchParams(window.location.search);
const city = ref(urlParams.get('city') || 'moscow');

const currentItem = ref(null);
const mediaList = ref([]);
const currentIndex = ref(0);
const intervalTimer = ref(null);
const isVideoPlaying = ref(false);

const fetchActiveSchedule = async () => {
    try {
        const response = await fetch(`/api/schedules/active?city=${city.value}`);
        
        // Безопасная проверка: проверяем, что сервер вернул именно JSON, а не HTML-ошибку
        const contentType = response.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
            throw new Error("Сервер вернул не JSON (возможно, эндпоинт не найден)");
        }

        if (!response.ok) throw new Error('Ошибка загрузки расписания');
        const data = await response.json();
        
        if (data && data.items && data.items.length > 0) {
            mediaList.value = data.items;
            if (!currentItem.value) {
                currentIndex.value = 0;
                loadCurrentMedia();
            }
        } else {
            currentItem.value = { type: 'text', text: `Нет активного расписания для филиала: ${city.value.toUpperCase()}` };
        }
    } catch (e) {
        console.warn('Внимание: не удалось получить расписание, показываем заглушку плеера.', e);
        // Заглушка вместо падения в ошибку
        currentItem.value = { type: 'text', text: `Эмулятор плеера: ${city.value.toUpperCase()} (Ожидание данных расписания)` };
    }
};

const loadCurrentMedia = () => {
    if (mediaList.value.length === 0) return;
    if (currentIndex.value >= mediaList.value.length) {
        currentIndex.value = 0;
    }

    const item = mediaList.value[currentIndex.value];
    currentItem.value = item;

    const filename = item.file || item;
    const isVid = typeof filename === 'string' && (filename.endsWith('.mp4') || filename.endsWith('.webm') || filename.endsWith('.mov'));

    if (isVid) {
        isVideoPlaying.value = true;
    } else {
        isVideoPlaying.value = false;
        const duration = (item.duration || 10) * 1000;
        if (intervalTimer.value) clearTimeout(intervalTimer.value);
        intervalTimer.value = setTimeout(() => {
            nextSlide();
        }, duration);
    }
};

const nextSlide = () => {
    currentIndex.value++;
    loadCurrentMedia();
};

const handleVideoEnded = () => {
    nextSlide();
};

watch(city, () => {
    currentItem.value = null;
    if (intervalTimer.value) clearTimeout(intervalTimer.value);
    fetchActiveSchedule();
});

let heartbeatInterval = null;
const sendHeartbeat = async () => {
    try {
        await fetch('/api/monitoring/ping', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ screen: `player_${city.value}`, city: city.value, status: 'В сети' })
        });
    } catch (e) {}
};

onMounted(() => {
    fetchActiveSchedule();
    const scheduleInterval = setInterval(fetchActiveSchedule, 120000);
    heartbeatInterval = setInterval(sendHeartbeat, 30000);

    onUnmounted(() => {
        clearInterval(scheduleInterval);
        clearInterval(heartbeatInterval);
        if (intervalTimer.value) clearTimeout(intervalTimer.value);
    });
});

// Кнопка выхода из полноэкранного режима обратно в админку
const exitPlayer = () => {
    window.location.search = '';
};
</script>

<template>
    <div class="fixed inset-0 bg-black flex items-center justify-center overflow-hidden select-none z-50">
        
        <!-- Кнопка выхода -->
        <button @click="exitPlayer" class="absolute top-4 right-4 bg-red-600/80 hover:bg-red-600 text-white text-xs px-3 py-1.5 rounded-lg backdrop-blur-md z-50 transition shadow-lg cursor-pointer">
            ✕ Выйти из плеера
        </button>

        <!-- Контент экрана -->
        <div v-if="currentItem" class="w-full h-full flex items-center justify-center relative">
            
            <div v-if="currentItem.type === 'text'" class="text-white text-center p-8">
                <div class="text-6xl mb-4">📺</div>
                <h1 class="text-2xl font-light tracking-widest uppercase text-emerald-400">Digital Signage Kiosk</h1>
                <p class="text-lg text-gray-400 mt-2">{{ currentItem.text }}</p>
            </div>

            <img v-else-if="!isVideoPlaying" :src="`/uploads/${currentItem.file || currentItem}`" class="w-full h-full object-contain">

            <video 
                v-else 
                :src="`/uploads/${currentItem.file || currentItem}`" 
                autoplay 
                muted 
                playsinline
                @ended="handleVideoEnded"
                class="w-full h-full object-contain">
            </video>

            <!-- Панель выбора филиала (для тестирования) -->
            <div class="absolute top-4 left-4 bg-black/60 backdrop-blur-md p-2 rounded-lg flex items-center gap-3 border border-white/10 z-40">
                <span class="text-xs text-white/70 font-medium">Эмулятор экрана:</span>
                <select v-model="city" class="bg-emerald-900 text-white text-xs px-3 py-1.5 rounded border border-emerald-700 outline-none cursor-pointer">
                    <option value="global">Вся сеть (Global)</option>
                    <option value="moscow">Москва (3 экрана)</option>
                    <option value="spb">Санкт-Петербург (2 экрана)</option>
                    <option value="novocheboksarsk">Новочебоксарск</option>
                    <option value="yartsevo">Ярцево</option>
                    <option value="azov">Азов</option>
                    <option value="orenburg">Оренбург</option>
                    <option value="chernyakhovsk">Черняховск</option>
                </select>
            </div>

            <div class="absolute bottom-4 left-4 bg-black/50 backdrop-blur-md text-white/60 text-xs px-3 py-1.5 rounded z-40">
                Филиал: <span class="text-emerald-400 font-bold uppercase">{{ city }}</span> | Слайд: {{ currentIndex + 1 }}/{{ mediaList.length }}
            </div>
        </div>

        <div v-else class="text-gray-400 text-sm animate-pulse">
            Загрузка вещания...
        </div>
    </div>
</template>