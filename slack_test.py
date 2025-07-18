import urequests
import ujson
import network
import time

class SlackAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://slack.com/api"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def send_message(self, channel, text, thread_ts=None):
        """チャンネルにメッセージを送信"""
        url = f"{self.base_url}/chat.postMessage"
        
        payload = {
            "channel": channel,
            "text": text
        }
        
        if thread_ts:
            payload["thread_ts"] = thread_ts
        
        try:
            response = urequests.post(
                url, 
                headers=self.headers,
                data=ujson.dumps(payload)
            )
            
            result = ujson.loads(response.text)
            response.close()
            
            if result.get("ok"):
                print(f"メッセージ送信成功: {result.get('ts')}")
                return result
            else:
                print(f"エラー: {result.get('error')}")
                return None
                
        except Exception as e:
            print(f"送信エラー: {e}")
            return None
    
    def get_channel_id(self, channel_name):
        """チャンネル名からチャンネルIDを取得"""
        url = f"{self.base_url}/conversations.list"
        
        try:
            response = urequests.get(url, headers=self.headers)
            result = ujson.loads(response.text)
            response.close()
            
            if result.get("ok"):
                channels = result.get("channels", [])
                for channel in channels:
                    if channel.get("name") == channel_name:
                        return channel.get("id")
            return None
            
        except Exception as e:
            print(f"チャンネル取得エラー: {e}")
            return None

def connect_wifi(ssid, password):
    """WiFi接続"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print("WiFiに接続中...")
        wlan.connect(ssid, password)
        
        timeout = 10  # 10秒でタイムアウト
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            print(".", end="")
        
        if wlan.isconnected():
            print(f"\nWiFi接続完了: {wlan.ifconfig()}")
            return wlan
        else:
            print("\nWiFi接続失敗")
            return None
    else:
        print(f"既にWiFi接続済み: {wlan.ifconfig()}")
        return wlan

def main():
    # ===== 設定値を更新してください =====
    # 例：
    # WIFI_SSID = ""                    # あなたのWiFi名
    # WIFI_PASSWORD = ""             # あなたのWiFiパスワード
    # SLACK_TOKEN = ""  # 実際のBot Token
    
    WIFI_SSID = ""              # 実際のWiFi名に変更
    WIFI_PASSWORD = ""      # 実際のWiFiパスワードに変更
    SLACK_TOKEN = ""  # 実際のBot Tokenに変更
    
    print("=== MicroPython Slack API テスト ===")
    
    try:
        # WiFi接続
        wlan = connect_wifi(WIFI_SSID, WIFI_PASSWORD)
        if not wlan:
            print("WiFi接続に失敗しました")
            return
        
        # Slack API初期化
        slack = SlackAPI(SLACK_TOKEN)
        
        # チャンネルIDを取得 (チャンネル名 "test" の場合)
        print("\nチャンネル情報を取得中...")
        channel_id = slack.get_channel_id("test")
        
        if channel_id:
            print(f"チャンネル #test のID: {channel_id}")
            
            # メッセージ送信
            message = "Hello from MicroPython! 🐍"
            print(f"\nメッセージを送信中: {message}")
            result = slack.send_message(channel_id, message)
            
            if result:
                print("✅ メッセージ送信完了")
            else:
                print("❌ メッセージ送信失敗")
        else:
            print("❌ チャンネル #test が見つかりません")
            print("利用可能なチャンネルを確認してください")
            
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import sys
        sys.print_exception(e)

# テスト実行用の簡単な関数
def test_connection():
    """接続テスト"""
    print("=== 接続テスト ===")
    
    # WiFi状態確認
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        print(f"✅ WiFi接続済み: {wlan.ifconfig()}")
    else:
        print("❌ WiFi未接続")
    
    # 簡単なHTTP接続テスト
    try:
        print("インターネット接続テスト中...")
        response = urequests.get("http://httpbin.org/ip")
        print(f"✅ インターネット接続OK: {response.text}")
        response.close()
    except Exception as e:
        print(f"❌ インターネット接続エラー: {e}")

# 実行例
if __name__ == "__main__":
    # 設定値が正しく設定されているかチェック
    if "your_wifi_ssid" in ["your_wifi_ssid", "your_wifi_password", "xoxb-your-bot-token-here"]:
        print("⚠️  設定値を実際の値に変更してください:")
        print("   - WIFI_SSID: 実際のWiFi名")
        print("   - WIFI_PASSWORD: 実際のWiFiパスワード")
        print("   - SLACK_TOKEN: 実際のBot Token")
        print("\n設定後、main()を実行してください")
    else:
        # 設定済みの場合は自動実行
        main()
