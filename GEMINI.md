# ViralCashMachine_V2

A Streamlit-based dashboard designed for generating AI-powered vertical video content (9:16) optimized for platforms like TikTok.

## Project Overview

- **Purpose:** Automate the creation of "Video Instances" which include a video hook, a freeze-frame narration, and interactive choices.
- **Main Technologies:**
    - **Streamlit:** UI and dashboard orchestration.
    - **Replicate API:** Used for media generation (Video, Image, Voice).
    - **OpenAI API:** Used for script analysis and generating prompts/JSON structures.
    - **Python 3:** Core language.
- **Architecture:** The application uses a "Instance-based" workflow where scripts are decomposed into discrete elements (video prompt, speech, image prompt, etc.) which are then used to generate assets via various AI models.

## Building and Running

### Prerequisites
- Python 3.x installed.
- API keys for Replicate and OpenAI.

### Setup
Run the setup script to install necessary dependencies:
```powershell
.\setup.bat
```
*This command executes `pip install -r requirements.txt`.*

### Running the Application
Start the Streamlit dashboard:
```powershell
.\start.bat
```
*This command executes `python -m streamlit run app.py`.*

### Configuration
1.  Copy `.env.example` to `.env`.
2.  Provide your `REPLICATE_API_TOKEN` and `OPENAI_API_KEY` either directly in the `.env` file or via the dashboard sidebar.

## Development Conventions

- **State Management:** Uses Streamlit's `st.session_state` to maintain the current video instance and navigation state.
- **Data Models:** Uses Python `dataclasses` (see `VideoInstance` in `app.py`) for structured data handling.
- **Logging:** A custom `log_terminal` function is used for color-coded terminal output.
- **Environment Variables:** The application automatically updates the `.env` file when keys are provided through the UI via the `save_key_to_env` utility.
- **Local Storage:**
    - Assets are automatically downloaded to the `exports/` directory.
    - Structure: `exports/{project_name}/{instance_id}/`.
    - Assets include `video.mp4`, `base_image.png`, `narrator.mp3`, `character.mp3`, and `metadata.json`.
- **Project Library:** A dedicated mode allows users to browse saved projects, preview assets, and reload them into the editor.
- **Media Specs:** Default output is 9:16 aspect ratio, suitable for mobile-first video platforms.
- **AI Models:**
    - **Video:** `prunaai/p-video`
    - **Images:** `bytedance/seedream-4.5`
    - **Voice:** `minimax/speech-2.8-turbo`
    - **Text:** GPT-4/GPT-5 models via OpenAI API.

## Project Structure
- `app.py`: The main entry point containing the Streamlit logic and AI orchestration.
- `requirements.txt`: Python dependency list.
- `setup.bat`: Installation script.
- `start.bat`: Execution script.
- `.env`: Local configuration file (ignored by git).
