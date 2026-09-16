import { ref, computed } from 'vue';

export function usePlaylists(authHeader, showToast, isImage, isVideo, safeJson, getFilesRef) {
    const playlists = ref([]); 
    const showPlaylistModal = ref(false); 
    const selectedFileToAdd = ref('');
    const newPlaylist = ref({ name: '', city: 'global', items: [], interval: 3, repeats: 1 });
    const showPreviewModal = ref(false); 
    const previewPlaylistName = ref(''); 
    const previewItems = ref([]);
    const previewIndex = ref(0); 
    const previewCurrentItem = computed(() => previewItems.value[previewIndex.value] || null);
    let previewTimer = null;
    
    const fetchPlaylists = async () => {
        try {
            const res = await fetch('/playlists/', { headers: { 'Authorization': authHeader.value } });
            const data = await safeJson(res); 
            playlists.value = data.playlists || [];
        } catch (e) {}
    };

    const addFileToPlaylist = () => { 
        if (!selectedFileToAdd.value) return; 
        newPlaylist.value.items.push({ file: selectedFileToAdd.value, duration: 10 }); 
    };

    const removePlaylistItem = (index) => { 
        newPlaylist.value.items.splice(index, 1); 
    };

    const movePlaylistItem = (index, direction) => {
        const newIndex = index + direction;
        if (newIndex < 0 || newIndex >= newPlaylist.value.items.length) return;
        const item = newPlaylist.value.items.splice(index, 1)[0];
        newPlaylist.value.items.splice(newIndex, 0, item);
    };

    const savePlaylist = async () => {
        if (!newPlaylist.value.name.trim() || newPlaylist.value.items.length === 0) {
            return showToast('Укажите название и добавьте файлы!', 'warning');
        }
        try {
            const res = await fetch('/playlists/', { 
                method: 'POST', 
                headers: { 'Authorization': authHeader.value, 'Content-Type': 'application/json' }, 
                body: JSON.stringify(newPlaylist.value) 
            });
            if (res.ok) {
                newPlaylist.value = { name: '', city: 'global', items: [], interval: 3, repeats: 1 };
                showPlaylistModal.value = false; 
                fetchPlaylists(); 
                showToast('Плейлист сохранен!', 'success');
            } else { 
                const err = await safeJson(res); 
                showToast(err.detail || 'Ошибка сохранения', 'error'); 
            }
        } catch (e) { 
            showToast('Ошибка сети', 'error'); 
        }
    };

    const deletePlaylist = async (id) => {
        try {
            const res = await fetch(`/playlists/${id}`, { method: 'DELETE', headers: { 'Authorization': authHeader.value } });
            if (res.ok) { 
                fetchPlaylists(); 
                showToast('Плейлист удален', 'success'); 
            }
        } catch (e) { 
            showToast('Ошибка сети', 'error'); 
        }
    };

    const getFileUrl = (name) => {
        const files = getFilesRef() || [];
        return files.find(f => f.name === name)?.url || '';
    };

    const runPreviewStep = () => {
        if (!showPreviewModal.value) return;
        const item = previewItems.value[previewIndex.value];
        if (!item) return;
        let delay = (item.duration || 10) * 1000;
        if (isVideo(item.file)) delay = 5000;
        if (previewTimer) clearTimeout(previewTimer);
        previewTimer = setTimeout(() => { 
            previewIndex.value = (previewIndex.value + 1) % previewItems.value.length; 
            runPreviewStep(); 
        }, delay);
    };

    const startPreview = (pl) => {
        if (!pl.items || pl.items.length === 0) return showToast('Плейлист пуст', 'warning');
        previewPlaylistName.value = pl.name; 
        previewItems.value = pl.items; 
        previewIndex.value = 0;
        showPreviewModal.value = true; 
        runPreviewStep();
    };

    const closePreview = () => { 
        showPreviewModal.value = false; 
        if (previewTimer) clearTimeout(previewTimer); 
    };

    return { 
        playlists, showPlaylistModal, selectedFileToAdd, newPlaylist, showPreviewModal, 
        previewPlaylistName, previewItems, previewIndex, previewCurrentItem, 
        fetchPlaylists, addFileToPlaylist, removePlaylistItem, movePlaylistItem, 
        savePlaylist, deletePlaylist, startPreview, closePreview, getFileUrl 
    };
}