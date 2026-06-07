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

st.set_page_config(page_title="ViralCashMachine_V2", page_icon="🚀", layout="wide")

# --- DATA MODELS ---
@dataclass
class VideoInstance:
    id: str = field(default_factory=lambda: datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    type: str = "intro" # intro, mid, final
    general_script: str = ""
    # Character Config
    char_left_name: str = "Monster A"
    char_left_gender: str = "Male"
    char_left_personality: str = "Aggressive"
    char_right_name: str = "Monster B"
    char_right_gender: str = "Female"
    char_right_personality: str = "Crazed"
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
    # Internal Prompt Slots (to be filled by AI)
    monster_left_desc: str = ""
    monster_right_desc: str = ""
    monster_left_idle: str = ""
    monster_right_idle: str = ""
    environment_desc: str = ""

# --- LOGGING UTILITY ---
def log_terminal(level, message):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    colors = {"INFO": "\033[94m", "SUCCESS": "\033[92m", "WARNING": "\033[93m", "ERROR": "\033[91m", "RESET": "\033[0m"}
    color = colors.get(level, colors["RESET"])
    print(f"{color}[{timestamp}] [{level}] {message}{colors['RESET']}")

def download_file(url, folder, filename):
    if not url: return None
    try:
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, filename)
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            log_terminal("SUCCESS", f"Downloaded: {filename}")
            return path
    except Exception as e:
        log_terminal("ERROR", f"Failed to download {url}: {e}")
    return None

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

def sync_instance_to_widgets(inst):
    st.session_state["inst_v_p"] = inst.video_prompt
    st.session_state["inst_c_s"] = inst.character_speech
    st.session_state["inst_f_p"] = inst.freeze_image_prompt
    st.session_state["inst_n_s"] = inst.narration_script
    st.session_state["inst_ca"] = inst.choice_a
    st.session_state["inst_cb"] = inst.choice_b
    st.session_state["inst_gen_script"] = inst.general_script
    st.session_state["inst_type_select"] = inst.type
    # Character Config
    st.session_state["c_l_n"] = inst.char_left_name
    st.session_state["c_l_g"] = inst.char_left_gender
    st.session_state["c_l_p"] = inst.char_left_personality
    st.session_state["c_r_n"] = inst.char_right_name
    st.session_state["c_r_g"] = inst.char_right_gender
    st.session_state["c_r_p"] = inst.char_right_personality

def load_into_editor(meta_data):
    inst = VideoInstance(**meta_data)
    st.session_state.current_instance = inst
    sync_instance_to_widgets(inst)
    st.session_state.navigation_mode = "📦 Instance"

st.title("🚀 ViralCashMachine_V2 - Dashboard")

# Initialize API Keys
init_replicate_token = os.getenv("REPLICATE_API_TOKEN", "")
init_openai_token = os.getenv("OPENAI_API_KEY", "")
openai_models = ["gpt-5.4-mini", "gpt-5.5-flagship", "gpt-5.4-thinking", "gpt-5.3-instant", "gpt-5-mini"]

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("""
        <div style="background: linear-gradient(45deg, #FF0000, #FFD700); padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 25px; box-shadow: 0px 10px 20px rgba(0,0,0,0.3); border: 2px solid #FFF;">
            <h1 style="color: white; font-size: 22px; font-family: 'Impact', sans-serif; text-transform: uppercase; margin: 0; letter-spacing: 1px; text-shadow: 3px 3px 0px #000;">
                💰 VIRAL CASH MACHINE V2 🚀
            </h1>
            <p style="color: white; font-size: 10px; font-family: 'Arial', sans-serif; margin-top: 5px; font-weight: bold; text-transform: uppercase;">
                L'algorithme n'a aucune chance
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    st.title("Settings")
    
    st.header("📂 Project Context")
    project_name = st.text_input("Project Name", value="default_project", help="Folder name where assets will be saved.")
    
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
    mode = st.radio("Choose Mode", ["📦 Instance", "📁 Projects", "📝 Script", "🎬 Video", "🖼️ Image", "🎙️ Voice"], key="navigation_mode")
    
    st.divider()
    st.header("⚙️ Quality Engine")
    quality_mode = st.radio("Production Mode", ["🟢 ECO / DRAFT", "💎 FULL QUALITY MAX"], index=0, help="Switch between fast/cheap testing and high-quality final production.")
    
    if quality_mode == "🟢 ECO / DRAFT":
        video_draft = True
        video_res = "720p"
        image_size = "2K"
        st.caption("🚀 Speed: Ultra-Fast | Cost: $0.005/sec")
    else:
        video_draft = False
        video_res = "1080p"
        image_size = "4K"
        st.caption("✨ Quality: Viral Max | Cost: $0.04/sec")

    if mode == "🎬 Video": model_name = st.selectbox("Select Model", ["prunaai/p-video"], key="video_model_select")
    elif mode == "🖼️ Image": model_name = st.selectbox("Select Model", ["bytedance/seedream-4.5"], key="image_model_select")
    elif mode == "🎙️ Voice": model_name = st.selectbox("Select Model", ["minimax/speech-2.8-turbo"], key="voice_model_select")
    else: 
        default_idx = openai_models.index("gpt-5.4-mini") if "gpt-5.4-mini" in openai_models else 0
        model_name = st.selectbox("Select Model", openai_models, index=default_idx, key="script_model_select")

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
        
        # --- PROJECT/INSTANCE QUICK LOADER ---
        with st.sidebar:
            st.divider()
            st.subheader("快速加载 / Quick Load")
            proj_path = os.path.join("exports", project_name)
            if os.path.exists(proj_path):
                instances = [d for d in os.listdir(proj_path) if os.path.isdir(os.path.join(proj_path, d))]
                if instances:
                    sel_id = st.selectbox("Open existing instance", ["-- Select --"] + instances, key="quick_load_sel")
                    if sel_id != "-- Select --":
                        if st.button("Open", use_container_width=True):
                            with open(os.path.join(proj_path, sel_id, "metadata.json"), "r") as f:
                                meta_data = json.load(f)
                            inst = VideoInstance(**meta_data)
                            st.session_state.current_instance = inst
                            sync_instance_to_widgets(inst)
                            st.rerun()
                else: st.caption("No instances found.")
            else: st.caption("No exports yet.")

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
            
            # --- CHARACTER SETUP UI ---
            st.divider()
            st.subheader("👤 Character Setup")
            c_col1, c_col2 = st.columns(2)
            with c_col1:
                st.write("**Monster Left (Speaker)**")
                inst.char_left_name = st.text_input("Name L", value=inst.char_left_name, key="c_l_n")
                l_genders = ["Male", "Female", "Alien", "Unknown"]
                l_persos = ["Aggressive", "Deceptive", "Terrified", "Crazed"]
                inst.char_left_gender = st.selectbox("Gender L", l_genders, index=l_genders.index(inst.char_left_gender) if inst.char_left_gender in l_genders else 0, key="c_l_g")
                inst.char_left_personality = st.selectbox("Personality L", l_persos, index=l_persos.index(inst.char_left_personality) if inst.char_left_personality in l_persos else 0, key="c_l_p")
            with c_col2:
                st.write("**Monster Right (Target)**")
                inst.char_right_name = st.text_input("Name R", value=inst.char_right_name, key="c_r_n")
                r_genders = ["Male", "Female", "Alien", "Unknown"]
                r_persos = ["Stoic", "Twitchy", "Menacing", "Feral", "Crazed"]
                inst.char_right_gender = st.selectbox("Gender R", r_genders, index=r_genders.index(inst.char_right_gender) if inst.char_right_gender in r_genders else 0, key="c_r_g")
                inst.char_right_personality = st.selectbox("Personality R", r_persos, index=r_persos.index(inst.char_right_personality) if inst.char_right_personality in r_persos else 0, key="c_r_p")

            if st.button("🧙 Decompose into Instance Elements", use_container_width=True):
                if not client: st.error("OpenAI Key required.")
                elif not gen_script: st.error("Please describe your idea.")
                else:
                    try:
                        log_terminal("INFO", f"Decomposing {inst_type} script...")
                        with st.spinner("Generating instance structure..."):
                            if inst_type == "intro":
                                sys_msg = f"""You are a master of horror video architecture. 
                                Task: Decompose the script into behavioral slots for a ViralCashMachine_V2 instance.
                                
                                CONTEXT:
                                - Left Monster: Gender is {inst.char_left_gender}.
                                - Right Monster: Gender is {inst.char_right_gender}.
                                
                                LANGUAGE RULE: 
                                - All descriptions (visuals, movements, environment) MUST be in ENGLISH.
                                
                                VISUAL RULE:
                                - NEVER use terms like 'hunched', 'crawling', 'leaning forward', or 'predatory posture'. These cause the video model to move the character.
                                - SAFE HORROR: Use terms like 'weathered', 'ashen', 'pale', 'aged', 'rough textured' instead of 'decayed', 'zombie', 'naked', or 'raw'.
                                - Describe monsters as STANDING UPRIGHT and FACING FORWARD.
                                
                                Instructions for Names:
                                - You MUST invent two UNIQUE, simple French names that MATCH the specified genders.
                                - For Female: Use names like Marie, Julie, Sophie, etc.
                                - For Male: Use names like Pierre, Paul, Thomas, etc.
                                - NEVER use placeholders like 'Monster A', 'Monster B', 'Character', or 'Creature' as names.
                                
                                Requirements:
                                1. Output a JSON with specific slots.
                                2. char_left_name: A real human-like name matching {inst.char_left_gender} gender.
                                3. char_right_name: A real human-like name matching {inst.char_right_gender} gender.
                                4. monster_left_desc: Visual description (ENGLISH).
                                5. monster_right_desc: Visual description (ENGLISH).
                                6. monster_left_idle: Movement (ENGLISH).
                                7. monster_right_idle: Movement (ENGLISH).
                                8. environment_desc: Background (ENGLISH).
                                
                                JSON Format:
                                {{
                                    "char_left_name": "...",
                                    "char_right_name": "...",
                                    "monster_left_desc": "...",
                                    "monster_right_desc": "...",
                                    "monster_left_idle": "...",
                                    "monster_right_idle": "...",
                                    "environment_desc": "..."
                                }}"""
                            else:
                                sys_msg = "Standard decomposition. ALL descriptions MUST be in English. Use safe horror terms (weathered, ashen)."

                            resp = client.chat.completions.create(
                                model=model_name,
                                response_format={ "type": "json_object" },
                                messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": gen_script}]
                            )
                            data = json.loads(resp.choices[0].message.content)
                            
                            # Update Instance Slots
                            new_left_name = data.get("char_left_name", inst.char_left_name)
                            new_right_name = data.get("char_right_name", inst.char_right_name)
                            
                            # Clean up placeholders if AI failed
                            if "Monster" in new_left_name or "Character" in new_left_name: new_left_name = "Pierre"
                            if "Monster" in new_right_name or "Character" in new_right_name: new_right_name = "Jacques"
                            
                            inst.char_left_name = new_left_name
                            inst.char_right_name = new_right_name
                            inst.monster_left_desc = data.get("monster_left_desc", "")
                            inst.monster_right_desc = data.get("monster_right_desc", "")
                            inst.monster_left_idle = data.get("monster_left_idle", "")
                            inst.monster_right_idle = data.get("monster_right_idle", "")
                            inst.environment_desc = data.get("environment_desc", "")
                            
                            # MANDATORY SPEECH - LOCKED
                            inst.character_speech = "Choisi moi. Ne lui fais pas confiance, je sais ce dont il est capable."
                            inst.narration_script = f"Choisi ton compagnon pour la nuit, {inst.char_left_name} ou {inst.char_right_name} ?"
                            inst.choice_a = inst.char_left_name
                            inst.choice_b = inst.char_right_name
                            
                            # --- MASTER ARBITER ASSEMBLY ---
                            # 1. Video Prompt Assembly (ULTRA-FORCED FPS)
                            inst.video_prompt = (
                                f"[CAMERA] 9:16 vertical. Photorealistic cinematic horror. ABSOLUTE STATIC CAMERA. ZERO movement. ZERO drift. ZERO shake. ZERO pan. ZERO tilt. ZERO zoom. Camera IS frozen in place like a security camera. Adult eye-level (1.7m). Fixed forever. "
                                f"[FOREGROUND_POV] VIDEO GAME FIRST-PERSON PERSPECTIVE. Like a first-person shooter game. The camera IS the eyes. ONLY two ungloved human hands visible, cut off at the wrist. NO forearms. NO sleeves. NO clothing. Skin is pale, ashen, weathered, rough textured. NO accessories of any kind. Pure bare skin only. Hands at hip height, palms slightly inward, angled down. STANDING UPRIGHT POSE ONLY. Subtle breathing motion. "
                                f"[ENV] {inst.environment_desc}. COMPLETELY STATIC BACKGROUND. No environmental animation. STATIC lighting. NO dynamic lights. NO flashlight. NO spotlight. Both characters fully lit and visible at all times. "
                                f"[MIDGROUND_LEFT] {inst.monster_left_desc}. FACING CAMERA. NOT moving toward camera. ABSOLUTE FIXED POSITION. Root locked to floor. ZERO translation. ZERO steps. NO advancing. ONLY upper body and head animate. Returns to neutral pose between actions. IDLE: {inst.monster_left_idle}. "
                                f"ACTION: Speaks directly to camera with intense eye-contact and full lip-sync. "
                                f"BEAT 1 - 'Choisi moi': aggressively taps own chest with fist, leaning forward. "
                                f"BEAT 2 - 'Ne lui fais pas confiance': NEVER breaks eye contact with camera, extends arm pointing accusingly to the right WITHOUT looking away, shakes head slowly while staring into camera. "
                                f"BEAT 3 - 'je sais ce dont il est capable': locks eyes back on camera, leans slightly forward with a slow threatening nod, expression darkens. "
                                f"Extreme facial articulation throughout. Returns to neutral idle after speech ends. "
                                f"[MIDGROUND_RIGHT] {inst.monster_right_desc}. FACING CAMERA. NOT moving toward camera. ABSOLUTE FIXED POSITION. Root locked to floor. ZERO translation. ZERO steps. NO advancing. ONLY upper body and head animate. Returns to neutral pose between actions. IDLE: {inst.monster_right_idle}."
                            )
                            
                            # 2. Freeze Image Prompt Assembly (ULTRA-FORCED FPS - UNIFORM)
                            inst.freeze_image_prompt = (
                                f"[CAMERA] 9:16 vertical. Photorealistic masterpiece. ABSOLUTE STATIC CAMERA. Camera IS the eyes, positioned at adult eye-level height (1.7m), horizontal gaze. "
                                f"[FOREGROUND_POV] VIDEO GAME FIRST-PERSON PERSPECTIVE. Like a first-person shooter game. ONLY two ungloved human hands visible, cut off at the wrist. NO forearms. NO sleeves. NO clothing. Skin is pale, ashen, weathered, rough textured. NO accessories of any kind. Pure bare skin only. Hands at hip height, palms slightly inward, angled down. STANDING UPRIGHT POSE ONLY. "
                                f"[ENV] {inst.environment_desc}. COMPLETELY STATIC BACKGROUND. STATIC lighting. NO flashlight. NO character occluded by shadow. "
                                f"[MIDGROUND_LEFT] {inst.monster_left_desc}. FACING CAMERA. NOT moving toward camera. Standing upright, ABSOLUTE FIXED POSITION. Root locked to floor. "
                                f"[MIDGROUND_RIGHT] {inst.monster_right_desc}. FACING CAMERA. NOT moving toward camera. Standing upright, ABSOLUTE FIXED POSITION. Root locked to floor. "
                                f"CLEAN IMAGE, NO TEXT. --NO third-person body, NO lying down, NO floor hands, NO crawling, NO walking, NO approaching camera, NO weapons, NO flashlight, NO accessories, NO gloves, NO watches, NO jewelry, NO camera movement."
                            )

                            st.session_state["inst_v_p"] = inst.video_prompt
                            st.session_state["inst_c_s"] = inst.character_speech
                            st.session_state["inst_f_p"] = inst.freeze_image_prompt
                            st.session_state["inst_n_s"] = inst.narration_script
                            st.session_state["inst_ca"] = inst.choice_a
                            st.session_state["inst_cb"] = inst.choice_b
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
                    
                    # 2. Character Voice
                    if inst.character_speech:
                        status.info("🎙️ Synthesizing Character Voice...")
                        v1 = replicate.run("minimax/speech-2.8-turbo", input={"text": inst.character_speech, "voice_id": "Deep_Voice_Man"})
                        inst.character_audio_url = str(v1)
                    
                    # 3. Base Image
                    status.info("🖼️ Generating Base Image...")
                    img = replicate.run("bytedance/seedream-4.5", input={"prompt": inst.freeze_image_prompt, "size": image_size, "aspect_ratio": "9:16"})
                    inst.freeze_image_url = str(img[0])
                    
                    # 4. Video
                    status.info("🎥 Animating Video (7s)...")
                    vid_params = {
                        "prompt": inst.video_prompt,
                        "image": inst.freeze_image_url,
                        "duration": 7, 
                        "aspect_ratio": "9:16",
                        "resolution": video_res,
                        "draft": video_draft,
                        "save_audio": True,
                        "negative_prompt": "lying down, floor hands, crawling, walking, approaching camera, full body third-person view, camera movement, handheld shake, pan, tilt, zoom, dolly, drift, rotation, drifting, camera shake, moving background, weapons, guns, items in hands, flat palms, palms up, text, deformed fingers, watches, bracelets, rings, gloves, sleeves, cuffs, wristbands, jewelry"
                    }
                    # Inject audio for lip-sync if available
                    if inst.character_audio_url:
                        vid_params["audio"] = inst.character_audio_url
                        
                    vid = replicate.run("prunaai/p-video", input=vid_params)
                    inst.video_url = str(vid)

                    # --- AUTO-DOWNLOAD & INDEXING ---
                    status.info("💾 Archiving assets locally...")
                    project_dir = os.path.join("exports", project_name, inst.id)
                    
                    if inst.narrator_audio_url:
                        download_file(inst.narrator_audio_url, project_dir, "narrator.mp3")
                    if inst.character_audio_url:
                        # For intro, character audio is actually the video, but we might want a separate file if it was generated
                        if inst.type != "intro":
                            download_file(inst.character_audio_url, project_dir, "character.mp3")
                    if inst.freeze_image_url:
                        download_file(inst.freeze_image_url, project_dir, "base_image.png")
                    if inst.video_url:
                        download_file(inst.video_url, project_dir, "video.mp4")
                    
                    # Save metadata
                    with open(os.path.join(project_dir, "metadata.json"), "w") as f:
                        json.dump(asdict(inst), f, indent=4)
                    
                    log_terminal("SUCCESS", f"Project {project_name} instance {inst.id} archived.")
                
                status.success(f"✅ Production complete & archived in exports/{project_name}!")
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

    elif mode == "📁 Projects":
        st.header("📁 Project Library")
        exports_dir = "exports"
        if not os.path.exists(exports_dir):
            st.info("No projects found yet. Generate some assets first!")
        else:
            projects = [d for d in os.listdir(exports_dir) if os.path.isdir(os.path.join(exports_dir, d))]
            if not projects: st.info("No projects found.")
            else:
                sel_proj = st.selectbox("Select Project", projects)
                proj_path = os.path.join(exports_dir, sel_proj)
                instances = [d for d in os.listdir(proj_path) if os.path.isdir(os.path.join(proj_path, d))]
                
                if not instances: st.warning("No instances found in this project.")
                else:
                    sel_inst = st.selectbox("Select Instance", instances)
                    inst_path = os.path.join(proj_path, sel_inst)
                    meta_path = os.path.join(inst_path, "metadata.json")
                    
                    if os.path.exists(meta_path):
                        with open(meta_path, "r") as f: meta_data = json.load(f)
                        st.subheader(f"Instance: {sel_inst} ({meta_data.get('type', 'N/A')})")
                        
                        # --- LOCAL ASSET PREVIEW ---
                        col_l, col_r = st.columns(2)
                        
                        # Part 1: Video
                        v_path = os.path.join(inst_path, "video.mp4")
                        if os.path.exists(v_path):
                            col_l.write("**Part 1: Video Hook (Local)**")
                            col_l.video(v_path)
                        else:
                            # Fallback to URL if local file is missing but URL exists in meta
                            v_url = meta_data.get("video_url")
                            if v_url:
                                col_l.write("**Part 1: Video Hook (Remote)**")
                                col_l.video(v_url)

                        # Part 2: Image & Audio
                        i_path = os.path.join(inst_path, "base_image.png")
                        if os.path.exists(i_path):
                            col_r.write("**Part 2: Base Image (Local)**")
                            col_r.image(i_path)
                        else:
                            i_url = meta_data.get("freeze_image_url")
                            if i_url:
                                col_r.write("**Part 2: Base Image (Remote)**")
                                col_r.image(i_url)
                            
                        n_path = os.path.join(inst_path, "narrator.mp3")
                        if os.path.exists(n_path): 
                            col_r.write("**Narrator Voice**")
                            col_r.audio(n_path)
                            
                        st.divider()
                        st.info(f"**Options:** A: {meta_data.get('choice_a')} | B: {meta_data.get('choice_b')}")
                        
                        if st.button("♻️ Load into Editor", on_click=load_into_editor, args=(meta_data,)):
                            st.rerun()

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
