import os
import sys
import subprocess
import threading
import webbrowser
import tempfile
import asyncio

# ==============================================================================
# 1. ஆட்டோ-இன்ஸ்டாலர் (இதைக் கிளிக் செய்தாலே எல்லாம் இன்ஸ்டால் ஆகும்)
# ==============================================================================
def auto_install():
    # EXE அல்லது கிட்ஹப்பில் ஓடும்போது தேவையில்லாத செக்
    if getattr(sys, 'frozen', False): return

    print("🔄 தேவையானவற்றைச் சரிபார்க்கிறேன்... தயவுசெய்து காத்திருக்கவும்.")
    packages = {
        'pyrogram': 'pyrogram',
        'tgcrypto': 'tgcrypto',
        'flask': 'flask',
        'edge_tts': 'edge-tts',
        'pytgcalls': 'pytgcalls==3.0.0.dev24'
    }
    for imp_name, pkg_name in packages.items():
        try:
            __import__(imp_name)
        except ImportError:
            print(f"⬇️ {pkg_name} இன்ஸ்டால் ஆகிறது...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg_name])

auto_install()

# இப்போது முக்கியமானவற்றை இம்போர்ட் செய்கிறோம்
from pyrogram import Client, filters
from flask import Flask, request, render_template_string
import edge_tts

# PyTgCalls 3.0.0.dev24 க்கான சரியான இம்போர்ட் முறை
try:
    from pytgcalls import PyTgCalls
    from pytgcalls.types import InputStream, InputAudioStream
except ImportError:
    from pytgcalls.client import PyTgCalls
    from pytgcalls.types import InputStream, InputAudioStream

# ==============================================================================
# 2. வெப் டேஷ்போர்டு (Browser Setup)
# ==============================================================================
CONFIG_FILE = 'config.txt'
config_event = threading.Event()

def run_web_setup():
    app = Flask(__name__)
    HTML = """
    <body style="background:#0f172a;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;">
        <div style="background:#1e293b;padding:30px;border-radius:15px;width:350px;box-shadow:0 10px 25px rgba(0,0,0,0.5);">
            <h2 style="color:#38bdf8;text-align:center;">🎙️ Subeesh Voice Bot</h2>
            <form method="post" action="/save">
                <input style="width:100%;padding:10px;margin:10px 0;background:#0f172a;border:1px solid #334155;color:#fff;" type="text" name="api_id" placeholder="API ID" required>
                <input style="width:100%;padding:10px;margin:10px 0;background:#0f172a;border:1px solid #334155;color:#fff;" type="text" name="api_hash" placeholder="API Hash" required>
                <input style="width:100%;padding:10px;margin:10px 0;background:#0f172a;border:1px solid #334155;color:#fff;" type="text" name="string_session" placeholder="String Session" required>
                <select style="width:100%;padding:10px;margin:10px 0;background:#0f172a;color:#fff;" name="voice">
                    <option value="ta-IN-ValluvarNeural">ஆண் குரல் (வள்ளுவர்)</option>
                    <option value="ta-IN-PallaviNeural">பெண் குரல் (பல்லவி)</option>
                </select>
                <button style="width:100%;padding:12px;background:#0ea5e9;border:none;border-radius:5px;font-weight:bold;cursor:pointer;" type="submit">பாட்டைத் தொடங்கு 🚀</button>
            </form>
        </div>
    </body>
    """
    @app.route('/')
    def index(): return render_template_string(HTML)
    
    @app.route('/save', methods=['POST'])
    def save():
        with open(CONFIG_FILE, 'w') as f:
            f.write(f"API_ID={request.form['api_id']}\nAPI_HASH={request.form['api_hash']}\nSESSION={request.form['string_session']}\nVOICE={request.form['voice']}")
        config_event.set()
        return "<h1>✅ செட்டப் முடிந்தது! இந்த பக்கத்தை மூடலாம்.</h1>"
    
    app.run(port=5000)

# ==============================================================================
# 3. பாட் லாஜிக் (Core Logic)
# ==============================================================================
async def main():
    if not os.path.exists(CONFIG_FILE):
        print("🌍 செட்டப் பக்கம் திறக்கிறது...")
        threading.Thread(target=run_web_setup, daemon=True).start()
        await asyncio.sleep(2)
        webbrowser.open('http://127.0.0.1:5000')
        config_event.wait()

    # கான்பிக் படித்தல்
    config = {}
    with open(CONFIG_FILE, 'r') as f:
        for line in f:
            k, v = line.strip().split('=')
            config[k] = v

    # FFmpeg பாத் செட் செய்தல்
    if os.path.exists('ffmpeg.exe'):
        os.environ['PATH'] += os.pathsep + os.getcwd()

    bot = Client("subeesh_bot", api_id=int(config['API_ID']), api_hash=config['API_HASH'], session_string=config['SESSION'])
    calls = PyTgCalls(bot)
    await calls.start()
    
    group_id = None

    @bot.on_message(filters.me & filters.regex(r'^\.join$'))
    async def join_vc(_, m):
        nonlocal group_id
        group_id = m.chat.id
        await calls.join_group_call(group_id)
        await m.reply("✅ குரூப் வாய்ஸ் சேட்டில் இணைந்தாச்சு!")

    @bot.on_message(filters.chat('me') & filters.text)
    async def speak(_, m):
        if not group_id or m.text.startswith("."): return
        
        # தமிழ் பேச்சு (TTS)
        tts = edge_tts.Communicate(m.text, config['VOICE'], rate='+12%')
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp: path = tmp.name
        await tts.save(path)

        try:
            await calls.change_stream(group_id, InputStream(InputAudioStream(path)))
            await m.reply(f"🔊 பேசுவது: {m.text}")
        except: pass

    print("🚀 பாட் ஆன்லைனில் உள்ளது!")
    await bot.start()
    await bot.send_message("me", "✅ **பாட் தயாராகிவிட்டது!**\nகுரூப்பில் சென்று `.join` என டைப் செய்யவும்.")
    await pyrogram.idle()

if __name__ == "__main__":
    asyncio.run(main())