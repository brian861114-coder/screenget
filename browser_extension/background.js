/**
 * background.js - Chrome 擴充套件背景腳本
 * 監聽分頁切換與更新事件，將網頁 URL 傳送給 ScreenGet 桌面應用。
 */

const NATIVE_HOST_NAME = 'com.screenget.host';

// 目前活動的分頁資訊
let currentTab = {
  url: '',
  title: '',
  startTime: Date.now()
};

// 嘗試連接 Native Messaging Host
let port = null;

function connectNativeHost() {
  try {
    port = chrome.runtime.connectNative(NATIVE_HOST_NAME);

    port.onMessage.addListener((msg) => {
      console.log('Received from host:', msg);
    });

    port.onDisconnect.addListener(() => {
      console.log('Native host disconnected:', chrome.runtime.lastError?.message);
      port = null;
      // 5 秒後嘗試重新連接
      setTimeout(connectNativeHost, 5000);
    });

    console.log('Connected to native host');
  } catch (e) {
    console.error('Failed to connect to native host:', e);
    port = null;
  }
}

// 傳送訊息給 Native Host
function sendToHost(data) {
  if (port) {
    try {
      port.postMessage(data);
    } catch (e) {
      console.error('Error sending message:', e);
      port = null;
    }
  }
}

// 更新目前分頁資訊
function updateCurrentTab(tab) {
  if (!tab || !tab.url) return;

  // 不再忽略 Chrome 內部頁面，讓使用者可以追蹤所有活動


  const now = Date.now();

  // 如果 URL 改變了，記錄上一個頁面的使用時間
  if (currentTab.url && currentTab.url !== tab.url) {
    const duration = (now - currentTab.startTime) / 1000;
    sendToHost({
      type: 'page_end',
      url: currentTab.url,
      title: currentTab.title,
      duration: duration,
      timestamp: new Date().toISOString()
    });
  }

  // 更新當前分頁
  currentTab = {
    url: tab.url,
    title: tab.title || '',
    startTime: now
  };

  // 通知 Native Host 新的頁面
  sendToHost({
    type: 'page_start',
    url: tab.url,
    title: tab.title || '',
    timestamp: new Date().toISOString()
  });
}

// 監聽分頁啟動事件
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  try {
    const tab = await chrome.tabs.get(activeInfo.tabId);
    updateCurrentTab(tab);
  } catch (e) {
    console.error('Error getting tab:', e);
  }
});

// 監聯分頁更新事件（URL 變更）
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.url || changeInfo.title) {
    // 確認是否為當前活動的分頁
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0] && tabs[0].id === tabId) {
        updateCurrentTab(tab);
      }
    });
  }
});

// 監聽視窗焦點變更
chrome.windows.onFocusChanged.addListener(async (windowId) => {
  if (windowId === chrome.windows.WINDOW_ID_NONE) return;

  try {
    const tabs = await chrome.tabs.query({ active: true, windowId: windowId });
    if (tabs[0]) {
      updateCurrentTab(tabs[0]);
    }
  } catch (e) {
    console.error('Error on window focus change:', e);
  }
});

// 初始化連接
connectNativeHost();

console.log('ScreenGet background script loaded');
