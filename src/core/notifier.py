from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, TextMessage
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.config import LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID  # configから設定を使用

# Botの初期化
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)

def send_message(message: str, user_id: str = LINE_USER_ID):
    """
    指定ユーザーにメッセージを送信
    """
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message({
                "to": user_id,
                "messages": [TextMessage(text=message)]
            })
        print("✅ メッセージを送信しました")
    except Exception as e:
        print(f"❌ メッセージ送信に失敗しました: {e}")

# ユーザーの提供したコードと互換性を保つためのエイリアス
def send_line_message(message: str):
    """
    指定したLINEユーザーにメッセージを送信する
    """
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message({
                "to": LINE_USER_ID,
                "messages": [TextMessage(text=message)]
            })
        print("✅ LINEメッセージを送信しました。")
    except Exception as e:
        print(f"❌ メッセージ送信に失敗しました: {e}")

# テスト用エントリーポイント（ターミナルから実行可）
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("使い方: python notifier.py 'メッセージ'")
        exit(1)
    test_message = sys.argv[1]
    send_message(test_message)
