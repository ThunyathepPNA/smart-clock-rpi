```markdown
# 📢 Smart Classroom Clock (Raspberry Pi Smart Speaker)

This repository contains the Python script running on the Raspberry Pi. It acts as the "Smart Speaker" for the Smart Classroom Clock system, fetching schedules from Firebase, generating speech via Google Cloud TTS, and sending display states to the ESP32 via Firebase Realtime Database.

## 🚀 Features
- **Real-time TTS**: Listens for instant announcement commands.
- **Smart Scheduler**: Caches schedules and executes them down to the exact second.
- **Heartbeat System**: Periodically updates its `last_seen` timestamp in Firebase to confirm online status.
- **Hardware Integration**: Dynamically adjusts ALSA volume levels and plays `.mp3` directly via `mpg123`.

## 🛠️ Prerequisites
- Python 3.x
- `mpg123` audio player (for playing TTS files)
- Google Cloud Service Account credentials

## ⚙️ Installation

**Install System Dependencies:**
   Install `mpg123` to handle MP3 playback on the Raspberry Pi:
   ```bash
   sudo apt-get update
   sudo apt-get install mpg123

1.Install Python Libraries:
Since there is no requirements.txt, install the required packages manually:
  pip install firebase-admin google-cloud-texttospeech

2. Authentication Setup:
Place your Google Cloud / Firebase service account JSON key in the root directory of this project and name it exactly:
serviceAccountKey.json

Running the Application
Manual Run:
To start the script manually for testing:
  python smart_speaker.py
Run Automatically on Boot (via systemd):
To ensure the speaker system starts automatically every time the Raspberry Pi turns on:

1.Create a new systemd service file:
  sudo nano /etc/systemd/system/smart-speaker.service

2.Add the following configuration (Adjust WorkingDirectory and ExecStart paths to match your setup):
  [Unit]
  Description=Smart Classroom Speaker Service
  After=network.target

  [Service]
  Type=simple
  User=pi
  WorkingDirectory=/home/pi/smart-clock-rpi
  ExecStart=/usr/bin/python3 /home/pi/smart-clock-rpi/smart_speaker.py
  Restart=always
  RestartSec=10

  [Install]
  WantedBy=multi-user.target

3. Enable and start the service:
  sudo systemctl daemon-reload
  sudo systemctl enable smart-speaker.service
  sudo systemctl start smart-speaker.service

4.Check the status and logs:
  sudo systemctl status smart-speaker.service
  journalctl -u smart-speaker.service -f
