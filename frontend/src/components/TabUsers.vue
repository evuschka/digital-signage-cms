<script setup>
const props = defineProps(['users', 'auth', 'requestConfirm']);
const { adminUsers, adminRequests, showAddUserModal, newUserForm, fetchAdminUsers, createUser, deleteUser, forceReset } = props.users;
const { login } = props.auth;
</script>

<template>
    <div class="space-y-6">
        <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-6 shadow-sm">
            <div class="flex justify-between items-center mb-6">
                <h2 class="text-xl font-semibold text-emerald-900">Управление учетными записями</h2>
                <div class="flex gap-2">
                    <button @click="showAddUserModal = true" class="text-xs bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-md font-medium shadow-sm">+ Новый пользователь</button>
                    <button @click="fetchAdminUsers" class="text-xs bg-emerald-200 hover:bg-emerald-300 text-emerald-900 px-3 py-1.5 rounded-md font-medium">Обновить</button>
                </div>
            </div>

            <div v-if="showAddUserModal" class="bg-emerald-100/50 border border-emerald-200 rounded-xl p-6 shadow-md mb-6">
                <h3 class="text-lg font-medium mb-4 text-emerald-800">Создание нового пользователя</h3>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                    <div><label class="block text-xs text-emerald-700 mb-1 font-medium">Логин</label><input v-model="newUserForm.username" type="text" class="w-full bg-white border border-emerald-300 rounded p-2 text-sm"></div>
                    <div><label class="block text-xs text-emerald-700 mb-1 font-medium">Пароль</label><input v-model="newUserForm.password" type="text" class="w-full bg-white border border-emerald-300 rounded p-2 text-sm"></div>
                    <div><label class="block text-xs text-emerald-700 mb-1 font-medium">Роль</label><select v-model="newUserForm.role" class="w-full bg-white border border-emerald-300 rounded p-2 text-sm"><option value="regional">Региональный</option><option value="admin">Администратор</option></select></div>
                    <div><label class="block text-xs text-emerald-700 mb-1 font-medium">Филиал (Город)</label><select v-model="newUserForm.city_id" class="w-full bg-white border border-emerald-300 rounded p-2 text-sm"><option value="global">Вся сеть</option><option value="moscow">Москва</option><option value="spb">Санкт-Петербург</option><option value="orenburg">Оренбург</option></select></div>
                </div>
                <div class="flex justify-end gap-3"><button @click="showAddUserModal = false" class="bg-emerald-200 text-emerald-900 px-4 py-2 rounded text-sm">Отмена</button><button @click="createUser" class="bg-emerald-600 text-white px-4 py-2 rounded text-sm">Создать</button></div>
            </div>

            <div class="bg-white border border-emerald-200 rounded-lg overflow-hidden">
                <table class="w-full text-sm text-left text-emerald-900">
                    <thead class="text-xs text-emerald-800 uppercase bg-emerald-100/70 border-b border-emerald-200"><tr><th class="px-6 py-3">Логин</th><th class="px-6 py-3">Роль</th><th class="px-6 py-3">Город</th><th class="px-6 py-3">Действия</th></tr></thead>
                    <tbody>
                        <tr v-for="(info, uname) in adminUsers" :key="uname" class="border-b border-emerald-200 hover:bg-emerald-50">
                            <td class="px-6 py-4 font-medium">{{ uname }}</td><td class="px-6 py-4">{{ info.role }}</td><td class="px-6 py-4">{{ info.city_id }}</td>
                            <td class="px-6 py-4 flex gap-2">
                                <button @click="requestConfirm($event, `Сбросить пароль?`, () => forceReset(uname))" class="bg-emerald-600 hover:bg-emerald-700 text-white text-xs px-3 py-1.5 rounded">Сбросить</button>
                                <button v-if="uname !== login" @click="requestConfirm($event, `Точно удалить?`, () => deleteUser(uname))" class="bg-red-50 text-red-700 text-xs px-3 py-1.5 rounded border border-red-200">Удалить</button>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</template>