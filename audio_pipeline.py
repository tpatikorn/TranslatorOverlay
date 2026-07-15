import os
import json
import zipfile
import urllib.request
import shutil
import queue
import numpy as np
import sounddevice as sd
import speech_recognition as sr
from PyQt6.QtCore import QThread, pyqtSignal, QRunnable, QThreadPool

from translator import translate_text
from logger import SessionLogger

class TranslationWorker(QRunnable):
    """
    Worker runnable that handles deep-translator translations for pre-transcribed text.
    Runs in a background thread from the global thread pool to avoid blocking the main audio thread.
    """
    def __init__(self, text, source_lang, target_lang1, target_lang2,
                 transcription_signal, status_signal, logger):
        super().__init__()
        self.text = text
        self.source_lang = source_lang
        self.target_lang1 = target_lang1
        self.target_lang2 = target_lang2
        self.transcription_signal = transcription_signal
        self.status_signal = status_signal
        self.logger = logger

    def run(self):
        if not self.text.strip():
            return

        try:
            self.status_signal.emit("Translating...")

            # Perform translations
            t1 = ""
            if self.target_lang1:
                t1 = translate_text(self.text, src=self.source_lang, trg=self.target_lang1)

            t2 = ""
            if self.target_lang2:
                t2 = translate_text(self.text, src=self.source_lang, trg=self.target_lang2)

            # Emit results to update overlay and control menu UI (True for final)
            self.transcription_signal.emit(self.text, [t1, t2], True)

            # Log results
            self.logger.log(
                src_text=self.text, src_lang=self.source_lang,
                trg1_text=t1, trg1_lang=self.target_lang1,
                trg2_text=t2, trg2_lang=self.target_lang2
            )
            self.status_signal.emit("Listening...")

        except Exception as e:
            self.logger.log(f"Error in translation worker: {e}")
            self.status_signal.emit(f"Error in translation worker: {e}")


class TranscriptionWorker(QRunnable):
    """
    Worker runnable that handles Google Web Speech Recognition and deep-translator.
    Runs in a background thread from the global thread pool to avoid blocking the main audio thread.
    """
    def __init__(self, audio_data, samplerate, source_lang, target_lang1, target_lang2,
                 transcription_signal, status_signal, logger):
        super().__init__()
        self.audio_data = audio_data
        self.samplerate = samplerate
        self.source_lang = source_lang
        self.target_lang1 = target_lang1
        self.target_lang2 = target_lang2
        self.transcription_signal = transcription_signal
        self.status_signal = status_signal
        self.logger = logger

    def run(self):
        if len(self.audio_data) == 0:
            return

        # Convert float32 numpy array to 16-bit PCM raw data
        # Normalize to prevent clipping and convert to int16
        max_val = np.max(np.abs(self.audio_data))
        if max_val > 0:
            normalized = self.audio_data / max_val
        else:
            normalized = self.audio_data

        audio_int16 = (normalized * 32767).astype(np.int16)
        raw_bytes = audio_int16.tobytes()

        # Construct speech_recognition AudioData object
        audio_obj = sr.AudioData(raw_bytes, sample_rate=self.samplerate, sample_width=2)
        recognizer = sr.Recognizer()

        try:
            self.status_signal.emit("Transcribing...")

            # Call Google Web Speech API (free, highly accurate for Thai)
            text = recognizer.recognize_google(audio_obj, language=self.source_lang)
            text = text.strip()

            if not text:
                self.status_signal.emit("Listening...")
                return

            self.status_signal.emit("Translating...")

            # Perform translations
            t1 = ""
            if self.target_lang1:
                t1 = translate_text(text, src=self.source_lang, trg=self.target_lang1)

            t2 = ""
            if self.target_lang2:
                t2 = translate_text(text, src=self.source_lang, trg=self.target_lang2)

            # Emit results to update overlay and control menu UI (True for final)
            self.transcription_signal.emit(text, [t1, t2], True)

            # Log results (thread-safe logger handles checking for pause status)
            self.logger.log(
                src_text=text, src_lang=self.source_lang,
                trg1_text=t1, trg1_lang=self.target_lang1,
                trg2_text=t2, trg2_lang=self.target_lang2
            )
            self.status_signal.emit("Listening...")

        except sr.UnknownValueError:
            # Sound was unintelligible, reset status to Listening
            self.status_signal.emit("Listening...")
        except sr.RequestError as e:
            self.logger.log(f"Speech recognition request error: {e}")
            self.status_signal.emit(f"Speech recognition request error: {e}")
        except Exception as e:
            self.logger.log(f"Error in transcription worker: {e}")
            self.status_signal.emit(f"Error in transcription worker: {e}")


class AudioPipelineThread(QThread):
    """
    QThread that streams microphone audio using sounddevice and analyzes sound levels.
    When a speech segment is followed by silence, it packages the audio and sends it to the thread pool.
    """
    transcription_updated = pyqtSignal(str, list, bool)  # Emits (source_text, [translation1, translation2], is_final)
    status_updated = pyqtSignal(str)              # Emits status message (e.g. "Listening...", "Transcribing...")
    speech_state_changed = pyqtSignal(bool)       # Emits True when speaker is active, False when silent
    volume_updated = pyqtSignal(float)            # Emits current volume level (0.0 to 1.0)

    def __init__(self, config: dict, logger: SessionLogger):
        super().__init__()
        self.config = config
        self.logger = logger

        self.running = False
        self.is_paused = False
        self.audio_queue = queue.Queue()

        # Audio capturing parameters
        self.samplerate = 16000
        self.channels = 1

        # Settings
        self.silence_threshold = 0.01  # Root-Mean-Square threshold for speech vs silence
        self.silence_limit = 1.3       # Seconds of silence before segmenting
        self.max_duration = 15.0       # Max seconds per segment to prevent memory build-up

    def set_paused(self, paused: bool):
        """Pause or resume audio queue processing."""
        self.is_paused = paused
        if paused:
            self.status_updated.emit("Paused")
            # Drain the queue to prevent stale audio from playing back on resume
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break
        else:
            self.status_updated.emit("Listening...")

    def update_config(self, new_config: dict):
        """Update configurations on the fly."""
        self.config = new_config

    def stop(self):
        """Safely terminate the audio recording and worker thread loop."""
        self.running = False
        self.wait()

    def run(self):
        self.running = True

        # Drain queue initially
        while not self.audio_queue.empty():
            self.audio_queue.get()

        def sd_callback(indata, frames, time_info, status):
            """Stream callback for sounddevice InputStream."""
            if status:
                print(f"sounddevice callback status: {frames} {time_info} {status}")
            if self.running and not self.is_paused:
                self.audio_queue.put(indata.copy())

        # Check configured input device
        device_idx = self.config.get("device_index")
        if device_idx is not None:
            # Validate device index
            try:
                sd.query_devices(device=device_idx, kind='input')
            except Exception as e:
                print(f"Configured audio device index {device_idx} invalid: {e}. Using default.")
                device_idx = None

        # Determine ASR engine & prepare models if Vosk is selected
        asr_engine = self.config.get("asr_engine", "google")
        src_lang = self.config.get("source_lang", "th")
        
        vosk_model = None
        vosk_recognizer = None
        
        if asr_engine == "vosk":
            # Vosk only supports Thai and English for our pre-configured models
            # Standardize source language. If it is auto, we default to th for Vosk
            lang = src_lang.lower().split("-")[0]
            if lang == "auto":
                lang = "th"
                
            if lang not in ("th", "en"):
                self.status_updated.emit("Vosk Unsupported Lang")
                self.transcription_updated.emit(
                    f"Vosk does not support source language '{src_lang}'.",
                    ["Falling back to Google Web Speech...", ""],
                    True
                )
                asr_engine = "google"
            else:
                # Ensure models/ directory exists
                os.makedirs("models", exist_ok=True)
                
                # Set up download details based on language
                if lang == "th":
                    model_path = os.path.join("models", "vosk-model-th")
                    download_url = "https://github.com/vistec-AI/commonvoice-th/releases/download/vosk-v1/model.zip"
                    zip_name = os.path.join("models", "vosk_model_thai.zip")
                else: # en
                    model_path = os.path.join("models", "vosk-model-en-us")
                    download_url = "https://alphacephei.com/kaldi/models/vosk-model-small-en-us-0.15.zip"
                    zip_name = os.path.join("models", "vosk_model_en.zip")
                
                # Check model availability and download if needed
                if not os.path.exists(model_path):
                    self.status_updated.emit("Downloading Vosk Model...")
                    self.transcription_updated.emit(
                        f"Downloading Vosk {lang.upper()} model (~40-100MB)... Please wait.",
                        ["This download only happens once.", ""],
                        True
                    )
                    try:
                        temp_extract = os.path.join("models", "vosk_temp_extract")
                        os.makedirs(temp_extract, exist_ok=True)
                        
                        # Download using urllib
                        urllib.request.urlretrieve(download_url, zip_name)
                        
                        # Extract
                        with zipfile.ZipFile(zip_name, 'r') as zip_ref:
                            zip_ref.extractall(temp_extract)
                            
                        # Search for the folder that actually contains 'am' and 'graph' directories
                        actual_dir = None
                        for root, dirs, files in os.walk(temp_extract):
                            if "am" in dirs and "graph" in dirs:
                                actual_dir = root
                                break
                                
                        if actual_dir:
                            if os.path.exists(model_path):
                                shutil.rmtree(model_path)
                            shutil.move(actual_dir, model_path)
                            
                        # Cleanup temp files
                        shutil.rmtree(temp_extract)
                        if os.path.exists(zip_name):
                            os.remove(zip_name)
                            
                        self.transcription_updated.emit("Model download complete.", ["Initializing...", ""], True)
                    except Exception as e:
                        print(f"Error downloading Vosk model: {e}")
                        self.status_updated.emit("Download Failed")
                        self.transcription_updated.emit(
                            f"Failed to download Vosk model: {e}",
                            ["Falling back to Google Web Speech...", ""],
                            True
                        )
                        asr_engine = "google"
                        if os.path.exists(zip_name):
                            os.remove(zip_name)
                        if os.path.exists(temp_extract):
                            shutil.rmtree(temp_extract)
                
                # Initialize model
                if asr_engine == "vosk" and os.path.exists(model_path):
                    self.status_updated.emit("Loading Vosk Model...")
                    try:
                        from vosk import Model, KaldiRecognizer
                        vosk_model = Model(model_path)
                        vosk_recognizer = KaldiRecognizer(vosk_model, self.samplerate)
                        self.status_updated.emit("Listening...")
                        self.transcription_updated.emit("Vosk engine ready.", ["Listening...", ""], True)
                    except Exception as e:
                        print(f"Error loading Vosk model: {e}")
                        self.status_updated.emit("Load Failed")
                        self.transcription_updated.emit(
                            f"Error loading Vosk model: {e}",
                            ["Falling back to Google Web Speech...", ""],
                            True
                        )
                        asr_engine = "google"

        self.status_updated.emit("Listening...")

        try:
            with sd.InputStream(samplerate=self.samplerate,
                                channels=self.channels,
                                dtype='float32',
                                device=device_idx,
                                callback=sd_callback):

                audio_buffer = []
                is_speaking = False
                silence_duration = 0.0
                speech_duration = 0.0

                while self.running:
                    try:
                        # Pull chunk from queue (timeout allows loop to check self.running)
                        chunk = self.audio_queue.get(timeout=0.1)
                    except queue.Empty:
                        # No audio chunk received
                        if asr_engine == "google" and is_speaking:
                            silence_duration += 0.1
                            if silence_duration >= self.silence_limit:
                                self.finalize_segment(audio_buffer)
                                audio_buffer = []
                                is_speaking = False
                                silence_duration = 0.0
                                speech_duration = 0.0
                        self.volume_updated.emit(0.0)
                        continue

                    if self.is_paused:
                        self.volume_updated.emit(0.0)
                        continue

                    # Calculate RMS energy for the sound volume indicator
                    rms = np.sqrt(np.mean(chunk ** 2))
                    
                    # Normalize RMS to 0.0 - 1.0 for UI visual progress bar.
                    # Normal speech peaks around 0.01 - 0.08. Noise gate at 0.002.
                    vol_level = 0.0
                    if rms > 0.002:
                        vol_level = min(1.0, (rms - 0.002) / 0.08)
                    self.volume_updated.emit(vol_level)

                    if asr_engine == "vosk" and vosk_recognizer is not None:
                        # Convert float32 numpy array to 16-bit PCM raw data for Vosk
                        audio_int16 = np.clip(chunk * 32767, -32768, 32767).astype(np.int16)
                        raw_bytes = audio_int16.tobytes()
                        
                        if vosk_recognizer.AcceptWaveform(raw_bytes):
                            result = json.loads(vosk_recognizer.Result())
                            text = result.get("text", "").strip()
                            if text:
                                # Trigger background thread translations
                                trg1 = self.config.get("target_lang1", "en")
                                trg2 = self.config.get("target_lang2", "")
                                lang = src_lang.lower().split("-")[0]
                                if lang == "auto":
                                    lang = "th"
                                    
                                worker = TranslationWorker(
                                    text=text,
                                    source_lang=lang,
                                    target_lang1=trg1,
                                    target_lang2=trg2,
                                    transcription_signal=self.transcription_updated,
                                    status_signal=self.status_updated,
                                    logger=self.logger
                                )
                                QThreadPool.globalInstance().start(worker)
                        else:
                            # Stream partial transcriptions in real time (False for partial)
                            partial = json.loads(vosk_recognizer.PartialResult())
                            text = partial.get("partial", "").strip()
                            if text:
                                self.transcription_updated.emit(text, ["", ""], False)
                    else:
                        # Google Web Speech engine (VAD segmentation)
                        chunk_len = len(chunk)
                        duration = chunk_len / self.samplerate
                        is_silent = rms < self.silence_threshold

                        if not is_speaking:
                            if not is_silent:
                                is_speaking = True
                                self.speech_state_changed.emit(True)
                                self.status_updated.emit("Listening...")
                                audio_buffer.append(chunk)
                                silence_duration = 0.0
                                speech_duration = duration
                        else:
                            audio_buffer.append(chunk)
                            speech_duration += duration
                            if is_silent:
                                silence_duration += duration
                            else:
                                silence_duration = 0.0

                            # Check segment end boundaries
                            if silence_duration >= self.silence_limit or speech_duration >= self.max_duration:
                                self.finalize_segment(audio_buffer)
                                audio_buffer = []
                                is_speaking = False
                                silence_duration = 0.0
                                speech_duration = 0.0

        except Exception as e:
            self.status_updated.emit("Audio Error")
            print(f"Error in sounddevice InputStream context: {e}")

    def finalize_segment(self, audio_buffer):
        """Concatenates the buffer and submits a TranscriptionWorker to the thread pool."""
        self.speech_state_changed.emit(False)
        if not audio_buffer:
            return

        full_audio = np.concatenate(audio_buffer, axis=0).flatten()

        # Pull latest language configurations
        src_lang = self.config.get("source_lang", "th")
        trg1 = self.config.get("target_lang1", "en")
        trg2 = self.config.get("target_lang2", "")

        # Instantiate and queue QRunnable worker
        worker = TranscriptionWorker(
            audio_data=full_audio,
            samplerate=self.samplerate,
            source_lang=src_lang,
            target_lang1=trg1,
            target_lang2=trg2,
            transcription_signal=self.transcription_updated,
            status_signal=self.status_updated,
            logger=self.logger
        )
        QThreadPool.globalInstance().start(worker)
