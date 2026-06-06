import streamlit as st
import replicate
import os
import requests
import datetime
import json
from dotenv import load_dotenv
from openai import OpenAI
from dataclasses import dataclass, asdict, field
from typing import List, Optional

# Load environment variables
load_dotenv()

st.set_page_config(page_title="Studio IA", page_icon="🚀", layout="wide")

# --- DATA MODELS ---
@dataclass
class VideoInstance:
    id: str = field(default_factory=lambda: datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    type: str = "intro" # intro, mid, final
    general_script: str = ""
    # Part 1: Dynamic Video
    video_prompt: str = ""
    character_speech: str = ""
    video_url: Optional[str] = None
    character_audio_url: Optional[str] = None
    # Part 2: Freeze Frame + Narration
    freeze_image_prompt: str = ""
    narration_script: str = ""
    freeze_image_url: Optional[str] = None
    narrator_audio_url: Optional[str] = None
    # Part 3: Choice
    choice_a: str = ""
    choice_b: str = ""
    timer_duration: int = 3

# --- LOGGING UTILITY ---
def log_terminal(level, message):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    colors = {"INFO": "\033[94m", "SUCCESS": "\033[92m", "WARNING": "\033[93m", "ERROR": "\033[91m", "RESET": "\033[0m"}
    color = colors.get(level, colors["RESET"])
    print(f"{color}[{timestamp}] [{level}] {message}{colors['RESET']}")

def save_key_to_env(key_name, value):
    if not value: return
    try:
        env_path = ".env"
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r") as f: lines = f.readlines()
        found = False
        new_lines = []
        for line in lines:
            if line.startswith(f"{key_name}="):
                new_lines.append(f"{key_name}={value}\n")
                found = True
            else: new_lines.append(line)
        if not found: new_lines.append(f"{key_name}={value}\n")
        with open(env_path, "w") as f: f.writelines(new_lines)
        log_terminal("SUCCESS", f"Saved {key_name} to .env file.")
    except Exception as e: log_terminal("ERROR", f"Failed to save {key_name} to .env: {e}")

st.title("🚀 Studio IA - Dashboard")

# Initialize API Keys
init_replicate_token = os.getenv("REPLICATE_API_TOKEN", "")
init_openai_token = os.getenv("OPENAI_API_KEY", "")
openai_models = ["gpt-5.4-mini", "gpt-5.5-flagship", "gpt-5.4-thinking", "gpt-5.3-instant", "gpt-5-mini"]

# --- SIDEBAR ---
with st.sidebar:
    st.title("Settings")
    st.header("🔑 Authentication")
    replicate_api_token = st.text_input("Replicate Token", type="password", value=init_replicate_token, key="main_replicate_token")
    if replicate_api_token != init_replicate_token: save_key_to_env("REPLICATE_API_TOKEN", replicate_api_token)
    
    openai_api_key_input = st.text_input("OpenAI Key", type="password", value=init_openai_token, key="main_openai_key")
    if openai_api_key_input != init_openai_token: save_key_to_env("OPENAI_API_KEY", openai_api_key_input)
    openai_api_key = openai_api_key_input

    st.divider()
    if openai_api_key:
        try:
            client_tmp = OpenAI(api_key=openai_api_key)
            fetched_models = client_tmp.models.list()
            model_ids = [m.id for m in fetched_models.data if (m.id.startswith("gpt-5") or m.id.startswith("o3") or "thinking" in m.id) and "preview" not in m.id]
            if model_ids:
                model_ids.sort(reverse=True)
                openai_models = model_ids
        except Exception: pass

    st.header("📂 Navigation")
    mode = st.radio("Choose Mode", ["📦 Instance", "📝 Script", "🎬 Video", "🖼️ Image", "🎙️ Voice"], key="navigation_mode")
    
    if mode == "🎬 Video": model_name = st.selectbox("Select Model", ["prunaai/p-video"], key="video_model_select")
    elif mode == "🖼️ Image": model_name = st.selectbox("Select Model", ["bytedance/seedream-4.5"], key="image_model_select")
    elif mode == "🎙️ Voice": model_name = st.selectbox("Select Model", ["minimax/speech-2.8-turbo"], key="voice_model_select")
    else: model_name = st.selectbox("Select Model", openai_models, key="script_model_select")

client = OpenAI(api_key=openai_api_key) if openai_api_key else None

if "shared_prompt" not in st.session_state:
    st.session_state.shared_prompt = {"decor": "", "chars": "", "env": "", "actions": "", "speech": ""}
if "current_instance" not in st.session_state:
    st.session_state.current_instance = VideoInstance()

# --- MAIN CONTENT ---
if replicate_api_token:
    os.environ["REPLICATE_API_TOKEN"] = replicate_api_token
    
    if mode == "📦 Instance":
        st.header("📦 Video Instance Studio")
        
        # Instance Type Selection
        inst_type = st.selectbox("Instance Type", ["intro", "mid", "final"], key="inst_type_select")
        st.session_state.current_instance.type = inst_type
        
        inst = st.session_state.current_instance
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("1. General Script")
            if inst_type == "intro":
                placeholder_text = "Describe two scary monsters (e.g. Skibidi-style, fantasy chimera) and the environment..."
                st.info("💡 **INTRO Template:** 2 monsters head-to-toe (Left/Right) + Hook Dialogue + Choice.")
            else:
                placeholder_text = "Enter your script idea..."
            
            gen_script = st.text_area("Script Idea", value=inst.general_script, placeholder=placeholder_text, height=150, key="inst_gen_script")
            
            if st.button("🧙 Decompose into Instance Elements", use_container_width=True):
                if not client: st.error("OpenAI Key required.")
                elif not gen_script: st.error("Please describe your idea.")
                else:
                    try:
                        log_terminal("INFO", f"Decomposing {inst_type} script...")
                        with st.spinner("Generating instance structure..."):
                            if inst_type == "intro":
                                sys_msg = """You are a master of horror video architecture. The user wants a DISTURBING INTRO instance.
                                Style: NOT aesthetic. It must be SCARY, CREEPY, and DISTURBING. Think body horror, uncanny valley, or dark fantasy monsters.
                                
                                Structure:
                                - Base image: 2 disturbing monsters standing head-to-toe, one on the LEFT, one on the RIGHT.
                                - CAMERA: Fixed camera, stationary shot.
                                - ANIMATION: BOTH monsters must perform unsettling, creepy emotes simultaneously (twitching, breathing heavily, glowing or leaking eyes).
                                - SPEECH: The monster on the left MUST speak directly to the camera with realistic lip-sync.
                                
                                Your job is to output a JSON with:
                                {
                                    "freeze_image_prompt": "Disturbing 9:16 full-body shot of two terrifying monsters standing in a dark, unsettling environment. One on the far left, one on the far right. High-detail horror textures, cinematic dark lighting, scary and unsettling atmosphere.",
                                    "video_prompt": "Fixed camera horror shot. BOTH monsters are animated with creepy, unsettling movements. The monster on the left stares into the camera and says: \\"Choisi moi. Ne lui fais pas confiance, je sais ce dont il est capable.\\" while the other monster twitches disturbingly. 9:16 vertical video.",
                                    "character_speech": "Choisi moi. Ne lui fais pas confiance, je sais ce dont il est capable.",
                                    "narration_script": "Choisi ton compagnon pour la nuit.",
                                    "choice_a": "[Disturbing Name/Description A]",
                                    "choice_b": "[Disturbing Name/Description B]"
                                }"""
                            else:
                                sys_msg = "Decompose script into: video_prompt, character_speech, freeze_image_prompt, narration_script, choice_a, choice_b."

                            resp = client.chat.completions.create(
                                model=model_name,
                                response_format={ "type": "json_object" },
                                messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": gen_script}]
                            )
                            data = json.loads(resp.choices[0].message.content)
                            
                            st.session_state["inst_v_p"] = data.get("video_prompt", "")
                            st.session_state["inst_c_s"] = data.get("character_speech", "")
                            st.session_state["inst_f_p"] = data.get("freeze_image_prompt", "")
                            st.session_state["inst_n_s"] = data.get("narration_script", "")
                            st.session_state["inst_ca"] = data.get("choice_a", "")
                            st.session_state["inst_cb"] = data.get("choice_b", "")
                            inst.general_script = gen_script
                            st.rerun()
                    except Exception as e: st.error(f"Failed to decompose: {e}")

            with st.expander("🔍 Debug: Raw Response"):
                if 'data' in locals(): st.json(data)

        with col2:
            st.subheader("2. Review Elements")
            inst_v_p = st.text_area("Video Action Prompt", key="inst_v_p")
            inst_c_s = st.text_input("Character Speech", key="inst_c_s")
            inst_f_p = st.text_area("Base Image Prompt", key="inst_f_p")
            inst_n_s = st.text_input("Narrator Script", key="inst_n_s")
            c1, c2 = st.columns(2)
            inst_ca = c1.text_input("Choice A", key="inst_ca")
            inst_cb = c2.text_input("Choice B", key="inst_cb")
            
            # Sync back
            inst.video_prompt, inst.character_speech = inst_v_p, inst_c_s
            inst.freeze_image_prompt, inst.narration_script = inst_f_p, inst_n_s
            inst.choice_a, inst.choice_b = inst_ca, inst_cb

        st.divider()
        st.subheader("3. Production Control")
        p_col1, p_col2 = st.columns(2)
        
        if p_col1.button("🎬 Generate All Assets (9:16)", use_container_width=True):
            try:
                status = st.empty()
                with st.spinner("🚀 Producing..."):
                    # 1. Narrator Voice (Always separate)
                    if inst.narration_script:
                        status.info("🎙️ Synthesizing Narrator Voice...")
                        # Use Deep_Voice_Man for Intro (more scary), Wise_Woman for others
                        v_id = "Deep_Voice_Man" if inst.type == "intro" else "Wise_Woman"
                        v2 = replicate.run("minimax/speech-2.8-turbo", input={"text": inst.narration_script, "voice_id": v_id})
                        inst.narrator_audio_url = str(v2)
                    
                    # 2. Character Voice (Only for non-intro types)
                    if inst.type != "intro" and inst.character_speech:
                        status.info("🎙️ Synthesizing Character Voice...")
                        v1 = replicate.run("minimax/speech-2.8-turbo", input={"text": inst.character_speech, "voice_id": "Deep_Voice_Man"})
                        inst.character_audio_url = str(v1)
                    
                    # 3. Base Image
                    status.info("🖼️ Generating Base Image...")
                    img = replicate.run("bytedance/seedream-4.5", input={"prompt": inst.freeze_image_prompt, "size": "2K", "aspect_ratio": "9:16"})
                    inst.freeze_image_url = str(img[0])
                    
                    # 4. Video (Native speech generation for Intro)
                    status.info("🎥 Animating Video (7s)...")
                    vid_params = {
                        "prompt": inst.video_prompt,
                        "image": inst.freeze_image_url,
                        "duration": 7, # Increased to 7 seconds
                        "aspect_ratio": "9:16",
                        "save_audio": True 
                    }
                    vid = replicate.run("prunaai/p-video", input=vid_params)
                    inst.video_url = str(vid)
                    
                    # If intro, the video already contains the character audio
                    if inst.type == "intro":
                        inst.character_audio_url = inst.video_url # Link it for the results preview
                
                status.success("✅ Production complete!")
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")
            
        if p_col2.button("💾 Save Config", use_container_width=True):
            st.download_button("Download JSON", data=json.dumps(asdict(inst), indent=4), file_name=f"instance_{inst.id}.json")

        if inst.video_url or inst.freeze_image_url:
            st.divider()
            st.subheader("🎥 Results")
            r1, r2 = st.columns(2)
            if inst.video_url:
                r1.write("**Part 1: Video Hook**")
                r1.video(inst.video_url)
                if inst.character_audio_url: r1.audio(inst.character_audio_url)
            if inst.freeze_image_url:
                r2.write("**Part 2: Freeze & Choice**")
                r2.image(inst.freeze_image_url)
                if inst.narrator_audio_url: r2.audio(inst.narrator_audio_url)
            if inst.choice_a: st.info(f"**Options:** A: {inst.choice_a} | B: {inst.choice_b}")

    # Simplified other modes
    elif mode == "📝 Script":
        st.header("📝 Script Studio")
        u_idea = st.text_area("Your Idea", height=150)
        if st.button("Generate Elements"):
            st.info("Generating standard prompt elements...")
    elif mode == "🎬 Video":
        st.header("🎬 Video Studio")
        # (Standard video logic)
    elif mode == "🖼️ Image":
        st.header("🖼️ Image Studio")
        # (Standard image logic)
    elif mode == "🎙️ Voice":
        st.header("🎙️ Voice Studio")
        # (Standard voice logic)
else:
    st.info("Provide API Tokens to start.")
