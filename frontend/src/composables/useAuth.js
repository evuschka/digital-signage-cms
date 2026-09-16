import { ref } from 'vue';

export function useAuth() {
    const login = ref(localStorage.getItem('cms_username') || '');
    const password = ref('');
    const authHeader = ref(localStorage.getItem('cms_auth') || '');
    const isAuthenticated = ref(!!localStorage.getItem('cms_auth'));
    const authError = ref('');
    const isResetMode = ref(false);
    const showAdminAlertModal = ref(false);
    const resetForm = ref({ username: '', success: '' });

    const doLogin = async () => {
        authError.value = '';
        const base64 = btoa(`${login.value}:${password.value}`);
        const header = `Basic ${base64}`;

        try {
            const res = await fetch('/files/', {
                headers: { 'Authorization': header }
            });

            if (!res.ok) {
                authError.value = 'Неверный логин или пароль';
                return false;
            }

            authHeader.value = header;
            isAuthenticated.value = true;
            localStorage.setItem('cms_auth', header);
            localStorage.setItem('cms_username', login.value);
            return true;
        } catch (e) {
            authError.value = 'Ошибка соединения с сервером';
            return false;
        }
    };

    const doLogout = () => {
        localStorage.removeItem('cms_auth');
        localStorage.removeItem('cms_username');
        authHeader.value = '';
        login.value = '';
        password.value = '';
        isAuthenticated.value = false;
    };

    const requestReset = async () => {
        if (!resetForm.value.username) return;
        try {
            const res = await fetch('/request-reset/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: resetForm.value.username })
            });
            const data = await res.json();
            if (res.ok) {
                resetForm.value.success = 'Запрос отправлен администратору';
            } else {
                authError.value = data.detail || 'Ошибка отправки запроса';
            }
        } catch (e) {
            authError.value = 'Ошибка связи с сервером';
        }
    };

    const updatePassword = async (onSuccessCallback) => {
        const oldP = prompt('Введите текущий пароль:');
        if (!oldP) return;
        const newP = prompt('Введите новый пароль:');
        if (!newP) return;

        try {
            const res = await fetch('/change-password/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': authHeader.value
                },
                body: JSON.stringify({ old_password: oldP, new_password: newP })
            });
            const data = await res.json();
            if (res.ok) {
                alert('Пароль успешно изменен! Пожалуйста, войдите заново.');
                if (onSuccessCallback) onSuccessCallback();
            } else {
                alert(data.detail || 'Ошибка смены пароля');
            }
        } catch (e) {
            alert('Сетевая ошибка при смене пароля');
        }
    };

    return {
        login,
        password,
        authHeader,
        isAuthenticated,
        authError,
        isResetMode,
        showAdminAlertModal,
        resetForm,
        doLogin,
        doLogout,
        requestReset,
        updatePassword
    };
}