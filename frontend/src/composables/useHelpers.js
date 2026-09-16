export function useHelpers() {
    const isImage = (name) => /\.(jpeg|jpg|png|webp|gif|svg|heic)$/i.test(name);
    const isVideo = (name) => /\.(mp4|mov|mkv|webm|avi)$/i.test(name);

    const formatSize = (bytes) => {
        if (!bytes || bytes === 0) return '0 B'; 
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + ['B', 'KB', 'MB', 'GB'][i];
    };

    const formatDate = (isoString, withSeconds = false) => {
        if (!isoString) return ''; 
        const d = new Date(isoString);
        const options = { hour: '2-digit', minute:'2-digit', hour12: false };
        if (withSeconds) options.second = '2-digit';
        return d.toLocaleDateString('ru-RU') + ' ' + d.toLocaleTimeString('ru-RU', options);
    };

    const getRemainingDays = (deletedAt) => {
        if (!deletedAt) return 'Срок неизвестен';
        const expiryDate = new Date(new Date(deletedAt).getTime() + 30 * 24 * 60 * 60 * 1000);
        const diffDays = Math.ceil((expiryDate - new Date()) / (1000 * 60 * 60 * 24));
        return diffDays <= 0 ? 'Истекает сегодня' : `Осталось хранения: ${diffDays} дн.`;
    };

    return { isImage, isVideo, formatSize, formatDate, getRemainingDays };
}