import sounddevice as sd
import soundfile as sf
import whisper

def speech_to_text(duration, samplerate=44100):
    # Record audio
    print("Recording...")
    filename = 'request.wav'
    mydata = sd.rec(int(samplerate * duration), samplerate=samplerate, channels=2, blocking=True)
    sf.write(filename, mydata, samplerate)
    print("Recording ended...")

    # Transcribe audio to text
    print("Transcribing audio...")
    model = whisper.load_model("tiny")
    result = model.transcribe(filename)
    print(result["text"])

    return result["text"]
