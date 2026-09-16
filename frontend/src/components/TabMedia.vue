<script setup>
const props = defineProps(['media', 'auth', 'helpers', 'requestConfirm']);
const { fetchFiles, fetchStats, searchQuery, filterCity, sortBy, filteredAndSortedFiles, deleteFile } = props.media;
const { login } = props.auth;
const { isImage, isVideo, formatSize, formatDate } = props.helpers;
</script>

<template>
    <section class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm">
        <div class="flex justify-between items-center mb-6">
            <h2 class="text-xl font-semibold text-emerald-900">Интерфейс управления контентом</h2>
            <button @click="fetchFiles(); fetchStats()" class="text-xs bg-emerald-200 hover:bg-emerald-300 text-emerald-900 px-3 py-1.5 rounded-md font-medium">Обновить</button>
        </div>
        <div class="flex flex-col md:flex-row gap-3 mb-6 bg-white p-4 rounded-lg border border-emerald-200 shadow-sm">
            <input v-model="searchQuery" type="text" placeholder="Поиск по имени файла..." class="flex-1 bg-white border border-emerald-300 rounded-lg p-2 text-sm">
            <select v-if="login === 'admin_main'" v-model="filterCity" class="w-full md:w-48 bg-white border border-emerald-300 rounded-lg p-2 text-sm">
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
            <select v-model="sortBy" class="w-full md:w-56 bg-white border border-emerald-300 rounded-lg p-2 text-sm">
                <option value="date_desc">Сначала новые</option>
                <option value="date_asc">Сначала старые</option>
                <option value="name_asc">По имени (А - Я)</option>
                <option value="name_desc">По имени (Я - А)</option>
                <option value="size_desc">Размер (большие сверху)</option>
                <option value="size_asc">Размер (маленькие сверху)</option>
            </select>
        </div>
        <div v-if="filteredAndSortedFiles.length === 0" class="text-center py-8 text-emerald-700 bg-white rounded-lg border border-dashed border-emerald-200">Контент не найден.</div>
        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div v-for="file in filteredAndSortedFiles" :key="file.name" class="bg-white border border-emerald-200 p-4 rounded-lg flex flex-col gap-3 shadow-sm hover:shadow-md transition">
                <div class="flex items-center gap-3">
                    <div class="shrink-0 w-16 h-16 bg-slate-100 border border-emerald-100 rounded flex items-center justify-center overflow-hidden">
                        <img v-if="isImage(file.name)" :src="file.url" class="object-cover w-full h-full">
                        <video v-else-if="isVideo(file.name)" :src="file.url" class="object-cover w-full h-full" muted></video>
                        <span v-else class="text-xs font-bold text-emerald-400">ФАЙЛ</span>
                    </div>
                    <div class="overflow-hidden">
                        <p class="font-medium text-sm text-emerald-900 truncate" :title="file.name">{{ file.name }}</p>
                        <p class="text-[11px] text-emerald-600 mt-0.5">Размер: {{ formatSize(file.size) }}</p>
                        <p class="text-[11px] text-emerald-600">{{ formatDate(file.last_modified) }}</p>
                    </div>
                </div>
                <div class="flex gap-2 mt-auto">
                    <a :href="file.url" target="_blank" class="flex-1 text-center bg-emerald-100 hover:bg-emerald-200 text-emerald-800 text-xs px-3 py-1.5 rounded font-medium">Смотреть</a>
                    <button v-if="login === 'admin_main'" @click="requestConfirm($event, 'Переместить файл в корзину?', () => deleteFile(file.name))" class="flex-1 bg-red-50 hover:bg-red-100 text-red-700 text-xs px-3 py-1.5 rounded border border-red-200">В корзину</button>
                </div>
            </div>
        </div>
    </section>
</template>