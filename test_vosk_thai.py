import os
import sys
import json
import queue
import zipfile
import urllib.request

# Configuration
MODEL_URL = "https://github.com/vistec-AI/commonvoice-th/releases/download/vosk-v1/model.zip"
EXTRACT_DIR = os.path.join("models", "vosk-model-th")

# 1. Dependency checks
try:
    import sounddevice as sd
except ImportError:
    print("Error: 'sounddevice' library is not installed.")
    print("Please install it by running: pip install sounddevice")
    sys.exit(1)

try:
    from vosk import Model, KaldiRecognizer
except ImportError:
    print("Error: 'vosk' library is not installed.")
    print("Please install it by running: pip install vosk")
    sys.exit(1)

# 2. Download and extract model if not present
def find_model_dir(start_path):
    """Finds the directory containing Kaldi model files (usually 'am' and 'graph')."""
    for root, dirs, files in os.walk(start_path):
        if "am" in dirs and "graph" in dirs:
            return root
    return None

model_path = find_model_dir(EXTRACT_DIR)

if not model_path:
    print("Vosk Thai model not found locally.")
    print(f"Downloading model from {MODEL_URL} (this may take a minute)...")
    zip_path = "vosk_model_thai.zip"
    try:
        # Download the file
        urllib.request.urlretrieve(MODEL_URL, zip_path)
        print("Download complete. Extracting files...")
        
        # Extract the file
        os.makedirs(EXTRACT_DIR, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(EXTRACT_DIR)
            
        print("Extraction complete.")
    except Exception as e:
        print(f"Failed to download or extract model: {e}")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        sys.exit(1)
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)

    # Locate the model directory again after extraction
    model_path = find_model_dir(EXTRACT_DIR)
    if not model_path:
        print("Error: Could not locate the Kaldi model directory within the extracted files.")
        sys.exit(1)

print(f"Using Vosk model located at: {model_path}")

# 3. Audio capturing and recognition loop
audio_queue = queue.Queue()

def audio_callback(indata, frames, time, status):
    """Callback for sounddevice RawInputStream."""
    if status:
        print(status, file=sys.stderr)
    audio_queue.put(bytes(indata))

try:
    # Initialize Vosk Model
    print("Loading model into memory...")
    model = Model(model_path)
    
    # Query default input device sample rate
    device_info = sd.query_devices(None, 'input')
    samplerate = int(device_info['default_samplerate'])
    print(f"Using default input device: {device_info['name']} (Sample Rate: {samplerate}Hz)")
    
    # Initialize Recognizer
    recognizer = KaldiRecognizer(model, samplerate)
    
    # Start audio stream
    # Vosk expects 16-bit mono PCM audio
    with sd.RawInputStream(samplerate=samplerate, blocksize=4000, device=None, dtype='int16',
                           channels=1, callback=audio_callback):
        print("\n========================================================")
        print("Listening... Speak in Thai to test. Press Ctrl+C to stop.")
        print("========================================================\n")
        
        while True:
            data = audio_queue.get()
            if recognizer.AcceptWaveform(data):
                # When a full utterance is recognized (detected pause)
                result = json.loads(recognizer.Result())
                text = result.get("text", "")
                if text:
                    print(f"\n[Final]: {text}\n")
            else:
                # When speaking (interim/partial results)
                partial = json.loads(recognizer.PartialResult())
                text = partial.get("partial", "")
                if text:
                    # Print partial results on the same line to simulate streaming
                    sys.stdout.write(f"\r[Partial]: {text}")
                    sys.stdout.flush()

except KeyboardInterrupt:
    print("\n\nTesting stopped by user.")
except Exception as e:
    print(f"\nAn error occurred during execution: {e}")
