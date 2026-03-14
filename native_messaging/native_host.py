"""
native_host.py - Native Messaging Host
接收來自 Chrome 擴充套件的訊息，將網頁使用資料寫入 SQLite 資料庫。
"""

import sys
import json
import struct
import logging
import os

# 將專案根目錄加入 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import UsageDatabase

logger = logging.getLogger(__name__)

log_dir = os.path.join(os.getenv('APPDATA', ''), 'ScreenGet')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'native_host.log'),
                          encoding='utf-8')
    ]
)


def read_message():
    """從 stdin 讀取 Chrome 傳來的訊息"""
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        return None
    message_length = struct.unpack('=I', raw_length)[0]
    message = sys.stdin.buffer.read(message_length).decode('utf-8')
    return json.loads(message)


def send_message(data):
    """透過 stdout 送出訊息給 Chrome"""
    encoded = json.dumps(data).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('=I', len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def main():
    """Native Messaging Host 主循環"""
    db = UsageDatabase()
    current_session_id = None

    logger.info("Native messaging host started")
    logger.info(f"Python executable: {sys.executable}")
    logger.info(f"Current directory: {os.getcwd()}")
    logger.info(f"Database path: {db.db_path}")

    while True:
        try:
            message = read_message()
            if message is None:
                logger.info("Received empty message (EOF), stopping")
                break

            msg_type = message.get('type', '')
            url = message.get('url', '')
            title = message.get('title', '')

            logger.info(f"Received message: {json.dumps(message)}")

            if msg_type == 'page_start':
                # 結束前一個 session
                if current_session_id is not None:
                    logger.info(f"Ending session {current_session_id} for new page")
                    db.end_session(current_session_id)

                # 開始新的 session
                # 從 URL 提取域名作為 app_name
                from urllib.parse import urlparse
                parsed = urlparse(url)
                if parsed.scheme in ('chrome', 'about', 'edge', 'chrome-extension'):
                    domain = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else f"{parsed.scheme}://internal"
                else:
                    domain = parsed.netloc or url[:50]

                current_session_id = db.start_session(
                    app_name=domain,
                    window_title=title,
                    exe_path='',
                    app_type='browser',
                    url=url
                )
                logger.info(f"Started session {current_session_id} for {domain}")

                send_message({'status': 'ok', 'session_id': current_session_id})

            elif msg_type == 'page_end':
                if current_session_id is not None:
                    logger.info(f"Ending session {current_session_id} (page_end)")
                    db.end_session(current_session_id)
                    current_session_id = None
                send_message({'status': 'ok'})

            else:
                logger.warning(f"Unknown message type: {msg_type}")
                send_message({'status': 'unknown_type'})

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            try:
                send_message({'status': 'error', 'message': str(e)})
            except Exception:
                pass

    # 清理
    if current_session_id is not None:
        logger.info(f"Cleaning up: ending session {current_session_id}")
        db.end_session(current_session_id)

    logger.info("Native messaging host stopped")


if __name__ == '__main__':
    main()
