<script setup>
import { ref, computed, onUnmounted } from 'vue';

const props = defineProps({
    playlists: Object,
    media: Object,
    helpers: Object,
    requestConfirm: Function,
    auth: Object
});

const isModalOpen = ref(false);

const newPlaylistForm = ref({
    name: '',
    city: 'global',
    interval: 3,
    repeats: 1,
    items: []
});

const previewPlaylist = ref(null);
const previewIndex = ref(0);
let previewTimer = null;

const playlistList = computed(() => {
    if (!props.playlists) return [];
    return props.playlists.playlists?.value ?? props.playlists.playlists ?? [];
});

const availableFiles = computed(() => {
    if (!props.media) return [];
    return props.media.files?.value ?? props.media.files ?? [];
});

const currentSlide = computed(() => {
    if (!previewPlaylist.value || !previewPlaylist.value.items || !previewPlaylist.value.items.length) return null;
    return previewPlaylist.value.items[previewIndex.value];
});

const getFileUrl = (fileName) => {
    if (!fileName) return '';
    const parts = fileName.split('/');
    const encodedParts = parts.map(p => encodeURIComponent(p));
    return `http://localhost:8000/media-file/${encodedParts.join('/')}`;
};

const addItem = (fileName) => {
    if (!fileName) return;
    newPlaylistForm.value.items.push({
        file: fileName,
        duration: 10
    });
};

const removeItem = (idx) => {
    newPlaylistForm.value.items.splice(idx, 1);
};

const handleSavePlaylist = async () => {
    if (!newPlaylistForm.value.name.trim()) return;
    if (newPlaylistForm.value.items.length === 0) return;

    if (props.playlists?.newPlaylist) {
        const target = props.playlists.newPlaylist.value ?? props.playlists.newPlaylist;
        Object.assign(target, newPlaylistForm.value);
    }

    await props.playlists.createPlaylist();
    
    isModalOpen.value = false;
    newPlaylistForm.value = {
        name: '',
        city: 'global',
        interval: 3,
        repeats: 1,
        items: []
    };
};

const startPreview = (pl) => {
    if (!pl.items || pl.items.length === 0) return;
    previewPlaylist.value = pl;
    previewIndex.value = 0;
    runSlide();
};

const runSlide = () => {
    clearTimeout(previewTimer);
    if (!previewPlaylist.value) return;

    const item = previewPlaylist.value.items[previewIndex.value];
    const duration = ((item && item.duration) || 5) * 1000;

    previewTimer = setTimeout(() => {
        if (!previewPlaylist.value) return;
        previewIndex.value = (previewIndex.value + 1) % previewPlaylist.value.items.length;
        runSlide();
    }, duration);
};

const closePreview = () => {
    clearTimeout(previewTimer);
    previewPlaylist.value = null;
    previewIndex.value = 0;
};

onUnmounted(() => {
    clearTimeout(previewTimer);
});
</script>

<template>
<div class="space-y-6 text-left font-sans">
    <div class="flex justify-between items-center">
        <div>
            <h2 class="text-xl font-bold text-emerald-900 m-0">Управление плейлистами (Фото/Видео ряды)</h2>
            <p class="text-xs text-emerald-700 mt-1">Группировка и настройка порядка проигрывания контента</p>
        </div>
        <button 
            type="button"
            @click="isModalOpen = true" 
            class="bg-emerald-600 hover:bg-emerald-700 text-white text-xs px-4 py-2 rounded-lg transition font-medium shadow-sm cursor-pointer border-0">
            + Создать плейлист
        </button>
    </div>

    <div v-if="playlistList.length === 0" class="bg-emerald-50/60 border border-emerald-200 rounded-xl p-8 text-center text-emerald-800 text-xs">
        Плейлисты еще не созданы.
    </div>

    <!-- Карточки плейлистов -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div v-for="pl in playlistList" :key="pl.id" class="bg-white border border-emerald-200 rounded-xl p-5 shadow-sm space-y-3">
            <div class="flex justify-between items-start">
                <div>
                    <h3 class="font-bold text-emerald-900 text-base m-0">{{ pl.name }}</h3>
                    <p class="text-xs text-emerald-600 mt-0.5 uppercase tracking-wide font-semibold text-[10px]">{{ pl.city }}</p>
                    <p class="text-[11px] text-gray-500 mt-0.5">Пауза: {{ pl.interval }} сек | Повторов: {{ pl.repeats }}</p>
                </div>
                <div class="flex gap-2">
                    <button @click="startPreview(pl)" class="text-emerald-700 hover:text-emerald-900 text-xs bg-emerald-50 border border-emerald-200 px-3 py-1 rounded cursor-pointer">
                        Предпросмотр
                    </button>
                    <button @click="props.requestConfirm($event, `Удалить плейлист '${pl.name}'?`, () => props.playlists.deletePlaylist(pl.id))" class="text-red-600 hover:text-red-800 text-xs border border-red-200 bg-red-50 px-2.5 py-1 rounded cursor-pointer">
                        Удалить
                    </button>
                </div>
            </div>

            <div class="bg-emerald-50/50 p-2.5 rounded-lg border border-emerald-100 max-h-40 overflow-y-auto space-y-1">
                <div v-for="(item, idx) in pl.items" :key="idx" class="flex justify-between text-xs py-1 border-b border-emerald-100/60 last:border-0">
                    <span class="truncate text-emerald-900 max-w-[220px]" :title="item.file">{{ idx + 1 }}. {{ item.file }}</span>
                    <span class="text-emerald-700 font-mono">{{ item.duration }} сек.</span>
                </div>
            </div>
        </div>
    </div>

    <!-- Модальное окно предпросмотра -->
    <div v-if="previewPlaylist" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-2xl max-w-2xl w-full overflow-hidden shadow-2xl border border-emerald-200">
            <div class="bg-emerald-800 text-white px-5 py-3 flex justify-between items-center">
                <h3 class="text-sm font-semibold m-0">Предпросмотр плейлиста: {{ previewPlaylist.name }}</h3>
                <button @click="closePreview" class="text-white hover:text-gray-200 font-bold text-lg bg-transparent border-0 cursor-pointer">✕</button>
            </div>

            <div class="w-full h-80 bg-black flex flex-col items-center justify-center relative">
                <template v-if="currentSlide">
                    <img 
                        v-if="props.helpers.isImage(currentSlide.file)" 
                        :src="getFileUrl(currentSlide.file)" 
                        class="max-h-full max-w-full object-contain block" 
                    />
                    <video 
                        v-else 
                        :src="getFileUrl(currentSlide.file)" 
                        autoplay 
                        controls
                        playsinline 
                        class="max-h-full max-w-full object-contain block">
                    </video>
                </template>

                <div class="absolute bottom-3 left-4 text-white/90 text-xs bg-black/60 px-3 py-1 rounded backdrop-blur-sm font-mono pointer-events-none">
                    Слайд {{ previewIndex + 1 }} из {{ previewPlaylist.items.length }} | Файл: {{ currentSlide?.file }}
                </div>
            </div>

            <div class="p-4 bg-gray-50 flex justify-between items-center border-t">
                <span class="text-xs text-gray-600">Эмуляция экрана вещания с учетом длительности слайдов</span>
                <button @click="closePreview" class="bg-gray-200 hover:bg-gray-300 text-gray-800 text-xs px-4 py-2 rounded-lg font-medium cursor-pointer border-0">
                    Закрыть предпросмотр
                </button>
            </div>
        </div>
    </div>

    <!-- Модальное окно создания плейлиста -->
    <div v-if="isModalOpen" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-2xl max-w-lg w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div class="flex justify-between items-center border-b pb-3 border-emerald-100">
                <h3 class="text-base font-bold text-emerald-900 m-0">Новый плейлист</h3>
                <button type="button" @click="isModalOpen = false" class="text-gray-400 hover:text-gray-600 font-bold bg-transparent border-0 cursor-pointer">✕</button>
            </div>

            <div>
                <label class="block text-xs font-medium text-emerald-900 mb-1">Название плейлиста:</label>
                <input v-model="newPlaylistForm.name" type="text" class="w-full px-3 py-2 bg-white text-emerald-950 border border-emerald-200 rounded-lg text-xs focus:outline-none focus:border-emerald-500" placeholder="Утренний эфир...">
            </div>

            <div class="grid grid-cols-3 gap-2">
                <div>
                    <label class="block text-[11px] font-medium text-emerald-900 mb-1">Город:</label>
                    <select v-model="newPlaylistForm.city" class="w-full px-2 py-1.5 bg-white text-emerald-950 border border-emerald-200 rounded-lg text-xs focus:outline-none focus:border-emerald-500">
                        <option value="global">global</option>
                        <option value="moscow">moscow</option>
                        <option value="spb">spb</option>
                        <option value="novocheboksarsk">novocheboksarsk</option>
                        <option value="yartsevo">yartsevo</option>
                        <option value="azov">azov</option>
                        <option value="orenburg">orenburg</option>
                        <option value="chernyakhovsk">chernyakhovsk</option>
                    </select>
                </div>
                <div>
                    <label class="block text-[11px] font-medium text-emerald-900 mb-1">Пауза (сек):</label>
                    <input v-model="newPlaylistForm.interval" type="number" class="w-full px-2 py-1.5 bg-white text-emerald-950 border border-emerald-200 rounded-lg text-xs focus:outline-none focus:border-emerald-500">
                </div>
                <div>
                    <label class="block text-[11px] font-medium text-emerald-900 mb-1">Повторы:</label>
                    <input v-model="newPlaylistForm.repeats" type="number" class="w-full px-2 py-1.5 bg-white text-emerald-950 border border-emerald-200 rounded-lg text-xs focus:outline-none focus:border-emerald-500">
                </div>
            </div>

            <div>
                <label class="block text-xs font-medium text-emerald-900 mb-1">Добавить файлы из медиатеки:</label>
                <select @change="(e) => { addItem(e.target.value); e.target.value = ''; }" class="w-full px-3 py-2 bg-white text-emerald-950 border border-emerald-200 rounded-lg text-xs focus:outline-none focus:border-emerald-500">
                    <option value="">-- Выберите файл для добавления --</option>
                    <option v-for="f in availableFiles" :key="f.name" :value="f.name">{{ f.name }}</option>
                </select>
            </div>

            <div class="space-y-1 max-h-36 overflow-y-auto">
                <div v-for="(item, idx) in newPlaylistForm.items" :key="idx" class="flex items-center gap-2 bg-emerald-50 p-2 rounded text-xs">
                    <span class="truncate flex-1 font-medium text-emerald-900">{{ item.file }}</span>
                    <input v-model.number="item.duration" type="number" class="w-14 px-1 py-0.5 bg-white text-emerald-950 border border-emerald-200 rounded text-center text-xs" title="Длительность показа в сек">
                    <span class="text-emerald-700">сек.</span>
                    <button type="button" @click="removeItem(idx)" class="text-red-500 hover:text-red-700 font-bold px-1 bg-transparent border-0 cursor-pointer">✕</button>
                </div>
            </div>

            <div class="flex justify-end gap-2 pt-3 border-t border-emerald-100">
                <button type="button" @click="isModalOpen = false" class="px-4 py-2 border border-emerald-200 rounded-lg text-xs font-medium bg-transparent text-emerald-900 cursor-pointer hover:bg-emerald-50">Отмена</button>
                <button type="button" @click="handleSavePlaylist" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-medium border-0 cursor-pointer shadow-sm">Сохранить</button>
            </div>
        </div>
    </div>
</div>
</template>