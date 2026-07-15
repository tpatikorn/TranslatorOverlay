import queue
import numpy as np
import sounddevice as sd
import speech_recognition as sr
from PyQt6.QtCore import QThread, pyqtSignal, QRunnable, QThreadPool

from translator import translate_text
from logger import SessionLogger

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

            # Emit results to update overlay and control menu UI
            self.transcription_signal.emit(text, [t1, t2])

            # Log results (thread-safe logger handles checking for pause status)
            self.logger.log(text, t1, t2)
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
    transcription_updated = pyqtSignal(str, list)  # Emits (source_text, [translation1, translation2])
    status_updated = pyqtSignal(str)              # Emits status message (e.g. "Listening...", "Transcribing...")
    speech_state_changed = pyqtSignal(bool)       # Emits True when speaker is active, False when silent

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
                        # No audio chunk received, increment silence if we were speaking
                        if is_speaking:
                            silence_duration += 0.1
                            if silence_duration >= self.silence_limit:
                                self.finalize_segment(audio_buffer)
                                audio_buffer = []
                                is_speaking = False
                                silence_duration = 0.0
                                speech_duration = 0.0
                        continue

                    if self.is_paused:
                        continue

                    # Compute duration of current chunk
                    chunk_len = len(chunk)
                    duration = chunk_len / self.samplerate

                    # Compute RMS energy of this chunk to detect speech activity
                    rms = np.sqrt(np.mean(chunk ** 2))
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
