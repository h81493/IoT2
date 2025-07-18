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

【対応プラットフォーム】
- ESP32
- ESP8266
- その他MicroPython対応デバイス

【必要な設定】
1. WiFi接続情報 (SSID/パスワード)
2. Slack Bot Token (xoxb-で始まるトークン)
3. 送信先チャンネル名

【使用方法】
1. 設定値を実際の値に変更
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

作成者: Claude (Anthropic)
修正者: hal

"""
import urequests
import ujson
import network
import time
import sys
if "user" in sys.modules: # userモジュールのキャッシュを削除
    del sys.modules["user"]
import user

def percent_encoding(s):
#URLパーセントエンコードする。
    ret=''
    for i in s:
        code=ord(i)
        if (code>= ord('0') and code <= ord('9')) or \
          (code>= ord('A') and code <= ord('Z')) or \
          (code>= ord('a') and code <= ord('z')) or \
          code==ord('-') or code==ord('.') or \
          code==ord('_') or code==ord('~'): 
            ret=ret+i
        else:
            if code<=0x7f:
                ret=ret+('%{:02x}'.format(code).upper())
                #":/?#[]@!$&'()*+,;=%"
            else:
                b=i.encode('utf-8')
                for j in b:
                    ret=ret+'%{:02x}'.format(j).upper()
    return ret

def p_dict(s):
    d={}
    for i in s:
        d[i]=percent_encoding(s[i])
    return(d)

class SlackAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://slack.com/api"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8"
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

        data = '&'.join('{}={}'.format(k, v) for k, v in p_dict(payload).items())
        del self.headers['Connection']
        del self.headers['Host']
        try:
            response = urequests.post(
                url, 
                headers=self.headers,
                data=data.encode()
                #data=ujson.dumps(payload)
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
def emoji():
#絵文字をランダムに１文字選ぶ。
    import random
    emj=[]
    #http://www.asahi-net.or.jp/~ax2s-kmtn/ref/unicode/u1f300.html
    emj.append(range(0x1f32d,0x1f3fa))#205
    emj.append(range(0x1f400,0x1f440))#64
    emj.append(range(0x1f451,0x1f489))#56
    emj.append(range(0x1f4a0,0x1f4ff))#95
    emj.append(range(0x1f5fb,0x1f600))#5
    el_sum=sum(map(len, emj))
    rand=random.choice(range(0,el_sum))
    em=0
    n=0
    for i in map(len,emj):
        if rand<i+em: break
        n=n+1
        em=em+i
    return chr(emj[n][rand-em])
def current_time():
#現地時刻を返す。
    tstamp=time.time()
    #time_diff = 9 * 60 * 60    # 日本の時差
    time_diff = 0
    t=time.localtime(tstamp+time_diff)[0:6]
    time_str = '{:02d}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}'\
           .format(t[0],t[1],t[2],t[3],t[4],t[5])
    return(time_str)

def main():
    # ===== 設定値を更新してください =====
    WIFI_SSID = user.ssid
    WIFI_PASSWORD = user.pswd
    SLACK_TOKEN = user.slack
    network.hostname(user.espName())

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
        channel_name = "test2"
        message = 'ESP32 SLACK API てすと ﾃｽﾄ  {:s} from {:s} {:s} at {:s}'\
           .format(emoji(),user.gid,user.espName(),current_time())
        channel_id = slack.get_channel_id(channel_name)
        
        if channel_id:
            print(f"チャンネル # {channel_name} のID: {channel_id}")
            
            # メッセージ送信
            #message = "Hello from MicroPython :snake:"
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
    if user.slack in ["xoxb-your-bot-token-here"]:
        print("⚠️  設定値を実際の値に変更してください:")
        print("   - slack: 実際のBot Token")
        print("\n設定後、main()を実行してください")
    else:
        # 設定済みの場合は自動実行
        main()

