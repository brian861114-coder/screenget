"""
native_host.py - Native Messaging Host
接收 Chrome 擴充套件訊息，寫入 bridge 狀態檔供主程式套用。
（不再直接寫入使用時長 DB，避免與前景追蹤雙重計時）
"""

import sys
import json
import struct
import logging
import os

# 將專案根目錄加入 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.browser_bridge import write_bridge_event, get_app_data_dir

log_dir = get_app_data_dir()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(log_dir, "native_host.log"), encoding="utf-8"
        )
    ],
)
logger = logging.getLogger(__name__)


def read_message():
    """從 stdin 讀取 Chrome 傳來的訊息"""
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        return None
    message_length = struct.unpack("=I", raw_length)[0]
    message = sys.stdin.buffer.read(message_length).decode("utf-8")
    return json.loads(message)


def send_message(data):
    """透過 stdout 送出訊息給 Chrome"""
    encoded = json.dumps(data).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("=I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def main():
    logger.info("Native messaging host started")
    logger.info(f"Python executable: {sys.executable}")
    logger.info(f"Bridge state dir: {log_dir}")

    while True:
        try:
            message = read_message()
            if message is None:
                logger.info("Received empty message (EOF), stopping")
                break

            msg_type = message.get("type", "")
            url = message.get("url", "")
            title = message.get("title", "")
            logger.info(f"Received: type={msg_type} url={url[:80]!r}")

            if msg_type in ("page_start", "page_end", "ping"):
                write_bridge_event(msg_type, url=url, title=title)
                send_message({"status": "ok", "type": msg_type})
            else:
                logger.warning(f"Unknown message type: {msg_type}")
                send_message({"status": "unknown_type"})

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            try:
                send_message({"status": "error", "message": str(e)})
            except Exception:
                pass

    logger.info("Native messaging host stopped")


if __name__ == "__main__":
    main()
