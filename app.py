#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram UserBot with Voice Chat TTS and Audio Playback
- Auto‑installs required libraries (pyrogram, tgcrypto, flask, edge‑tts, pytgcalls==3.0.0.dev24)
- Web‑based dark‑theme configuration when config.txt is missing
- .join command to join any group voice chat
- Text in Saved Messages → Tamil TTS (edge‑tts, +10% rate) played in joined VC
- Audio files (MP3 / voice) forwarded to Saved Messages played in VC
- Sends online confirmation to Saved Messages
- Checks for ffmpeg.exe in current directory (already present)
- Processes only new messages (no history loop)
- Fully compatible with pytgcalls==3.0.0.dev24 (uses InputStream & InputAudioStream)
"""

import os
import sys
import subprocess
import threading
import webbrowser
import tempfile
import asyncio

# ---------- AUTO INSTALLATION ----------
def install_missing_packages():
    required_packages = {
        'pyrogram': 'pyrogram',
        'tgcrypto': 'tgcrypto',
        'flask': 'flask',
        'edge_tts': 'edge-tts',
        'pytgcalls': 'pytgcalls==3.0.0.dev24'   # exact version for compatibility
    }
    for import_name, package_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            print(f"Installing {package_name}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])

install_missing_packages()

# Now safe to import
import pyrogram
from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask, request, render_template_string
import edge_tts
import tgcrypto  # not directly used, ensures crypto

# ---------- PYTGCALLS 3.0.0+ IMPORTS ----------
# Correct imports for pytgcalls==3.0.0.dev24
from pytgcalls import PyTgCalls
from pytgcalls.types import InputStream, InputAudioStream

# ---------- CONFIGURATION HANDLING ----------
CONFIG_FILE = 'config.txt'

def load_config():
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    return config

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        for key, value in config.items():
            f.write(f"{key}={value}\n")

# ---------- FLASK CONFIGURATION SERVER ----------
config_event = threading.Event()
config_data = {}

def run_config_server():
    app = Flask(__name__)

    HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram UserBot Configuration</title>
        <style>
            body { background: #1e1e2f; color: #e0e0e0; font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .container { background: #2a2a3b; padding: 2rem; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); width: 400px; }
            h1 { text-align: center; margin-bottom: 1.5rem; color: #bb86fc; }
            label { display: block; margin-top: 1rem; }
            input, select { width: 100%; padding: 0.5rem; background: #33334e; border: 1px solid #555; color: #e0e0e0; border-radius: 5px; margin-top: 0.25rem; }
            button { background: #bb86fc; color: #000; border: none; padding: 0.75rem; width: 100%; border-radius: 5px; font-size: 1rem; cursor: pointer; margin-top: 1.5rem; }
            button:hover { background: #a06ef0; }
            .note { font-size: 0.9rem; color: #aaa; margin-top: 1rem; text-align: center; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>UserBot Configuration</h1>
            <form method="post" action="/save">
                <label>API ID:</label>
                <input type="text" name="api_id" required>
                <label>API Hash:</label>
                <input type="text" name="api_hash" required>
                <label>String Session:</label>
                <input type="text" name="string_session" required>
                <label>Voice Selection:</label>
                <select name="voice">
                    <option value="ta-IN-ValluvarNeural">Male (ValluvarNeural)</option>
                    <option value="ta-IN-PallaviNeural">Female (PallaviNeural)</option>
                </select>
                <button type="submit">Save & Start Bot</button>
            </form>
            <div class="note">After saving, this window will close and the bot will start.</div>
        </div>
    </body>
    </html>
    """

    @app.route('/')
    def index():
        return render_template_string(HTML_TEMPLATE)

    @app.route('/save', methods=['POST'])
    def save():
        global config_data
        config_data = {
            'API_ID': request.form['api_id'],
            'API_HASH': request.form['api_hash'],
            'STRING_SESSION': request.form['string_session'],
            'VOICE': request.form['voice']
        }
        save_config(config_data)
        config_event.set()
        # Shutdown Flask server
        func = request.environ.get('werkzeug.server.shutdown')
        if func:
            func()
        return "Configuration saved. You may close this window."

    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)

# ---------- FFMPEG CHECK ----------
def check_ffmpeg():
    # We expect ffmpeg.exe in the current directory (as per user's project)
    ffmpeg_name = 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'
    if os.path.isfile(ffmpeg_name):
        # Add current directory to PATH so pytgcalls can find it
        current_dir = os.path.dirname(os.path.abspath(ffmpeg_name))
        os.environ['PATH'] = current_dir + os.pathsep + os.environ.get('PATH', '')
        return True
    # Also check system PATH as fallback
    import shutil
    if shutil.which(ffmpeg_name):
        return True
    raise RuntimeError(
        f"ffmpeg not found. Please ensure {ffmpeg_name} is in the current directory "
        "or available in your system PATH."
    )

# ---------- MAIN BOT LOGIC ----------
async def main():
    # Load or create configuration
    config = load_config()
    if not config:
        print("Configuration not found. Starting web setup...")
        server_thread = threading.Thread(target=run_config_server, daemon=True)
        server_thread.start()
        webbrowser.open('http://127.0.0.1:5000')
        config_event.wait()  # wait until config is saved
        config = load_config()
        print("Configuration saved. Starting bot...")

    # Verify ffmpeg presence (ffmpeg.exe in current directory)
    check_ffmpeg()

    # Create Pyrogram client with the provided session string
    client = Client(
        "userbot_session",
        api_id=int(config['API_ID']),
        api_hash=config['API_HASH'],
        session_string=config['STRING_SESSION']
    )

    # Initialize PyTgCalls for voice chat
    calls = PyTgCalls(client)
    await calls.start()

    current_group_id = None  # stores the chat ID of the VC we are in

    # ---------- HELPER: Play audio in current group ----------
    async def play_audio(source_path):
        nonlocal current_group_id
        if current_group_id is None:
            return
        try:
            # Create audio stream using InputStream + InputAudioStream (pytgcalls 3.0.0+)
            audio_source = InputStream(
                InputAudioStream(source_path),
            )
            # Use change_stream to play the audio in the current voice chat
            await calls.change_stream(current_group_id, audio_source)
        except Exception as e:
            print(f"Playback error: {e}")
        finally:
            # Delete temporary files after a delay to avoid interfering with playback
            asyncio.create_task(delete_file_after_delay(source_path, delay=10))

    # ---------- HANDLER: .join command ----------
    @client.on_message(filters.group & filters.text & ~filters.forwarded & filters.regex(r'^\.join$'))
    async def join_voice_chat(client: Client, message: Message):
        nonlocal current_group_id
        chat_id = message.chat.id
        try:
            # Leave previous VC if any
            if current_group_id:
                await calls.leave_group_call(current_group_id)
            # Join the new group's voice chat
            await calls.join_group_call(chat_id)
            current_group_id = chat_id
            await message.reply("✅ Joined voice chat.")
        except Exception as e:
            await message.reply(f"❌ Failed to join: {e}")

    # ---------- HANDLER: Saved Messages (text / audio) ----------
    @client.on_message(filters.chat('me') & ~filters.service)
    async def handle_saved_message(client: Client, message: Message):
        nonlocal current_group_id
        if current_group_id is None:
            return  # not in any voice chat, ignore

        # ----- TEXT MESSAGE -> TTS -----
        if message.text:
            text = message.text
            voice = config.get('VOICE', 'ta-IN-ValluvarNeural')  # default male
            try:
                # Generate speech with edge-tts
                tts = edge_tts.Communicate(text, voice, rate='+10%')
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                    temp_path = tmp.name
                await tts.save(temp_path)

                # Play in the voice chat
                await play_audio(temp_path)
            except Exception as e:
                print(f"TTS playback error: {e}")

        # ----- AUDIO / VOICE MESSAGE -----
        elif message.audio or message.voice:
            try:
                # Download the file
                file_path = await message.download()
                # Play in the voice chat
                await play_audio(file_path)
            except Exception as e:
                print(f"Audio playback error: {e}")

    # Helper to delete files after a delay (avoid interfering with playback)
    async def delete_file_after_delay(path, delay):
        await asyncio.sleep(delay)
        try:
            os.unlink(path)
        except:
            pass

    # ---------- START THE BOT ----------
    await client.start()
    await client.send_message("me", "✅ Bot is online and ready.")
    print("Bot is running. Press Ctrl+C to stop.")
    await pyrogram.idle()

    # Cleanup on exit
    await client.stop()
    await calls.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
