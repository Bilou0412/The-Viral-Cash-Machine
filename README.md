# 🚀 ViralCashMachine V2

[![English](https://img.shields.io/badge/Language-English-blue)](#english) [![Français](https://img.shields.io/badge/Langue-Fran%C3%A7ais-red)](#fran%C3%A7ais)

---

<a id="english"></a>
## 🇬🇧 English Version

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=Streamlit&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat&logo=openai&logoColor=white)
![Replicate](https://img.shields.io/badge/Replicate-000000?style=flat&logo=replicate&logoColor=white)

**ViralCashMachine V2** is a powerful Streamlit-based dashboard designed to fully automate the generation of highly engaging, AI-powered vertical video content (9:16) optimized for short-form platforms like TikTok, YouTube Shorts, and Instagram Reels.

### ✨ Key Features

- **🎬 Instance-Based Generation:** Automate the creation of "Video Instances" consisting of a dynamic video hook, a freeze-frame with narration, and interactive choices.
- **🤖 Multi-AI Orchestration:**
  - **Text & Prompts:** OpenAI (GPT-4/GPT-5 models) for script analysis and prompt engineering.
  - **Video Generation:** `prunaai/p-video` via Replicate.
  - **Image Generation:** `bytedance/seedream-4.5` via Replicate.
  - **Voice Synthesis:** `minimax/speech-2.8-turbo` via Replicate.
- **⚙️ 3-Step Production Pipeline:**
  1. **Assets Generation:** Synthesizes audio, creates base images, and renders raw AI video animations.
  2. **Raw Compilation:** Uses MoviePy to stitch assets together, add dynamic subtitles (Whisper), centered cinematic zooms, and character nameplates based on AI facial detection.
  3. **AI Upscaling & Polish:** Leverages **Real-ESRGAN** (NCNN Vulkan) for high-fidelity video upscaling and applies custom FFmpeg color grading for that premium "AMV" aesthetic.
- **📂 Project Management:** Built-in library to browse saved projects, preview assets, and manage your exports.

### 🛠️ Prerequisites

- **Python 3.8+** installed on your system.
- **API Keys** for:
  - [OpenAI](https://platform.openai.com/)
  - [Replicate](https://replicate.com/)
- FFmpeg (Required by MoviePy and the Color Grading pipeline).

### 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone git@github.com:Bilou0412/The-Viral-Cash-Machine.git
   cd The-Viral-Cash-Machine
   ```

2. **Install dependencies:**
   Run the setup script which will automatically install the requirements via pip:
   ```powershell
   .\setup.bat
   ```

3. **Environment Configuration:**
   - Copy the `.env.example` file and rename it to `.env`.
   - Add your API keys:
     ```env
     OPENAI_API_KEY=your_openai_key_here
     REPLICATE_API_TOKEN=your_replicate_token_here
     ```

### 💻 Usage

Start the Streamlit dashboard by running:
```powershell
.\start.bat
```

**The Workflow:**
1. **Design:** Input your script or prompt in the dashboard.
2. **Step 1 (Assets):** Click `Generate All Assets` to call the AI models and download the raw media.
3. **Step 2 (Compilation):** Run `Basic Compilation` to assemble the video, audio, and subtitles.
4. **Step 3 (Upscale):** Execute `AI Upscale` to enhance the final render using Real-ESRGAN to crisp 1080x1920 resolution.

---

<a id="français"></a>
## 🇫🇷 Version Française

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=Streamlit&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat&logo=openai&logoColor=white)
![Replicate](https://img.shields.io/badge/Replicate-000000?style=flat&logo=replicate&logoColor=white)

**ViralCashMachine V2** est un tableau de bord puissant basé sur Streamlit, conçu pour automatiser entièrement la génération de contenu vidéo vertical (9:16) ultra-engageant, propulsé par l'IA et optimisé pour les plateformes telles que TikTok, YouTube Shorts et Instagram Reels.

### ✨ Fonctionnalités Principales

- **🎬 Génération par Instance :** Automatisez la création d'"Instances Vidéo" comprenant un hook vidéo dynamique, un arrêt sur image avec narration, et des choix interactifs.
- **🤖 Orchestration Multi-IA :**
  - **Texte & Prompts :** OpenAI (modèles GPT-4/GPT-5) pour l'analyse de script et l'ingénierie de prompt.
  - **Génération Vidéo :** `prunaai/p-video` via Replicate.
  - **Génération d'Image :** `bytedance/seedream-4.5` via Replicate.
  - **Synthèse Vocale :** `minimax/speech-2.8-turbo` via Replicate.
- **⚙️ Pipeline de Production en 3 Étapes :**
  1. **Génération des Assets :** Synthétise l'audio, crée les images de base et effectue le rendu brut des animations vidéo IA.
  2. **Compilation Brute (Raw) :** Utilise MoviePy pour assembler les assets, ajouter des sous-titres dynamiques (Whisper), des zooms cinématiques centrés, et des plaques de noms de personnages basées sur la détection faciale IA.
  3. **Upscaling IA & Finitions :** Exploite **Real-ESRGAN** (NCNN Vulkan) pour un upscaling vidéo haute fidélité et applique une colorimétrie personnalisée via FFmpeg pour obtenir une esthétique "AMV" premium.
- **📂 Gestion de Projet :** Bibliothèque intégrée pour parcourir les projets sauvegardés, prévisualiser les assets et gérer vos exports.

### 🛠️ Prérequis

- **Python 3.8+** installé sur votre système.
- **Clés API** pour :
  - [OpenAI](https://platform.openai.com/)
  - [Replicate](https://replicate.com/)
- FFmpeg (Requis pour MoviePy et le pipeline de Colorimétrie).

### 🚀 Installation & Configuration

1. **Cloner le dépôt :**
   ```bash
   git clone git@github.com:Bilou0412/The-Viral-Cash-Machine.git
   cd The-Viral-Cash-Machine
   ```

2. **Installer les dépendances :**
   Exécutez le script d'installation qui installera automatiquement les prérequis via pip :
   ```powershell
   .\setup.bat
   ```

3. **Configuration de l'Environnement :**
   - Copiez le fichier `.env.example` et renommez-le en `.env`.
   - Ajoutez vos clés API :
     ```env
     OPENAI_API_KEY=votre_cle_openai_ici
     REPLICATE_API_TOKEN=votre_token_replicate_ici
     ```

### 💻 Utilisation

Démarrez le tableau de bord Streamlit en exécutant :
```powershell
.\start.bat
```

**Le Workflow :**
1. **Design :** Saisissez votre script ou prompt dans le tableau de bord.
2. **Étape 1 (Assets) :** Cliquez sur `Generate All Assets` pour appeler les modèles IA et télécharger les médias bruts.
3. **Étape 2 (Compilation) :** Exécutez `Basic Compilation` pour assembler la vidéo, l'audio et les sous-titres.
4. **Étape 3 (Upscale) :** Exécutez `AI Upscale` pour améliorer le rendu final en utilisant Real-ESRGAN pour obtenir une résolution nette de 1080x1920.

---

## 📂 Project Structure / Structure du Projet

```text
The-Viral-Cash-Machine/
├── app.py                  # Main Streamlit dashboard and UI logic
├── compiler.py             # Video rendering, MoviePy logic, and Real-ESRGAN upscaling
├── requirements.txt        # Python dependencies
├── setup.bat               # Environment setup script
├── start.bat               # Application launch script
├── bin/                    # Contains Real-ESRGAN executables and models
├── assets/                 # Fonts, sound effects, and static assets
├── src/                    # Core logic and workflow engine (bricks, traits, etc.)
└── exports/                # Auto-generated output directory for projects and instances
```
