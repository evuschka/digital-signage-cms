<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
    media: Object,
    auth: Object,
    helpers: Object,
    requestConfirm: Function
});

const searchQuery = ref('');
const selectedFolder = ref('all');
const sortOrder = ref('new');

const filesList = computed(() => {
    let list = props.media?.files?.value ?? props.media?.files ?? [];
    
    // Поиск по имени
    if (searchQuery.value.trim()) {
        const q = searchQuery.value.toLowerCase();
        list = list.filter(f => f.name.toLowerCase().includes(q));
    }

    // Фильтр по папкам
    if (selectedFolder.value !== 'all') {
        list = list.filter(f => f.name.startsWith(selectedFolder.value + '/'));
    }

    return list;
});

const getFileUrl = (fileName) => {
    if (!fileName) return '';
    const parts = fileName.split('/');
    const encodedParts = parts.map(p => encodeURIComponent(p));
    return `http://localhost:8000/media-file/${encodedParts.join('/')}`;
};
</script>

<template>
<div class="space-y-6 text-left font-sans w-full">
    <!-- Верхняя панель управления и фильтров во всю ширину -->
    <div class="flex flex-col md:flex-row justify-between items-center gap-4 bg-white p-5 rounded-2xl border border-emerald-200 shadow-sm w-full">
        <h2 class="text-xl font-bold text-emerald-900 m-0">Интерфейс управления контентом</h2>
        
        <div class="flex items-center gap-3 w-full md:w-auto">
            <input 
                v-model="searchQuery" 
                type="text" 
                placeholder="Поиск по имени файла..." 
                class="px-3.5 py-2 bg-white text-emerald-950 border border-emerald-300 rounded-xl text-xs focus:outline-none focus:border-emerald-500 shadow-sm w-full md:w-64">

            <select v-model="selectedFolder" class="px-3 py-2 bg-white text-emerald-950 border border-emerald-300 rounded-xl text-xs focus:outline-none focus:border-emerald-500 shadow-sm">
                <option value="all">Все папки офисов</option>
                <option value="global">global</option>
                <option value="moscow">moscow</option>
                <option value="spb">spb</option>
                <option value="novocheboksarsk">novocheboksarsk</option>
                <option value="yartsevo">yartsevo</option>
                <option value="azov">azov</option>
                <option value="orenburg">orenburg</option>
                <option value="chernyakhovsk">chernyakhovsk</option>
            </select>

            <button @click="props.media.fetchFiles()" class="bg-emerald-600 hover:bg-emerald-700 text-white text-xs px-4 py-2 rounded-xl transition font-semibold shadow-sm cursor-pointer border-0 shrink-0">
                Обновить
            </button>
        </div>
    </div>

    <!-- Сетка карточек файлов на всю ширину -->
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-5 w-full">
        <div v-for="file in filesList" :key="file.name" class="bg-white border border-emerald-200 rounded-2xl p-4 shadow-sm flex flex-col justify-between space-y-3">
            <div class="w-full h-36 bg-emerald-50/70 rounded-xl overflow-hidden flex items-center justify-center border border-emerald-100 relative">
                <img 
                    v-if="props.helpers.isImage(file.name)" 
                    :src="getFileUrl(file.name)" 
                    class="w-full h-full object-cover" 
                />
                <video 
                    v-else-if="props.helpers.isVideo(file.name)" 
                    :src="getFileUrl(file.name)" 
                    class="w-full h-full object-cover">
                </video>
                <div v-else class="text-3xl">📄</div>
            </div>

            <div>
                <h3 class="font-bold text-emerald-950 text-xs truncate m-0" :title="file.name">{{ file.name }}</h3>
                <p class="text-[11px] text-emerald-700 mt-1">Размер: {{ props.helpers.formatSize(file.size) }}</p>
                <p class="text-[10px] text-gray-400 mt-0.5">{{ file.date }}</p>
            </div>

            <div class="flex gap-2 pt-2 border-t border-emerald-100">
                <a :href="getFileUrl(file.name)" target="_blank" class="flex-1 text-center text-emerald-700 hover:bg-emerald-50 text-xs py-1.5 rounded-xl border border-emerald-200 font-medium transition">
                    Смотреть
                </a>
                <button v-if="props.auth.login.value === 'admin_main'" @click="props.requestConfirm($event, `Удалить файл '${file.name}' в корзину?`, () => props.media.moveToTrash(file.name))" class="text-red-600 hover:bg-red-50 text-xs px-3 py-1.5 rounded-xl border border-red-200 font-medium transition bg-transparent cursor-pointer">
                    В корзину
                </button>
            </div>
        </div>
    </div>

    <div v-if="filesList.length === 0" class="bg-white border border-emerald-200 rounded-2xl p-12 text-center text-emerald-800 text-xs shadow-sm w-full">
        Медиафайлы не найдены.
    </div>
</div>
</template>