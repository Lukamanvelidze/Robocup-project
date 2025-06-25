## audio Processing + Whisper Speech Recognition

 captures microphone audio from the NAO robot, processes it using [OpenAI's Whisper](https://github.com/openai/whisper) speech-to-text model, and returns a list of recognized words.

---

##  Overview

- Captures live audio from the **front microphone** of the NAO robot using `ALAudioDevice`.
- Buffers a short audio segment (default: 50 frames).
- Saves the audio as a WAV file.
- Transcribes the audio using Whisper (`base` model by default).
- Outputs the result as a list of words.

---

##  Prerequisites

1. **Python+** 
2. **OpenAI Whisper** or [`faster-whisper`](https://github.com/guillaumekln/faster-whisper) for better performance
3. **NAOqi SDK** installed and configured
4. Access to a **NAO robot** or emulator with a running `naoqi` instance

---

## 🛠️ Installation

Clone the repo (or copy the file) and set up the environment:

```bash
pip install numpy openai-whisper
