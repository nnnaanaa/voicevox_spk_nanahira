from requests.exceptions import Timeout
from datetime import datetime
import requests
import json
import io
import wave
import pyaudio
import time
import cv2
import os

def main():
    # 天気予報の取得
    office_name = "東京都"

    weathermap = OpenWeatherMap()
    area_code = weathermap.get_weather_forecast_area_code()[office_name]
    text = weathermap.get_weather_forecast(area_code)

    voicevox = VoicevoxEngine()
    voicevox.speak(text=text)

class VoicevoxEngine:
    def __init__(self,host="127.0.0.1",port=50021):
        self.host = host
        self.port = port

    def speak(self,text=None,speaker=54): # spaker_id = ななひら
        params = (
            ("text", text),
            ("speaker", speaker)
        )

        try:
            init_q = requests.post(
                f"http://{self.host}:{self.port}/audio_query",
                params=params
            )

            res = requests.post(
                f"http://{self.host}:{self.port}/synthesis",
                headers={"Content-Type": "application/json"},
                params=params,
                data=json.dumps(init_q.json())
            )
        # http request error
        except requests.exceptions.RequestException as e:
            print(e)
            return False

        # メモリ展開
        audio = io.BytesIO(res.content)

        with wave.open(audio,'rb') as f:
            # 音声再生処理
            p = pyaudio.PyAudio()

            def _callback(in_data, frame_count, time_info, status):
                data = f.readframes(frame_count)
                return (data, pyaudio.paContinue)

            stream = p.open(format=p.get_format_from_width(width=f.getsampwidth()),
                            channels=f.getnchannels(),
                            rate=f.getframerate(),
                            output=True,
                            stream_callback=_callback)

            # 音声再生
            stream.start_stream()
            while stream.is_active():
                time.sleep(0.1)

            stream.stop_stream()
            stream.close()
            p.terminate()

    def speak_weather(self):
        pass

# 気象庁APIを使用して天気予報の取得。気温が取得できないのが難点。
class WeatherForecast:
    def __init__(self):
        pass

    def get_weather_forecast_area_code(self):
        try:
            area_code_url = "https://www.jma.go.jp/bosai/common/const/area.json"
            area_code_json = requests.get(area_code_url).json()
            area_code_list = list(area_code_json["offices"].keys())
            area_name_list = [_["name"] for _ in area_code_json["offices"].values()]
            # zip()関数を使用して、keysとvaluesをまとめて1つのイテレータにする
            pairs = zip(area_name_list, area_code_list)

            # dict()関数を使用して、タプルのリストを辞書に変換する
            area_dict = dict(pairs)
            return area_dict
        except Exception as e:
            print(e)
            return False

    def get_weather_forecast(self, area_code="130000"):

        # デフォルトでは東京地方のエリアコード
        # ![エリアコード](https://www.jma.go.jp/bosai/common/const/area.json)

        jma_url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"

        try:
            jma_json = requests.get(jma_url, timeout=3.0).json()
        except Timeout:
            return False

        except requests.exceptions.JSONDecodeError:
            return False

        # 各種情報取得
        # 当日=0 明日=1 明後日=2
        json_loc = 1

        jma_date = jma_json[0]["timeSeries"][0]["timeDefines"][json_loc]
        jma_area = jma_json[0]["timeSeries"][0]["areas"][0]["area"]["name"]
        jma_weather = jma_json[0]["timeSeries"][0]["areas"][0]["weathers"][json_loc]
        jma_wind = jma_json[0]["timeSeries"][0]["areas"][0]["winds"][json_loc]
        jma_publishingOffice = jma_json[0]["publishingOffice"]
        
        # 全角スペース削除
        jma_weather = jma_weather.replace('　', '')
        jma_wind = jma_wind.replace('　', '')

        # 時刻フォーマット
        # strptime()関数を使用して、文字列をdatetimeオブジェクトに変換する
        date_format = "%Y-%m-%dT%H:%M:%S%z"
        date_format_str = "%Y年%m月%d日%H時"
        jma_date = datetime.strptime(jma_date, date_format)
        jma_date = datetime.strftime(jma_date, date_format_str)

        # メッセージの作成
        result = self.create_message(jma_date, jma_area, jma_publishingOffice, jma_weather, jma_wind)
        return result
    
    def create_message(self, jma_date: str, jma_area: str, jma_publishingOffice: str, jma_weather: str, jma_wind: str) -> str:
        result = f"\
            {jma_date}の{jma_area}の天気予報をお知らせします。\
            気象台は{jma_publishingOffice}です。\
            天気は{jma_weather}です。\
            風の状況は{jma_wind}です。"
        
        return result
    
class OpenWeatherMap(WeatherForecast):
    def __init__(self):
        # 環境変数からAPIkeyを取得
        self.api_key = os.environ.get("OPEN_WEATHER_API_KEY")
        print(self.api_key)

    # 現在天気を取得
    def get_openweathermap_weaher(self, id="1850147"):
        url = f"http://api.openweathermap.org/data/2.5/weather?units=metric&id={id}&APPID={self.api_key}"
        result_json = requests.get(url, timeout=3.0).json()
        # print(result_json)
        temp = result_json["main"]["temp"]
        temp_max = result_json["main"]["temp_max"]
        temp_min = result_json["main"]["temp_min"]

        # 固定値
        p = "東京都"

        result = {
            "area": p,
            "temp": temp,
            "temp_max": temp_max,
            "temp_min": temp_min,
        }
        return result

    # 天気予報を取得
    def get_openweathermap_forecast(self, id="1850147"):
        url = f"http://api.openweathermap.org/data/2.5/forecast?units=metric&id={id}&APPID={self.api_key}"
        result_json = requests.get(url, timeout=3.0).json()

    def create_message(self, jma_date: str, jma_area: str, jma_publishingOffice: str, jma_weather: str, jma_wind: str) -> str:
        result = f"\
            {jma_date}の{jma_area}の天気予報をお知らせします。\
            気象台は{jma_publishingOffice}です。\
            天気は{jma_weather}です。\
            風の状況は{jma_wind}です。"
        
        # 現在の気温の取得
        temp_info = self.get_openweathermap_weaher()
        result += f"現在の{temp_info['area']}の気温は{temp_info['temp']}度です。\
            最高気温は{temp_info['temp_max']}度です。\
            最低気温は{temp_info['temp_min']}度です。"
        
        return result
    
# 中村さんそのボイスパックを購入したのでそれの試験。。。
class Sounds:
    def __init__(self, filename):
        self.filename = filename

    def playwavfile(self):
        try:
            wf = wave.open(self.filename, "r")
        except Exception as e:
            print(e)
            return False
            
        # ストリームを開く
        try:
            p = pyaudio.PyAudio()
            stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True)

            # 音声再生
            chunk = 1024
            data = wf.readframes(chunk)
            while len(data) > 0:
                stream.write(data)
                data = wf.readframes(chunk)
            stream.close()
            p.terminate()
            return 0

        except Exception as e:
            print(e)

# テスト用にJson取得結果をファイルに出力する。
def json_dump(jsondata, filename="./test.json"):
    try:
        with open(filename, 'w') as fp:
            json.dump(jsondata, fp, indent=4, ensure_ascii=False)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()
