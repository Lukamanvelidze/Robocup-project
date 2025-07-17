#  NAO Plays Marco Polo

This project aims to make the NAO humanoid robot play the game **Marco Polo** in the **"Marco" role**.

---

## Project Overview

The robot will detect when a human responds with the word **"Polo"**, determine the direction of the sound, move toward the target, and finally stop after hearing a keyword "stop".

---
### Cross-Version Architecture:

Due to hardware limitations of the NAO robot:

- The robot software uses **Python 2.7** to interface with **NAOqi**, the proprietary middleware required to access NAO's microphones, audio streams, and motion APIs.
- We also use Whisper AI, which provides robust keyword recognition, requires **Python 3.8+** to run efficiently with modern libraries like PyTorch.

To bridge these two environments:

- We implement a **client-server architecture**.
  - The **NAO (Python 2.7)** records audio and sends it to the **Whisper server (Python 3.8)** over a socket connection.
  - The **Whisper server** transcribes the audio and sends back the recognized text to the NAO client.
  
This design allows us to use the most appropriate toolchain for each task while maintaining compatibility with older hardware constraints.

##  Components

###  Sound Localization
- **Goal**: Estimate the direction of incoming sound.
- **Description**: Uses NAO's microphone array to identify where the "Polo" response is coming from.
- **Detailed Overview** :
  the code  allows the NAO robot to estimate the **direction of arrival (DoA)** of a sound source using the **two front microphones** (left and right). It uses the **GCC-PHAT (Generalized Cross-Correlation with Phase Transform)** algorithm to compute the **Time Difference of Arrival (TDoA)** and convert it into an angle.

---

## How It Works

### Collect Microphone Data
- The robot subscribes to the audio stream via `ALAudioDevice`.
- Samples are collected from 4 microphones, but only mic 0 (Left) and mic 1 (Right) are used for direction estimation.
- It collects `50`(which is around 4 seconds) audio frames, each 1600 samples at 16kHz (0.1 seconds per frame).

```python
self.collected_samples = [[], [], [], []]  # mic0, mic1, mic2, mic3
```

---

### Estimate Sound Direction
Once enough audio is collected, the system estimates the angle of arrival using `estimate_direction_gccphat()`:

```python
angle = self.estimate_direction_gccphat(mic0_samples, mic1_samples)
```

#### Steps:
1. **Frame Splitting**: Audio is split into non-overlapping 1600-sample frames.
2. **RMS Filtering**: Frames with low RMS (energy) are skipped. before this step results were not convincing, because data was getting cluttered with unusable frames and calculations were off.
3. **GCC-PHAT**: Calculates time delay τ between mic0 and mic1 using:
   - FFT cross-spectrum: `SIG1 * conj(SIG2)`
   - Normalize phase
   - Inverse FFT to get cross-correlation
   - Use interpolation to improve resolution
4. **Angle Estimation**:
   - τ is converted to an angle using:
     ```
     angle = asin((τ * c) / d)
     ```
     Where:
     - τ = estimated delay
     - c = speed of sound (343 m/s)
     - d = distance between microphones (calculated from irl positions)
5. **Best Frame Selection**: The frame with highest RMS is used for the final angle.

---

###  Speech Recognition
- **Goal**: Detect the keyword **"Polo"**.
- **Description**: uses OpenAI whisper on local device  to trigger behavior once the keyword is detected.

  
 #### Principle Behind the System

1. **Recording**:
   - The robot uses the `ALAudioDevice` module to collect audio from its microphones.
   - Only a short clip (e.g., 50 frames ≈ 3 seconds) is recorded after the robot says "Marco".
   - This ensures the system only captures the relevant response window from the user.

2. **Preprocessing**:
   - Audio from mic0 (front-left microphone) is normalized and saved as a mono WAV file.
   - Silence or low-amplitude noise is boosted to ensure clarity in the final recording.

3. **Transmission to Server**:
   - The recorded audio is sent via TCP to a server on the local network.
   - A 4-byte header indicates the size of the WAV payload.
   - The server is expected to be running a Whisper transcription service that:
     - Decodes the WAV file.
     - Runs Whisper to transcribe the speech.
     - Sends back the recognized text and its length.

4. **Keyword Matching**:
   - Once the transcription is received, it's split into individual words.
   - The robot searches for the presence of predefined keywords (e.g., `"Hi"`, `"Polo"`).
   - Depending on the match:
     - It may respond with a phrase (`"I am comming"`) or something similar.
     - Or repeat the call again after a delay.
     - If no response is received twice, it ends the interaction.

###  Target Approach
- **Goal**: Move the robot toward the sound source.
- **Description**: Uses basic motion control to approach the estimated direction of the sound.

---


### Limitations:
- Unfortunately, the version of the robot we were working with had only two functioning microphones (Left and Right). Because of this, sound localization can only estimate the direction in 2D and cannot distinguish whether the sound is coming from the front or the back. Therefore, our robot assumes that the sound is coming from the front.


###  Improvements for the Future:

- **Continuous Listening**:  
  Currently, the system captures a fixed number of audio frames, writes them to a temporary `.wav` file, and sends it to the Whisper server after collection. This introduces latency and limits interactivity.  
  In future iterations, the architecture could be restructured to allow **continuous audio streaming**, enabling NAO to **"listen live"** instead of working in discrete chunks. This would make keyword recognition and response much more natural and immediate.

- **Real-time Whisper Integration**:  
  Whisper could be integrated in a streaming fashion using newer models or WebSocket-based servers, allowing NAO to act on keywords as soon as they are detected mid-sentence.



##  Technologies Used

- Naoqi
- whisper
- numpy


