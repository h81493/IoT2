# slack_test.py
"""
MicroPython Slack API Client
============================

【機能概要】
このコードは、MicroPython環境でSlack APIを使用してメッセージを送信するためのクライアントです。
主な機能：
- WiFi接続管理
- Slack APIを使用したメッセージ送信
- チャンネル名からチャンネルIDの取得
- 接続状態の確認とテスト機能
- URLパーセントエンコーディング機能
- ランダム絵文字生成機能
- 現地時刻表示機能

【対応プラットフォーム】
- ESP32
- ESP8266
- その他MicroPython対応デバイス

【必要な設定】
1. WiFi接続情報 (SSID/パスワード)
2. Slack Bot Token (xoxb-で始まるトークン)
3. 送信先チャンネル名
4. userモジュール（設定情報を含む）

【使用方法】
1. userモジュールに設定値を定義
2. main()関数を実行してメッセージ送信
3. test_connection()で接続テスト

【修正履歴】
- 2025/07/18: 初版作成 (Claude)
- 2025/07/18: 大幅な機能追加・修正 (hal)
  - userモジュールからの設定読み込み
  - URLパーセントエンコーディング関数追加
  - Content-Type変更（JSON→form-urlencoded）
  - ランダム絵文字生成機能追加
  - 現地時刻表示機能追加
  - メッセージ内容の改善
  - ホスト名設定機能追加
  - エラーハンドリング改善
- 2025/07/18: 設定値チェック強化 (Claude)
  - user.slackが未定義・空文字・Noneの場合もエラー検出するように改善
- 2025/07/18: コメント追加 (Claude)

作成者: Claude (Anthropic)
修正者: hal
"""
import urequests  # HTTP リクエスト用ライブラリ
import ujson      # JSON パース用ライブラリ
import network    # WiFi接続用ライブラリ
import time       # 時刻処理用ライブラリ
import sys        # システム関連ライブラリ

# userモジュールのキャッシュクリア（設定変更を反映するため）
if "user" in sys.modules: 
    del sys.modules["user"]
import user       # ユーザー設定モジュール

def percent_encoding(s):
    """URLパーセントエンコードを実行する関数
    
    Args:
        s (str): エンコードする文字列
    
    Returns:
        str: パーセントエンコードされた文字列
    """
    ret = ''
    for i in s:
        code = ord(i)
        # 安全な文字（英数字、一部の記号）はそのまま
        if (code >= ord('0') and code <= ord('9')) or \
           (code >= ord('A') and code <= ord('Z')) or \
           (code >= ord('a') and code <= ord('z')) or \
           code == ord('-') or code == ord('.') or \
           code == ord('_') or code == ord('~'): 
            ret = ret + i
        else:
            # それ以外の文字はパーセントエンコード
            if code <= 0x7f:
                # ASCII文字の場合
                ret = ret + ('%{:02x}'.format(code).upper())
            else:
                # マルチバイト文字（日本語など）の場合
                b = i.encode('utf-8')
                for j in b:
                    ret = ret + '%{:02x}'.format(j).upper()
    return ret

def p_dict(s):
    """辞書の値をパーセントエンコードする関数
    
    Args:
        s (dict): エンコードする辞書
    
    Returns:
        dict: 値がパーセントエンコードされた辞書
    """
    d = {}
    for i in s:
        d[i] = percent_encoding(s[i])
    return d

class SlackAPI:
    """Slack API クライアントクラス"""
    
    def __init__(self, token):
        """初期化
        
        Args:
            token (str): Slack Bot Token
        """
        self.token = token
        self.base_url = "https://slack.com/api"
        # form-urlencodedでの送信に対応したヘッダー
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8"
        }
    
    def send_message(self, channel, text, thread_ts=None):
        """チャンネルにメッセージを送信
        
        Args:
            channel (str): 送信先チャンネルID
            text (str): 送信するメッセージ
            thread_ts (str, optional): スレッドのタイムスタンプ（リプライ時）
        
        Returns:
            dict: 送信結果（成功時）またはNone（失敗時）
        """
        url = f"{self.base_url}/chat.postMessage"
        payload = {
            "channel": channel,
            "text": text
        }
        
        # スレッドへの返信の場合
        if thread_ts:
            payload["thread_ts"] = thread_ts

        # form-urlencoded形式のデータ作成（日本語対応）
        data = '&'.join('{}={}'.format(k, v) for k, v in p_dict(payload).items())
        
        # 不要なヘッダーを削除（MicroPythonの制約対応）
        if 'Connection' in self.headers:
            del self.headers['Connection']
        if 'Host' in self.headers:
            del self.headers['Host']
            
        try:
            response = urequests.post(
                url, 
                headers=self.headers,
                data=data.encode()  # バイト列として送信
            )
            
            result = ujson.loads(response.text)
            response.close()  # メモリリーク防止
            
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
        """チャンネル名からチャンネルIDを取得
        
        Args:
            channel_name (str): チャンネル名（#なし）
        
        Returns:
            str: チャンネルID（見つからない場合はNone）
        """
        url = f"{self.base_url}/conversations.list"
        
        try:
            response = urequests.get(url, headers=self.headers)
            result = ujson.loads(response.text)
            response.close()  # メモリリーク防止
            
            if result.get("ok"):
                channels = result.get("channels", [])
                # チャンネル名で検索
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
def emoji():
    """絵文字をランダムに1文字選択する関数
    
    Returns:
        str: ランダムに選択された絵文字（Unicode文字）
    """
    import random
    emj = []
    # Unicode絵文字の範囲を定義
    # 参考: http://www.asahi-net.or.jp/~ax2s-kmtn/ref/unicode/u1f300.html
    emj.append(range(0x1f32d, 0x1f3fa))  # 205文字
    emj.append(range(0x1f400, 0x1f440))  # 64文字
    emj.append(range(0x1f451, 0x1f489))  # 56文字
    emj.append(range(0x1f4a0, 0x1f4ff))  # 95文字
    emj.append(range(0x1f5fb, 0x1f600))  # 5文字
    
    # 全絵文字数を計算
    el_sum = sum(map(len, emj))
    # ランダムな位置を選択
    rand = random.choice(range(0, el_sum))
    
    # どの範囲に含まれるかを特定
    em = 0
    n = 0
    for i in map(len, emj):
        if rand < i + em: 
            break
        n = n + 1
        em = em + i
    
    # 該当する絵文字を返す
    return chr(emj[n][rand - em])
def current_time():
    """現在の現地時刻を文字列で返す関数
    
    Returns:
        str: 現在時刻（YYYY/MM/DD HH:MM:SS形式）
    """
    tstamp = time.time()
    # 時差調整（現在は0設定、必要に応じて調整）
    time_diff = 0  # 日本時間の場合は 9 * 60 * 60
    t = time.localtime(tstamp + time_diff)[0:6]
    
    # フォーマット済み時刻文字列を作成
    time_str = '{:02d}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}'\
           .format(t[0], t[1], t[2], t[3], t[4], t[5])
    return time_str

def main():
    """メイン実行関数"""
    # userモジュールから設定値を取得
    WIFI_SSID = user.ssid
    WIFI_PASSWORD = user.pswd
    SLACK_TOKEN = user.slack
    
    # ESP32のホスト名を設定
    network.hostname(user.espName())

    print("=== MicroPython Slack API テスト ===")
    
    try:
        # WiFi接続を試行
        wlan = connect_wifi(WIFI_SSID, WIFI_PASSWORD)
        if not wlan:
            print("WiFi接続に失敗しました")
            return
        
        # Slack API クライアントを初期化
        slack = SlackAPI(SLACK_TOKEN)
        
        # 送信先チャンネルの設定
        print("\nチャンネル情報を取得中...")
        channel_name = "test2"
        
        # 送信メッセージの作成（絵文字、ユーザー情報、時刻を含む）
        message = 'ESP32 SLACK API てすと ﾃｽﾄ  {:s} from {:s} {:s} at {:s}'\
           .format(emoji(), user.gid, user.espName(), current_time())
        
        # チャンネルIDを取得
        channel_id = slack.get_channel_id(channel_name)
        
        if channel_id:
            print(f"チャンネル # {channel_name} のID: {channel_id}")
            
            # メッセージを送信
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
        sys.print_exception(e)  # 詳細なエラー情報を表示

# テスト実行用の簡単な関数
def test_connection():
    """WiFi接続とインターネット接続をテストする関数"""
    print("=== 接続テスト ===")
    
    # WiFi接続状態を確認
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        print(f"✅ WiFi接続済み: {wlan.ifconfig()}")
    else:
        print("❌ WiFi未接続")
    
    # インターネット接続テスト
    try:
        print("インターネット接続テスト中...")
        response = urequests.get("http://httpbin.org/ip")
        print(f"✅ インターネット接続OK: {response.text}")
        response.close()  # メモリリーク防止
    except Exception as e:
        print(f"❌ インターネット接続エラー: {e}")

# ===========================================
# プログラム実行部分
# ===========================================
if __name__ == "__main__":
    # Slack Bot Tokenが正しく設定されているかチェック
    if not hasattr(user, 'slack') or not user.slack or user.slack in ["xoxb-your-bot-token-here", ""]:
        print("⚠️  設定値を実際の値に変更してください:")
        print("   - slack: 実際のBot Token")
        print("\n設定後、main()を実行してください")
    else:
        # 設定が完了している場合は自動実行
        main()

