/**
 * background.js - Chrome 擴充套件背景腳本
 * 監聽分頁切換與更新事件，將網頁 URL 傳送給 ScreenGet 桌面應用。
 */

const NATIVE_HOST_NAME = 'com.screenget.host';

let currentTab = {
  url: '',
  title: '',
  startTime: Date.now()
};

let port = null;
let connected = false;

function connectNativeHost() {
  try {
    port = chrome.runtime.connectNative(NATIVE_HOST_NAME);

    port.onMessage.addListener((msg) => {
      console.log('Received from host:', msg);
      if (msg && msg.status === 'ok') {
        connected = true;
      }
    });

    port.onDisconnect.addListener(() => {
      const err = chrome.runtime.lastError?.message || 'disconnected';
      console.log('Native host disconnected:', err);
      port = null;
      connected = false;
      setTimeout(connectNativeHost, 5000);
    });

    connected = true;
    console.log('Connected to native host');
    // 連線後立刻 ping，讓桌面端知道橋接活著
    sendToHost({ type: 'ping', url: '', title: '', timestamp: new Date().toISOString() });
  } catch (e) {
    console.error('Failed to connect to native host:', e);
    port = null;
    connected = false;
    setTimeout(connectNativeHost, 5000);
  }
}

function sendToHost(data) {
  if (!port) {
    connectNativeHost();
  }
  if (!port) return;
  try {
    port.postMessage(data);
  } catch (e) {
    console.error('Error sending message:', e);
    port = null;
    connected = false;
  }
}

function updateCurrentTab(tab) {
  if (!tab || !tab.url) return;

  const now = Date.now();

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

  currentTab = {
    url: tab.url,
    title: tab.title || '',
    startTime: now
  };

  sendToHost({
    type: 'page_start',
    url: tab.url,
    title: tab.title || '',
    timestamp: new Date().toISOString()
  });
}

chrome.tabs.onActivated.addListener(async (activeInfo) => {
  try {
    const tab = await chrome.tabs.get(activeInfo.tabId);
    updateCurrentTab(tab);
  } catch (e) {
    console.error('Error getting tab:', e);
  }
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.url || changeInfo.title) {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0] && tabs[0].id === tabId) {
        updateCurrentTab(tab);
      }
    });
  }
});

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

// popup 可查詢連線狀態
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === 'get_status') {
    sendResponse({
      connected: connected && !!port,
      url: currentTab.url || '',
      title: currentTab.title || ''
    });
    return true;
  }
});

// 週期 ping，維持狀態檔新鮮度
setInterval(() => {
  sendToHost({ type: 'ping', url: currentTab.url || '', title: currentTab.title || '', timestamp: new Date().toISOString() });
}, 60000);

connectNativeHost();

// 啟動時同步目前分頁
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  if (tabs[0]) updateCurrentTab(tabs[0]);
});

console.log('ScreenGet background script loaded');
