#  NAO Plays Marco Polo

This project aims to make the NAO humanoid robot play the game **Marco Polo** in the **"Marco" role**.

---

## Project Overview

The robot will detect when a human responds with the word **"Polo"**, determine the direction of the sound, move toward the target, and finally recognize a colored tape using computer vision to confirm the target's location and point at it.

---

##  Components

###  Sound Localization
- **Goal**: Estimate the direction of incoming sound.
- **Description**: Uses NAO's microphone array to identify where the "Polo" response is coming from.

###  Speech Recognition
- **Goal**: Detect the keyword **"Polo"**.
- **Description**: uses OpenAI whisper on local device  to trigger behavior once the keyword is detected.

###  Target Approach
- **Goal**: Move the robot toward the sound source.
- **Description**: Uses basic motion control to approach the estimated direction of the sound.

---

##  Technologies Used

- Naoqi
- openCV
- whisper
- will add more later


