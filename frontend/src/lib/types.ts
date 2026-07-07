// Domain types mirroring the live U1 API contract (FastAPI). Verified against the
// running server's responses. Visual prompt fields are EN, dialogue/narration FR.

export type EpisodeStatus = "draft" | "assets" | "montage" | "done"

export type AssetType = "image" | "video" | "audio"

export type AssetStatus = "pending" | "generating" | "ready" | "failed" | "error"

// ── DB-backed resources ────────────────────────────────────────────────

export interface Project {
  id: number
  name: string
  created_at: string
  settings_json: string | null
}

export interface Episode {
  id: number
  project_id: number
  title: string
  status: EpisodeStatus
  format: string // "aventure"
  theme: string // "horror" | … (see GET /themes)
  draft_mode: boolean
  duration_s: number | null
  final_path: string | null
  created_at: string
}

// ── Themes (GET /themes) ───────────────────────────────────────────────

export interface Theme {
  name: string // machine key, e.g. "horror"
  label: string // human label (FR), e.g. "Horreur"
}

// ── AdventureScript (mirror of adventure.py) ───────────────────────────

export interface VoiceProfile {
  description: string // EN
}

export interface Choice {
  label_fr: string
  image_desc: string // EN
  is_fatal: boolean
}

export interface Round {
  action_desc: string
  action_narration_fr: string
  environment_desc: string
  danger_desc: string
  environment_narration_fr: string
  character_line_fr: string
  character_delivery: string
  choices: [Choice, Choice]
  choice_narration_fr: string
  fatal_kill_desc: string
  fatal_pov_reaction: string
  fatal_narration_fr: string
  survival_outcome_desc: string
  survival_narration_fr: string
}

export interface AdventureScript {
  char_left_name: string
  char_right_name: string
  char_left_desc: string
  char_right_desc: string
  char_left_voice: VoiceProfile
  char_right_voice: VoiceProfile
  transition_narration_fr: string
  rounds: [Round, Round, Round]
  epilogue_other_desc: string
  epilogue_narration_fr: string
}

// ── Beats (GET /episodes/{id}/beats) ───────────────────────────────────
// Flat list; the unique key is (round_index, beat). `beat` is a composite key
// like "action.frame" | "action.motion" | "choice.0" | "narration" |
// "character.voice" | "epilogue.frame". round_index is null for transition
// narration and the epilogue.

export interface BeatEntry {
  round_index: number | null
  beat: string
  kind: AssetType
  image_prompt: string | null
  motion_prompt: string | null
  text: string | null
}

export interface BeatsResponse {
  episode_id: number
  assets: BeatEntry[]
}

// ── Assets (GET /episodes/{id}/assets) ─────────────────────────────────

export interface Asset {
  id: number
  episode_id: number
  round_index: number | null
  beat: string
  kind: AssetType
  prompt: string
  local_path: string | null
  status: AssetStatus
  draft: boolean
  excluded: boolean // écarté du montage par l'utilisateur
  sha: string | null
  created_at: string
}

// ── Cost (GET /episodes/{id}/cost) ─────────────────────────────────────

export interface CostBreakdownRow {
  model: string
  units: number
  unit_kind: "image" | "second" | "kchar"
  amount_usd: number
}

export interface CostEstimate {
  episode_id: number
  estimated_usd: number
  actual_usd: number
  breakdown: CostBreakdownRow[]
}

// ── Library (GET /library) ─────────────────────────────────────────────

export interface LibraryItem {
  episode_id: number
  title: string
  project_id: number
  status: EpisodeStatus
  duration_s: number | null
  final_path: string | null
}

// ── SSE event payload (GET /events/{episode_id}) ───────────────────────

export type JobEventType =
  | "generation_started"
  | "asset_started"
  | "asset_ready"
  | "asset_failed"
  | "generation_done"
  | "produce_done"

export interface JobEvent {
  type: JobEventType
  asset_id?: number
  beat?: string
  kind?: AssetType
  index?: number
  local_path?: string
  amount_usd?: number
  total?: number
}

// ── Request bodies ─────────────────────────────────────────────────────

export interface CreateEpisodeBody {
  project_id: number
  title: string
  draft_mode: boolean
  theme?: string // default "horror" server-side
  brief?: Brief // brief du producteur (optionnel)
}

export interface GenerateScriptBody {
  prompt: string
  char_left_name?: string
  char_right_name?: string
  char_left_desc?: string
  char_right_desc?: string
  n_rounds?: number // 1..8, default 3
}

export interface UpdateAssetBody {
  prompt?: string
  excluded?: boolean
}

// ── Editor (E5) — node-based brick editor ──────────────────────────────
// Mirrors the backend EditorDocument + RenderModel contracts. The editor lets
// the user assemble a video from "bricks" (generative or media/text/layer)
// laid out on tracks, then derives a RenderModel for preview/render.

// Brick palette (GET /api/bricks). Generative kinds only; media/text/layer are
// hardcoded client-side.
export type GenerativeKind = "image" | "video" | "voice"

export interface BrickSpec {
  kind: GenerativeKind
  required_fields: string[]
  preferred_models: string[]
}

// Dynamic model form (GET /api/models/{owner}/{name}/form).
export type FormFieldType =
  | "string"
  | "integer"
  | "number"
  | "boolean"
  | "enum"
  | "file"
  | "array"

export interface FormField {
  name: string
  type: FormFieldType
  required: boolean
  default: unknown
  enum: string[] | null
  description: string
  order: number
  // Libellé métier FR (fallback = nom brut embelli côté backend). `help` optionnel.
  label?: string
  help?: string
}

export interface ModelForm {
  model_ref: string
  version_id: string
  fields: FormField[]
}

// Model search (GET /api/models/search?kind=&q=).
export interface ModelSearchResult {
  owner: string
  name: string
  cover: string | null
  description: string
}

// ── EditorDocument ─────────────────────────────────────────────────────

export interface Canvas {
  width: number
  height: number
  fps: number
}

export interface GlobalContext {
  text: string
  characters: Record<string, string>
  art_direction: string
  extra: Record<string, string>
}

export interface TrackDef {
  index: number
  role: string
}

export type LayerType = "text" | "imported_media" | "png_overlay" | "narration"

export interface Layer {
  type: LayerType
  z: number
  payload: Record<string, unknown>
}

export interface Placement {
  track: number
  start: number
  duration: number
}

export type BrickType = "image" | "video" | "voice" | "media" | "text" | "clip"

export interface GenerativeBrick {
  id: string
  type: GenerativeKind
  model_ref: string
  params: Record<string, unknown>
  context_overrides?: Partial<GlobalContext>
  preset_id?: string
  layers: Layer[]
  placement: Placement
}

export interface MediaBrick {
  id: string
  type: "media"
  asset_ref?: string
  source_path?: string
  layers: Layer[]
  placement: Placement
}

export interface TextBrick {
  id: string
  type: "text"
  payload: Record<string, unknown>
  placement: Placement
}

// Brique COMPOSITE (générée par le script) : un asset = image (+ motion si vidéo)
// + enfants voix. C'est l'unité RÉVISÉE (R2). `params` = tous les inputs du modèle.
export interface GenNode {
  model_ref: string
  params: Record<string, unknown>
}

export interface AudioChild {
  id: string
  role: "narration" | "dialogue"
  model_ref: string
  params: Record<string, unknown>
}

// v5 — descripteur 3 niveaux (Vidéo → Scène → Plan). Le `shot` = le PLAN ; le
// décor/lumière ambiante viennent de la Scène (résolus au build backend). `shot`
// absent → prompt-blob legacy.
export interface Lumiere {
  sources: string; direction: string; qualite: string; temperature: string; contraste: string
}
export interface Cadre { taille_plan: string; focale: string; angle_hauteur: string; mise_au_point: string }
export interface Profondeur { avant_plan: string; plan_moyen: string; arriere_plan: string }
export interface Camera { type: string; vitesse: string; depart_arrivee: string }
export interface PersonnagePresent {
  ref: string; action: string; trajectoire: string; vitesse: string
  expression: string; etat_debut: string; etat_fin: string
}
export interface ElementSecondaire { quoi: string; mouvement: string; etat_debut: string; etat_fin: string }
export interface Physique { element: string; comportement: string; intensite_direction: string }
export interface LumiereTemps { ce_qui_change: string; depart_arrivee: string }
export interface Son {
  dialogue_voix: string; bruitage_sfx: string; perspective_mixage: string
  dynamique_silence: string; ambiance_override: string; transition_audio: string
}
export interface Segment { debut_s: number; fin_s: number; image_camera: string; action_sujet: string; son: string }
export interface Continuite { lien_precedent: string; lien_suivant: string }

export interface ShotBrief {
  start_image: string
  cadre: Cadre
  profondeur: Profondeur
  camera: Camera
  personnages_presents: PersonnagePresent[]
  elements_secondaires: ElementSecondaire[]
  physique_environnement: Physique[]
  lumiere_override?: Lumiere | null
  lumiere_temps: LumiereTemps
  son: Son
  timeline: Segment[]
  intention_plan: string
  continuite: Continuite
}

// Fiche de la BIBLE perso (identité récurrente).
export interface CharacterEntry {
  id: string
  name: string
  appearance: string
  wardrobe: string
  voice_id: string
  traits: string
}

// Fiche de la BIBLE décor (le lieu défini une fois, référencé par les scènes).
export interface LocationEntry {
  ref: string
  lieu: string
  echelle: string
  int_ext: string
  layout_spatial: string
  palette: string
  matieres: string
  props_fixes: string[]
  lumiere_base: Lumiere
}

export interface ClipBrick {
  id: string
  type: "clip"
  kind: "video" | "photo"
  image: GenNode
  motion?: GenNode | null
  shot?: ShotBrief | null
  children: AudioChild[]
  context_overrides?: Partial<GlobalContext> | null
  preset_id?: number | null
  layers?: Layer[]
  placement: Placement
}

export type Brick = GenerativeBrick | MediaBrick | TextBrick | ClipBrick

export const isClipBrick = (b: Brick): b is ClipBrick => b.type === "clip"

// Regroupement narratif de briques (v3) — un index vers `bricks`, pas une
// imbrication. Une scène = un contexte concentré (photo d'environnement + plans).
export interface Scene {
  id: string
  title: string
  context: GlobalContext
  environment_photo_ref: string
  shot_ids: string[]
  // v5 — la scène référence un décor (bible) et le fait varier (hérité par ses plans).
  location_ref?: string
  epoque_override?: string
  saison?: string
  moment_jour?: string
  meteo?: string
  lumiere_ambiante?: Lumiere
  mood?: string
  ambiance_sonore?: string
  musique_override?: string
  intention_scene?: string
}

export interface RenderMeta {
  ratio: string; fps: number; resolution: string
  style_rendu: string; grain_etalonnage: string; epoque_defaut: string
}
export interface IntentionGlobale { genre: string; ton: string; arc_narratif: string }

export interface EditorDoc {
  schema_version: number
  title: string
  canvas: Canvas
  global_context: GlobalContext
  tracks: TrackDef[]
  bricks: Brick[]
  scenes?: Scene[]
  bible?: CharacterEntry[]
  // v5 — niveau VIDÉO.
  meta?: RenderMeta
  intention_globale?: IntentionGlobale
  musique_score?: string
  location_bible?: LocationEntry[]
}

export interface EditorDocument {
  id: string
  project_id: number
  title: string
  doc: EditorDoc
}

// Quel décrypteur a produit les scènes : "openai" (réel) ou "fake" (démo /
// placeholder, renvoyé tant qu'aucune clé OpenAI n'est configurée).
export type DecomposerSource = "openai" | "fake"

export interface SceneDocumentResult extends EditorDocument {
  source?: DecomposerSource
}

// Résultat de la direction artistique : le document réécrit (prompts d'environnement
// + art direction) + quel moteur l'a produit (openai/fake).
export interface ArtDirectionResult extends EditorDocument {
  source?: DecomposerSource
}

// Résultat du dialoguiste : le document réécrit (textes parlés) + le moteur.
export interface DialogueResult extends EditorDocument {
  source?: DecomposerSource
}

// Table ronde — création scène par scène (les agents discutent).
export interface Turn {
  role: string      // clé du métier qui parle (cf. crew.ts)
  message: string
}
export interface ArcScene {
  id: string
  title: string
}
export interface ScenePlanResult {
  id: string        // id du document créé
  title: string
  doc: EditorDoc
  arc: ArcScene[]
  source?: DecomposerSource
}
export interface BuildSceneResult {
  id: string
  scene_id: string
  title: string
  transcript: Turn[]
  remaining: string[]
  doc: EditorDoc
  source?: DecomposerSource
}
export interface ScenesState {
  arc: ArcScene[]
  built: string[]
  remaining: string[]
}

// Le brief du producteur (phase développement) — le cahier des charges qui
// oriente toute la chaîne. Proposé par l'agent producteur, éditable.
export type Platform = "tiktok" | "reels" | "shorts" | "youtube_short"

export interface Brief {
  objectif: string
  audience: string
  plateforme: Platform
  duree_s: number
  budget_usd: number
  ton: string
  langue: string
  notes: string
}

export interface BriefResult extends Brief {
  source?: DecomposerSource
}

// Fiche de sortie écrite par l'attaché de presse / Growth (phase distribution).
export interface DistributionKit {
  title: string
  description: string
  hashtags: string[]
  hook: string
}

export interface DistributionResult extends DistributionKit {
  id?: string
  source?: DecomposerSource
}

export interface EditorDocumentSummary {
  id: string
  project_id: number
  title: string
}

export interface CreateEditorDocumentBody {
  project_id: number
  title: string
}

// ── Templates (T1) — bibliothèque de structures réutilisables ──────────
// Un template décrit le CONTENANT (structure de la timeline), jamais le contenu :
// une liste ordonnée de slots (vidéo/photo, durée, format, narration).
export interface TemplateSlot {
  id: string
  kind: "video" | "photo"
  duration: number
  aspect_ratio: string
  resolution: string
  narration: boolean
}

export interface Template {
  id: string
  name: string
  slots: TemplateSlot[]
}

export interface TemplateSummary {
  id: string
  name: string
  slot_count: number
  total_duration: number
}

export interface CreateTemplateBody {
  name: string
  slots: TemplateSlot[]
}

// ── Templates de prompt système (T2.1) — l'identité + la trame à trous ──
// Un prompt système par brique/rôle, à trous ({token}) ; les trous alimentent
// le questionnaire. `holes` est dérivé côté serveur (ordre d'apparition).
export interface RolePrompt {
  id: string
  label: string
  // Champs du cahier des charges (clé du schéma → texte à trous). Cf. shot-schema.
  fields: Record<string, string>
}

export interface PromptTemplate {
  id: string
  name: string
  identity: string
  roles: RolePrompt[]
  holes: string[]
}

export interface PromptTemplateSummary {
  id: string
  name: string
  role_count: number
  hole_count: number
}

export interface CreatePromptTemplateBody {
  name: string
  identity: string
  roles: RolePrompt[]
}

// ── RenderModel (GET /api/editor/documents/{id}/render-model) ──────────

export type RenderMedia = "video" | "image" | "audio" | "text" | "overlay"

export interface RenderSubtitle {
  text: string
  start: number
  end: number
}

export interface RenderClip {
  id: string
  media: RenderMedia
  src?: string | null
  start: number
  duration: number
  track?: number
  z?: number
  text?: string
  style?: Record<string, unknown>
  subtitles?: RenderSubtitle[]
  transform?: Record<string, unknown>
}

export interface RenderModel {
  version: "1.0"
  canvas: Canvas
  clips: RenderClip[]
  total_duration: number
}

// Type guards — narrow Brick on its discriminant.
export const isGenerativeBrick = (b: Brick): b is GenerativeBrick =>
  b.type === "image" || b.type === "video" || b.type === "voice"
export const isMediaBrick = (b: Brick): b is MediaBrick => b.type === "media"
export const isTextBrick = (b: Brick): b is TextBrick => b.type === "text"

// Settings — BYOK API keys (status only; the secret is never returned).
export interface KeysStatus {
  openai_set: boolean
  replicate_set: boolean
}

// Auth (Phase B.1) — utilisateur courant. `is_admin` : seul l'admin peut générer
// en B.1 (clés globales). Le mot de passe / hash n'est jamais renvoyé.
export interface AuthUser {
  id: number
  email: string
  is_admin: boolean
}
