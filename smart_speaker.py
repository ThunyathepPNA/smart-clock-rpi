import firebase_admin
from firebase_admin import credentials, db
import os
from google.cloud import texttospeech
import threading
import uuid
import time
from datetime import datetime

# --- 1. Setup Firebase & Google Cloud ---
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://smart-classroom-clock-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "serviceAccountKey.json"
client = texttospeech.TextToSpeechClient()

# Lock ป้องกันการพูดซ้อนกัน
speak_lock = threading.Lock()

# --- 2. ฟังก์ชันหลักสำหรับพูด (TTS) ---
def speak(data):
    with speak_lock:
        try:
            text = data.get('message', '')
            lang = data.get('language', 'th')
            vol = data.get('volume', 70)
            
            if not text: return
            print(f"📢 Speaking: {text} | Lang: {lang} | Vol: {vol}%")
            
            # ปรับระดับเสียง
            web_vol = int(vol)
            safe_vol = 0 if web_vol <= 0 else 70 + int((web_vol / 100.0) * 30)
            os.system(f"amixer set Master {safe_vol}% > /dev/null 2>&1")
            os.system(f"amixer set PCM {safe_vol}% > /dev/null 2>&1")
            
            # เตรียมข้อความและเลือกเสียง
            synthesis_input = texttospeech.SynthesisInput(text=text)
            if lang == 'th':
                voice_name = "th-TH-Neural2-C" 
                language_code = "th-TH"
            else: 
                voice_name = "en-US-Neural2-C" 
                language_code = "en-US"

            voice = texttospeech.VoiceSelectionParams(language_code=language_code, name=voice_name)
            audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=1.0)

            # ยิง API ขอไฟล์เสียง
            response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)

            # สร้างไฟล์และเล่นเสียง
            temp_file = f"announce_{uuid.uuid4().hex[:6]}.mp3"
            with open(temp_file, "wb") as out:
                out.write(response.audio_content)

            os.system(f"mpg123 -q silence.mp3 {temp_file}")
            
            # ลบไฟล์ทิ้งหลังเล่นเสร็จ
            if os.path.exists(temp_file):
                os.remove(temp_file) 
                
        except Exception as e:
            print(f"❌ Error speaking: {e}")

# --- 3. ฟังก์ชันรับคำสั่งประกาศทันที (Quick Announce) ---
def on_command(event):
    if event.data and isinstance(event.data, dict):
        # รันใน Thread ใหม่จะได้ไม่บล็อกการฟัง
        threading.Thread(target=speak, args=(event.data,)).start()

# --- 4. ฟังก์ชันส่งชีพจร (Heartbeat) ---
def speaker_heartbeat():
    db.reference('/speaker/status').set('online')
    while True:
        try:
            current_time_ms = int(time.time() * 1000)
            db.reference('/speaker/last_seen').set(current_time_ms)
        except Exception as e:
            print(f"❌ Heartbeat Error: {e}")
        time.sleep(60)

# --- 5. ฟังก์ชันตั้งเวลาล่วงหน้า (Scheduler แบบมี Cache) ---
def check_schedule():
    cached_schedules = {}
    last_fetch_time = 0
    
    while True:
        try:
            current_timestamp = time.time()
            now = datetime.now()
            current_time_str = now.strftime("%H:%M") 
            
            # ดึงข้อมูลจากเน็ตทุกๆ 30 วินาที
            if current_timestamp - last_fetch_time > 30:
                fetched_data = db.reference('/schedules').get()
                if fetched_data:
                    cached_schedules = fetched_data
                last_fetch_time = current_timestamp

            # เช็คเวลาจาก Cache ทุกๆ 1 วินาที
            if cached_schedules:
                for key, task in cached_schedules.items():
                    if not isinstance(task, dict) or task.get('disabled') == True:
                        continue

                    # ถ้าเวลาตรงเป๊ะ และยังไม่ได้รัน
                    if task.get('time') == current_time_str and not task.get('executed'):
                        message_text = task.get('text', '')
                        print(f"⏰ Executing scheduled task: {message_text}")
                        
                        brt = task.get('brightness', 8)
                        vol = task.get('volume', 70)

                        # สั่งจอ ESP32
                        db.reference('/display/text').set(message_text)
                        db.reference('/display/brightness').set(brt)
                        db.reference('/config/volume').set(vol)
                        
                        # สั่งลำโพง
                        speak_data = {
                            'message': message_text,
                            'language': 'th',
                            'volume': vol
                        }
                        threading.Thread(target=speak, args=(speak_data,)).start()
                        
                        # อัปเดตสถานะว่าทำแล้ว
                        db.reference(f'/schedules/{key}/executed').set(True)
                        cached_schedules[key]['executed'] = True

        except Exception as e:
            print(f"❌ Scheduler Error: {e}")
            last_fetch_time = 0 # รีเซ็ตให้ดึงข้อมูลใหม่
        
        time.sleep(1) # หลับ 1 วินาทีเพื่อไม่ให้กิน CPU

# --- เริ่มทำงาน ---
print("🎧 Smart Speaker Ready (Final Version)")
print("Waiting for commands...")

# เปิด Thread การทำงานคู่ขนาน
threading.Thread(target=speaker_heartbeat, daemon=True).start()
threading.Thread(target=check_schedule, daemon=True).start()

# ดักฟังคำสั่ง Quick Announce
try:
    db.reference('tts/command').listen(on_command)
except Exception as e:
    print(f"❌ Connection Error: {e}")
