from gtts import gTTS
import os

def text_to_speech(text, lang='en'):
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save("welcome.mp3")
    os.system("mpg321 welcome.mp3 >/dev/null 2>&1")