<script setup>
import { inject, computed, ref } from 'vue';

const media = inject('media');
const getFileUrl = inject('getFileUrl');
const { formatSize, formatDate, isImage, isVideo } = inject('helpers');
const { isAdmin, isModerator } = inject('roles');

const emit = defineEmits(['requestConfirm']);

// Модератор по умолчанию видит только файлы на проверке
const statusFilter = ref(isModerator.value ? 'pending' : 'all');

const displayFiles = computed(() => {
    let list = media.filteredAndSortedFiles.value;
    if (statusFilter.value !== 'all') {
        list = list.filter(f => f.status === statusFilter.value);
    }
    return list;
});
</script>

<template>
<section class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm">
    <div class="flex justify-between items-center mb-6">
        <h2 class="text-xl font-semibold text-emerald-900">{{ isModerator ? 'Модерация контента' : 'Медиатека' }}</h2>
        <button @click="media.fetchFiles(); media.fetchStats()" class="text-xs bg-emerald-200 hover:bg-emerald-300 text-emerald-900 px-3 py-1.5 rounded-md font-medium cursor-pointer border-0">Обновить</button>
    </div>
    
    <div class="flex flex-col md:flex-row gap-3 mb-6 bg-white p-4 rounded-lg border border-emerald-200 shadow-sm">
        <input v-model="media.searchQuery.value" type="text" placeholder="Поиск по имени файла..." class="flex-1 bg-white text-emerald-950 border border-emerald-300 rounded-lg p-2 text-sm focus:outline-none focus:border-emerald-600">
        
        <select v-model="statusFilter" class="w-full md:w-48 bg-white text-emerald-950 border border-emerald-300 rounded-lg p-2 text-sm focus:outline-none focus:border-emerald-600">
            <option value="all">Все статусы</option>
            <option value="pending">⏳ На проверке</option>
            <option value="approved">✅ Одобрено</option>
            <option value="rejected">❌ Отклонено</option>
        </select>

        <select v-model="media.filterCity.value" class="w-full md:w-48 bg-white text-emerald-950 border border-emerald-300 rounded-lg p-2 text-sm focus:outline-none focus:border-emerald-600">
            <option value="all">Все папки офисов</option>
            <option value="global">Глобальная (global)</option>
            <option value="moscow">Москва</option>
            <option value="spb">Санкт-Петербург</option>
            <option value="novocheboksarsk">Новочебоксарск</option>
            <option value="yartsevo">Ярцево</option>
            <option value="azov">Азов</option>
            <option value="orenburg">Оренбург</option>
            <option value="chernyakhovsk">Черняховск</option>
        </select>
        <select v-model="media.sortBy.value" class="w-full md:w-56 bg-white text-emerald-950 border border-emerald-300 rounded-lg p-2 text-sm focus:outline-none focus:border-emerald-600">
            <option value="date_desc">Сначала новые</option>
            <option value="date_asc">Сначала старые</option>
            <option value="name_asc">По имени (А - Я)</option>
            <option value="name_desc">По имени (Я - А)</option>
            <option value="size_desc">Размер (большие сверху)</option>
            <option value="size_asc">Размер (маленькие сверху)</option>
        </select>
    </div>
    
    <div v-if="displayFiles.length === 0" class="text-center py-8 text-emerald-700 bg-white rounded-lg border border-dashed border-emerald-200">
        Контент не найден.
    </div>
    
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="file in displayFiles" :key="file.name" class="relative bg-white border border-emerald-200 p-4 rounded-lg flex flex-col gap-3 shadow-sm hover:shadow-md transition">
            
            <!-- Бейджик статуса модерации -->
            <div class="absolute top-2 right-2 flex gap-1 z-10">
                <span v-if="file.status === 'pending'" class="bg-amber-100 text-amber-800 text-[10px] px-2 py-1 rounded-full font-bold shadow-sm border border-amber-200">⏳ На проверке</span>
                <span v-else-if="file.status === 'approved'" class="bg-emerald-100 text-emerald-800 text-[10px] px-2 py-1 rounded-full font-bold shadow-sm border border-emerald-200">✅ Одобрено</span>
                <span v-else-if="file.status === 'rejected'" class="bg-red-100 text-red-800 text-[10px] px-2 py-1 rounded-full font-bold shadow-sm border border-red-200">❌ Отклонено</span>
            </div>

            <div class="flex items-center gap-3 mt-4">
                <div class="shrink-0 w-16 h-16 bg-slate-100 border border-emerald-100 rounded flex items-center justify-center overflow-hidden">
                    <img v-if="isImage(file.name)" :src="getFileUrl(file.name)" class="object-cover w-full h-full">
                    <video v-else-if="isVideo(file.name)" :src="getFileUrl(file.name)" class="object-cover w-full h-full" muted></video>
                    <span v-else class="text-xs font-bold text-emerald-400">ФАЙЛ</span>
                </div>
                <div class="overflow-hidden">
                    <p class="font-medium text-sm text-emerald-900 truncate" :title="file.name">{{ file.name }}</p>
                    <p class="text-[11px] text-emerald-600 mt-0.5">Размер: {{ formatSize(file.size) }}</p>
                    <p class="text-[11px] text-emerald-600">{{ formatDate(file.last_modified) }}</p>
                    <p class="text-[10px] text-slate-500 mt-0.5 font-medium">Автор: {{ file.uploaded_by || 'Неизвестен' }}</p>
                </div>
            </div>
            
            <div class="flex gap-2 mt-auto pt-2">
                <a :href="getFileUrl(file.name)" target="_blank" class="flex-1 text-center bg-emerald-100 hover:bg-emerald-200 text-emerald-800 text-xs px-3 py-1.5 rounded transition font-medium cursor-pointer">Смотреть</a>
                <!-- Модераторам удалять файлы нельзя -->
                <button v-if="!isModerator" @click="emit('requestConfirm', $event, 'Переместить файл в корзину?', () => media.deleteFile(file.name))" class="flex-1 bg-red-50 hover:bg-red-100 text-red-700 text-xs px-3 py-1.5 rounded border border-red-200 transition cursor-pointer">В корзину</button>
            </div>

            <!-- Кнопки модерации (Только для Админов/Модераторов и если файл на проверке) -->
            <div v-if="(isAdmin || isModerator) && file.status === 'pending'" class="flex gap-2 mt-2 pt-2 border-t border-emerald-100">
                <button @click="media.moderateFile(file.name, 'approve')" class="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white text-xs px-2 py-1.5 rounded transition cursor-pointer border-0 font-medium">✅ Допустить</button>
                <button @click="media.moderateFile(file.name, 'reject')" class="flex-1 bg-red-500 hover:bg-red-600 text-white text-xs px-2 py-1.5 rounded transition cursor-pointer border-0 font-medium">❌ Отклонить</button>
            </div>
            
        </div>
    </div>
</section>
</template>