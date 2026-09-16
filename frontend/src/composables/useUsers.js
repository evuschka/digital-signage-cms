import { ref } from 'vue';

export function useUsers(authHeader, showToast, safeJson) {
    const adminUsers = ref({}); 
    const adminRequests = ref([]);
    const showAddUserModal = ref(false);
    const newUserForm = ref({ username: '', password: '', role: 'regional', city_id: 'moscow' });

    const fetchAdminUsers = async () => {
        try {
            const res = await fetch('/admin/users/', { headers: { 'Authorization': authHeader.value } });
            if (res.ok) { 
                const data = await safeJson(res); 
                adminUsers.value = data.users || {}; 
                adminRequests.value = data.requests || []; 
            }
        } catch (e) {}
    };

    const createUser = async () => {
        if (!newUserForm.value.username || !newUserForm.value.password) {
            return showToast('Заполните логин и пароль', 'warning');
        }
        try {
            const res = await fetch('/admin/users/', { 
                method: 'POST', 
                headers: { 'Authorization': authHeader.value, 'Content-Type': 'application/json' }, 
                body: JSON.stringify(newUserForm.value) 
            });
            if (res.ok) {
                showAddUserModal.value = false; 
                newUserForm.value = { username: '', password: '', role: 'regional', city_id: 'moscow' };
                fetchAdminUsers(); 
                showToast('Пользователь успешно создан', 'success');
            } else { 
                const data = await safeJson(res); 
                showToast(data.detail || 'Ошибка создания', 'error'); 
            }
        } catch (e) { 
            showToast('Ошибка сети', 'error'); 
        }
    };

    const deleteUser = async (uname) => {
        try {
            const res = await fetch(`/admin/users/${uname}`, { method: 'DELETE', headers: { 'Authorization': authHeader.value } });
            if (res.ok) { 
                fetchAdminUsers(); 
                showToast('Пользователь удален', 'success'); 
            } else { 
                const data = await safeJson(res); 
                showToast(data.detail || 'Ошибка удаления', 'error'); 
            }
        } catch (e) { 
            showToast('Ошибка сети', 'error'); 
        }
    };

    const forceReset = async (uname) => {
        try {
            const res = await fetch('/admin/reset-password/', { 
                method: 'POST', 
                headers: { 'Authorization': authHeader.value, 'Content-Type': 'application/json' }, 
                body: JSON.stringify({ username: uname }) 
            });
            const data = await safeJson(res);
            if (res.ok) { 
                fetchAdminUsers(); 
                alert(`🛑 ВАЖНО: ПАРОЛЬ СБРОШЕН!\n\nПользователь: ${uname}\nВременный пароль: ${data.temp_password}\n\nОбязательно передайте этот пароль сотруднику!`);
            } else { 
                showToast(data.detail || 'Ошибка сброса', 'error'); 
            }
        } catch (e) { 
            showToast('Ошибка сети', 'error'); 
        }
    };

    return { adminUsers, adminRequests, showAddUserModal, newUserForm, fetchAdminUsers, createUser, deleteUser, forceReset };
}