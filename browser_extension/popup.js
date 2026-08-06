/**
 * popup.js - Chrome 擴充套件彈出視窗腳本
 * 顯示目前追蹤的頁面和連線狀態。
 */

document.addEventListener('DOMContentLoaded', async () => {
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    const currentUrl = document.getElementById('currentUrl');

    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab && tab.url) {
            currentUrl.textContent = tab.url;
        } else {
            currentUrl.textContent = '無法取得';
        }
    } catch (e) {
        currentUrl.textContent = '無法取得';
    }

    try {
        const status = await chrome.runtime.sendMessage({ type: 'get_status' });
        if (status && status.connected) {
            statusDot.classList.remove('disconnected');
            statusText.textContent = '已連線 - 正在追蹤';
            if (status.url) {
                currentUrl.textContent = status.url;
            }
        } else {
            statusDot.classList.add('disconnected');
            statusText.textContent = '未連線（請確認 ScreenGet 已啟動並註冊橋接）';
        }
    } catch (e) {
        statusDot.classList.add('disconnected');
        statusText.textContent = '未連線';
    }
});
