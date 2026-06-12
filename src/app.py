import streamlit as st
import os
import datetime
import json
from dataclasses import dataclass, field
from typing import List, Optional
from dotenv import load_dotenv
from openai import OpenAI

from .infra.download import download_file
from .infra.env import save_key_to_env
from .pipeline import Pipeline, VideoInstance as PipelineVideoInstance

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
    # Subtitles with timestamps
    character_subtitles: List[dict] = field(default_factory=list)
    narrator_subtitles: List[dict] = field(default_factory=list)
    # Head detection coordinates (normalized 0-1)
    head_l_x: float = 0.25
    head_l_y: float = 0.40
    head_r_x: float = 0.75
    head_r_y: float = 0.40

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


@st.cache_resource
def get_pipeline() -> Pipeline:
    """Get or create cached pipeline with injected dependencies."""
    return Pipeline()

st.title("🚀 ViralCashMachine_V2 - Dashboard")

# Initialize API Keys
init_replicate_token = os.getenv("REPLICATE_API_TOKEN", "")
init_openai_token = os.getenv("OPENAI_API_KEY", "")

# FORCE ENVIRONMENT PERSISTENCE
if init_replicate_token: os.environ["REPLICATE_API_TOKEN"] = init_replicate_token
if init_openai_token: os.environ["OPENAI_API_KEY"] = init_openai_token
openai_models = ["gpt-5.4-mini", "gpt-5.5-flagship", "gpt-5.4-thinking", "gpt-5.3-instant", "gpt-5-mini"]

if "main_replicate_token" not in st.session_state:
    st.session_state["main_replicate_token"] = init_replicate_token
if "main_openai_key" not in st.session_state:
    st.session_state["main_openai_key"] = init_openai_token

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
    replicate_api_token = st.text_input("Replicate Token", type="password", key="main_replicate_token")
    if replicate_api_token != init_replicate_token: save_key_to_env("REPLICATE_API_TOKEN", replicate_api_token)
    
    openai_api_key_input = st.text_input("OpenAI Key", type="password", key="main_openai_key")
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
    sync_instance_to_widgets(st.session_state.current_instance)

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
            
            gen_script = st.text_area("Script Idea", placeholder=placeholder_text, height=150, key="inst_gen_script")
            
            # --- CHARACTER SETUP UI ---
            st.divider()
            st.subheader("👤 Character Setup")
            c_col1, c_col2 = st.columns(2)
            with c_col1:
                st.write("**Monster Left (Speaker)**")
                inst.char_left_name = st.text_input("Name L", key="c_l_n")
                l_genders = ["Male", "Female", "Alien", "Unknown"]
                l_persos = ["Aggressive", "Deceptive", "Terrified", "Crazed"]
                inst.char_left_gender = st.selectbox("Gender L", l_genders, key="c_l_g")
                inst.char_left_personality = st.selectbox("Personality L", l_persos, key="c_l_p")
            with c_col2:
                st.write("**Monster Right (Target)**")
                inst.char_right_name = st.text_input("Name R", key="c_r_n")
                r_genders = ["Male", "Female", "Alien", "Unknown"]
                r_persos = ["Stoic", "Twitchy", "Menacing", "Feral", "Crazed"]
                inst.char_right_gender = st.selectbox("Gender R", r_genders, key="c_r_g")
                inst.char_right_personality = st.selectbox("Personality R", r_persos, key="c_r_p")

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
                                - NEVER use terms like 'hunched', 'crawling', 'leaning forward', 'predatory posture', 'sway', 'breathing', 'shifting', or 'floating'. These cause the video model to move the camera or the character's root.
                                - SAFE HORROR: Use terms like 'weathered', 'ashen', 'pale', 'aged', 'rough textured' instead of 'decayed', 'zombie', 'naked', or 'raw'.
                                - Describe monsters as STANDING UPRIGHT and FACING FORWARD. NO head movement. Only eyes and mouth animate.
                                
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
                            
                            # Update Instance Slots with strict cleanup
                            new_left_name = data.get("char_left_name", "Pierre")
                            new_right_name = data.get("char_right_name", "Julie")
                            
                            # EXTREME PLACEHOLDER CLEANUP (Anti-Monster logic)
                            bad_tokens = ["monster", "character", "creature", "subject", "entity", "left", "right", "name", "unknown", "placeholder"]
                            if not new_left_name or any(t in new_left_name.lower() for t in bad_tokens):
                                new_left_name = "Pierre" if inst.char_left_gender == "Male" else "Marie"
                            if not new_right_name or any(t in new_right_name.lower() for t in bad_tokens):
                                new_right_name = "Jacques" if inst.char_right_gender == "Male" else "Julie"
                            
                            inst.char_left_name = new_left_name
                            inst.char_right_name = new_right_name
                            inst.monster_left_desc = data.get("monster_left_desc", "")
                            inst.monster_right_desc = data.get("monster_right_desc", "")
                            inst.monster_left_idle = data.get("monster_left_idle", "")
                            inst.monster_right_idle = data.get("monster_right_idle", "")
                            inst.environment_desc = data.get("environment_desc", "")
                            
                            # MANDATORY SPEECH - LOCKED SYNC
                            inst.character_speech = "Choisi moi. Ne lui fais pas confiance, je sais ce dont il est capable."
                            inst.narration_script = f"Choisi ton compagnon pour la nuit, {inst.char_left_name} ou {inst.char_right_name} ?"
                            inst.choice_a = inst.char_left_name
                            inst.choice_b = inst.char_right_name
                            
                            # --- MASTER ARBITER ASSEMBLY ---
                            # 1. Video Prompt Assembly (ULTRA-FORCED FPS)
                            inst.video_prompt = (
                                f"[CAMERA] ABSOLUTE STATIC CAMERA. ZERO movement of any kind. ZERO drift. ZERO shake. ZERO pan. ZERO tilt. ZERO zoom. Frozen security camera perspective. Eye-level 1.7m. 9:16 vertical. "
                                f"[FOREGROUND_POV] First-person view. Two ungloved human hands visible at the BOTTOM of the frame, cut off at the wrist. NO forearms. NO sleeves. NO clothing. Skin is pale, ashen, weathered, rough textured. NO accessories. Hands at hip height, palms slightly inward, angled down. STANDING UPRIGHT POSE ONLY. HANDS ONLY move with micro finger curl adjustments. Camera itself NEVER moves. "
                                f"[ENV] {inst.environment_desc}. COMPLETELY STATIC BACKGROUND. No environmental animation. STATIC lighting. NO dynamic lights. NO flashlight. NO spotlight. Both characters fully lit and visible at all times. "
                                f"[MIDGROUND_LEFT] {inst.monster_left_desc}. FACING CAMERA. NOT moving toward camera. ABSOLUTE FIXED POSITION. Root locked to floor. ZERO translation. ZERO steps. NO advancing. ZERO head sway. ONLY eyes and mouth animate. Returns to neutral pose between actions. IDLE: {inst.monster_left_idle}. "
                                f"ACTION: Speaks directly to camera with intense eye-contact and full lip-sync. "
                                f"BEAT 1 - 'Choisi moi': aggressively taps own chest with fist, leaning forward. "
                                f"BEAT 2 - 'Ne lui fais pas confiance': NEVER breaks eye contact with camera, extends arm pointing accusingly to the right WITHOUT looking away, shakes head slowly while staring into camera. "
                                f"BEAT 3 - 'je sais ce dont il est capable': locks eyes back on camera, leans slightly forward with a slow threatening nod, expression darkens. "
                                f"Extreme facial articulation throughout. Returns to neutral idle after speech ends. "
                                f"[MIDGROUND_RIGHT] {inst.monster_right_desc}. FACING CAMERA. NOT moving toward camera. ABSOLUTE FIXED POSITION. Root locked to floor. ZERO translation. ZERO steps. NO advancing. ZERO head sway. ONLY eyes and mouth animate. Returns to neutral pose between actions. IDLE: {inst.monster_right_idle}."
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
        p_row1_col1, p_row1_col2 = st.columns(2)

        # STEP 1: ASSETS
        if p_row1_col1.button("🎬 [STEP 1] Generate All Assets", use_container_width=True):
            try:
                with st.spinner("🚀 Producing Assets..."):
                    pipeline = get_pipeline()
                    asset_bundle = pipeline.generate_assets(
                        project_name,
                        inst.id,
                        inst.video_prompt,
                        inst.freeze_image_prompt,
                        inst.character_speech,
                        inst.narration_script,
                        inst.type,
                    )
                    # Update instance with generated URLs
                    inst.narrator_audio_url = asset_bundle.narrator_audio_url
                    inst.character_audio_url = asset_bundle.character_audio_url
                    inst.freeze_image_url = asset_bundle.freeze_image_url
                    inst.video_url = asset_bundle.video_url
                    # Persist metadata
                    project_dir = os.path.join("exports", project_name, inst.id)
                    with open(os.path.join(project_dir, "metadata.json"), "w") as f:
                        json.dump(asdict(inst), f, indent=4)
                st.success("✅ Step 1: Assets Ready!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

        # STEP 2: MOVIEPY
        if p_row1_col2.button("🎞️ [STEP 2] Basic Compilation", use_container_width=True):
            try:
                with st.spinner("🎬 Running MoviePy..."):
                    # Load metadata to get head positions
                    project_dir = os.path.join("exports", project_name, inst.id)
                    meta_path = os.path.join(project_dir, "metadata.json")
                    if not os.path.exists(meta_path):
                        raise FileNotFoundError(f"metadata.json not found at {meta_path}")

                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)

                    # Create immutable VideoInstance from metadata
                    video_instance = VideoInstance(
                        project_name=project_name,
                        instance_id=inst.id,
                        char_left_name=meta.get("char_left_name", "Unknown"),
                        char_right_name=meta.get("char_right_name", "Unknown"),
                        head_l_x=meta.get("head_l_x", 0.25),
                        head_l_y=meta.get("head_l_y", 0.40),
                        head_r_x=meta.get("head_r_x", 0.75),
                        head_r_y=meta.get("head_r_y", 0.40),
                    )

                    # Compile video with immutable instance
                    pipeline = get_pipeline()
                    compiled_video = pipeline.compile_video(video_instance)
                st.success(f"✅ Step 2: Video Ready!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

        # --- CUMULATIVE PRODUCTION GALLERY ---
        st.divider()
        st.header("🎬 Production Gallery")
        project_dir = os.path.join("exports", project_name, inst.id)
        
        has_assets = os.path.exists(os.path.join(project_dir, "base_image.png"))
        has_final_vid = os.path.exists(os.path.join(project_dir, "final_video.mp4"))

        if not (has_assets or has_final_vid):
            st.info("No production results yet. Start with Step 1.")

        if has_final_vid:
            st.subheader("🏆 FINAL VIDEO (Step 2)")
            st.video(os.path.join(project_dir, "final_video.mp4"))
            st.success("✨ Compiled montage: intro → hook → narration → choice")
            st.divider()

        if has_assets:
            st.subheader("📦 Base Assets (Step 1)")
            r1, r2 = st.columns(2)
            r1.image(os.path.join(project_dir, "base_image.png"), caption="Base Image")
            if os.path.exists(os.path.join(project_dir, "video.mp4")):
                r2.video(os.path.join(project_dir, "video.mp4"))
                r2.caption("Raw AI Animation")

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
                        
                        p_col_1, p_col_2 = st.columns(2)
                        if p_col_1.button("♻️ Load into Editor", on_click=load_into_editor, args=(meta_data,), use_container_width=True):
                            st.rerun()
                        if p_col_2.button("🎞️ Compile Final Video", use_container_width=True):
                            with st.spinner("🎬 Compiling..."):
                                try:
                                    # Create immutable VideoInstance from metadata
                                    video_instance = VideoInstance(
                                        project_name=sel_proj,
                                        instance_id=sel_inst,
                                        char_left_name=meta_data.get("char_left_name", "Unknown"),
                                        char_right_name=meta_data.get("char_right_name", "Unknown"),
                                        head_l_x=meta_data.get("head_l_x", 0.25),
                                        head_l_y=meta_data.get("head_l_y", 0.40),
                                        head_r_x=meta_data.get("head_r_x", 0.75),
                                        head_r_y=meta_data.get("head_r_y", 0.40),
                                    )
                                    pipeline = get_pipeline()
                                    compiled_video = pipeline.compile_video(video_instance)
                                    st.success(f"✅ Video ready: {compiled_video.output_path}")
                                except Exception as e:
                                    st.error(f"Error: {e}")

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
