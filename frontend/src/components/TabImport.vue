<script setup>
const props = defineProps(['media']);
const { selectedCity, selectedFile, uploading, uploadProgress, uploadError, importLogs, handleFileSelect, uploadFile } = props.media;
</script>

<template>
    <div class="space-y-6">
        <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm">
            <h2 class="text-xl font-semibold mb-2 text-emerald-900">Импорт контента</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
                <!-- Блок загрузки -->
                <div class="space-y-4 bg-white p-5 rounded-lg border border-emerald-200 shadow-sm">
                    <h3 class="text-sm font-semibold text-emerald-900">Параметры</h3>
                    <div>
                        <label class="block text-xs text-emerald-700 mb-1 font-medium">Целевой филиал:</label>
                        <select v-model="selectedCity" class="w-full bg-white border border-emerald-300 text-sm rounded-lg p-2.5 focus:outline-none focus:border-emerald-600">
                            <option value="global">Вся сеть (Все города)</option>
                            <option value="moscow">Москва</option>
                            <option value="spb">Санкт-Петербург</option>
                            <option value="novocheboksarsk">Новочебоксарск</option>
                            <option value="yartsevo">Ярцево</option>
                            <option value="azov">Азов</option>
                            <option value="orenburg">Оренбург</option>
                            <option value="chernyakhovsk">Черняховск</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs text-emerald-700 mb-1 font-medium">Файл:</label>
                        <input type="file" @change="handleFileSelect" class="block w-full text-xs text-emerald-800 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-emerald-600 file:text-white cursor-pointer">
                    </div>
                    <div v-if="uploading" class="w-full bg-emerald-100 rounded-full h-2">
                        <div class="bg-emerald-600 h-2 rounded-full transition-all duration-300" :style="{ width: uploadProgress + '%' }"></div>
                    </div>
                    <button @click="uploadFile" :disabled="!selectedFile || uploading" class="w-full bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300 text-white font-medium px-4 py-2.5 rounded-lg transition text-sm">
                        {{ uploading ? `Загрузка... ${uploadProgress}%` : 'Начать импорт' }}
                    </button>
                    <p v-if="uploadError" class="text-red-600 text-xs mt-2">{{ uploadError }}</p>
                </div>
                
                <!-- Журнал загрузки -->
                <div class="bg-white p-5 rounded-lg border border-emerald-200 shadow-sm">
                    <h3 class="text-sm font-semibold text-emerald-900 mb-3">Журнал обработки</h3>
                    <div v-if="importLogs.length === 0" class="text-xs text-emerald-600 py-12 text-center border border-dashed border-emerald-200 rounded-lg">Отчет пуст.</div>
                    <div v-else class="space-y-2 max-h-64 overflow-y-auto">
                        <div v-for="(log, idx) in importLogs" :key="idx" class="p-3 rounded text-xs border" :class="log.success ? 'bg-emerald-50 border-emerald-200 text-emerald-900' : 'bg-red-50 border-red-200 text-red-900'">
                            <p class="font-semibold">{{ log.filename }} — <span>{{ log.success ? 'Успешно' : 'Ошибка' }}</span></p>
                            <p class="mt-0.5">{{ log.text }}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>