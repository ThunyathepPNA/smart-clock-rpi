import firebase_admin
from firebase_admin import credentials, db
import os
from google.cloud import texttospeech
import threading
import uuid
import time
from datetime import datetime

# --- Setup ---
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://smart-classroom-clock-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "serviceAccountKey.json"
client = texttospeech.TextToSpeechClient()

speak_lock = threading.Lock()

def speak(data):
    with speak_lock:
        try:
            text = data.get('message', '')
            lang = data.get('language', 'th')
            vol = data.get('volume', 70)
            
            if not text: return
            print(f"📢 Speaking: {text} | Lang: {lang}")
            
            # 1. ปรับระดับเสียง
            web_vol = int(vol)
            if web_vol <= 0:
                safe_vol = 0
            else:
                safe_vol = 70 + int((web_vol / 100.0) * 30)
                
            os.system(f"amixer set Master {safe_vol}% > /dev/null 2>&1")
            os.system(f"amixer set PCM {safe_vol}% > /dev/null 2>&1")
            
            # 2. เตรียมข้อความ
            synthesis_input = texttospeech.SynthesisInput(text=text)

            # 3. เลือกเสียง
            if lang == 'th':
                voice_name = "th-TH-Neural2-C" 
                language_code = "th-TH"
            else: 
                voice_name = "en-US-Neural2-C" 
                language_code = "en-US"

            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0
            )

            # 4. ยิง API ขอไฟล์เสียง
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )

            # 5. สร้างชื่อไฟล์แบบสุ่ม
            temp_file = f"announce_{uuid.uuid4().hex[:6]}.mp3"
            
            with open(temp_file, "wb") as out:
                out.write(response.audio_content)

            # 6. ใช้ mpg123 เล่นเสียง
            os.system(f"mpg123 -q silence.mp3 {temp_file}")
            
            # 7. เล่นเสร็จแล้วเคลียร์ทิ้ง
            if os.path.exists(temp_file):
                os.remove(temp_file) 
                
        except Exception as e:
            print(f"Error speaking: {e}")

def on_command(event):
    if event.data and isinstance(event.data, dict):
        speak(event.data)

# 🌟 ฟังก์ชันส่งชีพจร (Heartbeat) 🌟
def speaker_heartbeat():
    db.reference('/speaker/status').set('online')
    while True:
        try:
            current_time_ms = int(time.time() * 1000)
            db.reference('/speaker/last_seen').set(current_time_ms)
        except Exception as e:
            print(f"Heartbeat Error: {e}")
        
        time.sleep(60)

# 🌟 ฟังก์ชันเช็คตารางเวลาล่วงหน้า (แบบเดิม เสถียรสุด) 🌟
def check_schedule():
    while True:
        try:
            schedules = db.reference('/schedules').get()
            
            if schedules:
                now = datetime.now()
                current_time_str = now.strftime("%H:%M")
                
                for key, task in schedules.items():
                    if not isinstance(task, dict):
                        continue

                    if task.get('disabled') == True:
                        continue

                    if task.get('time') == current_time_str and not task.get('executed'):
                        message_text = task.get('text', '')
                        print(f"⏰ Executing scheduled task: {message_text}")
                        
                        brt = task.get('brightness', 8)
                        vol = task.get('volume', 70)

                        db.reference('/display/text').set(message_text)
                        db.reference('/display/brightness').set(brt)
                        db.reference('/config/volume').set(vol)
                        
                        speak_data = {
                            'message': message_text,
                            'language': 'th',
                            'volume': vol
                        }
                        threading.Thread(target=speak, args=(speak_data,)).start()
                        
                        db.reference(f'/schedules/{key}/executed').set(True)

        except Exception as e:
            print(f"Scheduler Error: {e}")
        
        # กลับไปใช้ดีเลย์ 30 วินาที เพื่อความเสถียร
        time.sleep(30)


print("🎧 Smart Speaker Ready (Reverted to Stable Version)")
print("Waiting for commands...")

threading.Thread(target=speaker_heartbeat, daemon=True).start()
threading.Thread(target=check_schedule, daemon=True).start()

try:
    db.reference('tts/command').listen(on_command)
except Exception as e:
    print(f"Connection Error: {e}")
