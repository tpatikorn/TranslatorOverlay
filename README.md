# Translator Overlay

A real-time, premium translucent subtitle overlay and translator for speakers, lecturers, or streamers. It captures speech from your microphone, displays live subtitles on the screen, translates them in real-time into up to two target languages, and stores a timestamped session log.

---

## Key Features

1. **Dual ASR Engines**:
   - **Google Web Speech (Cloud)**:
     - *How it works*: Captures complete phrases using Voice Activity Detection (VAD) and transcribes them once a pause is detected.
     - *Strengths*: Highly accurate transcription, especially for proper nouns, names, and complex vocabulary.
   - **Vosk (Local Streaming)**:
     - *How it works*: Runs entirely offline. It transcribes in real-time, showing words on your screen **as you speak**. 
     - *Strengths*: Instant visual feedback with zero network latency. Translations are completed automatically as soon as a finalized phrase boundary is detected.
2. **Visual Sound Level Indicator**:
   - A cellular-signal-strength style bar (5 cyan progress segments) on the menu bar showing microphone sound volume and voice detection.
3. **Highly Customizable Overlay**:
   - Change font family, sizing, background color, background opacity, screen bottom offsets, text alignment, and history length on the fly.
4. **Auto-Downloading Models**:
   - Select the Vosk engine, and the application automatically downloads the appropriate language model (Thai VISTEC model or English small model) to your machine.
5. **Session Logger**:
   - Writes all original transcriptions and their translations to a clean, timestamped log file under `logs/`.

---

## Installation & Setup

Ensure you have **Python 3.8+** installed.

### 1. Set Up Virtual Environment (Recommended)
Open a terminal in the project directory and run:
```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install Requirements
Install all dependencies using `pip`:
```powershell
pip install -r requirements.txt
```

If you plan to use the **Vosk** offline engine, you must also install the `vosk` package:
```powershell
pip install vosk
```

*(Note: The main application and test scripts will check for dependencies on startup and prompt you if anything is missing.)*

---

## Running the Application

To run the main application overlay:
```powershell
python main.py
```
*(If you are using the virtual environment, execute `.venv\Scripts\python main.py`.)*

### Controls
* **Control Menu**: Hover over or click the floating menu bar to raise its opacity.
* **Pause / Resume**: Pause audio logging and transcription at any time.
* **Settings**: Open the settings panel to change languages, sound input devices, ASR engine choice, and subtitle styling parameters.
* **Exit**: Stops background threads and exits cleanly.

---

## Testing Vosk Accuracy Individually

If you want to test Vosk's real-time accuracy and performance for Thai independently of the main GUI:
```powershell
python test_vosk_thai.py
```
This utility script will check for required libraries (`vosk` and `sounddevice`), download the Thai model, and print live transcription chunks inside your terminal window.
