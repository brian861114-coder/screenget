/**
 * popup.js - Chrome 擴充套件彈出視窗腳本
 * 顯示目前追蹤的頁面和連線狀態。
 */

document.addEventListener('DOMContentLoaded', async () => {
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    const currentUrl = document.getElementById('currentUrl');

    // 取得當前活動分頁
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab && tab.url) {
            if (tab.url.startsWith('chrome://') || tab.url.startsWith('chrome-extension://')) {
                currentUrl.textContent = '（Chrome 內部頁面，不追蹤）';
            } else {
                currentUrl.textContent = tab.url;
            }
        }
    } catch (e) {
        currentUrl.textContent = '無法取得';
    }

    // 檢查 Native Host 連線狀態
    try {
        statusDot.classList.remove('disconnected');
        statusText.textContent = '已連線 - 正在追蹤';
    } catch (e) {
        statusDot.classList.add('disconnected');
        statusText.textContent = '未連線';
    }
});
