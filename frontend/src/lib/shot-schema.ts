// Le « cahier des charges » d'un plan : les CHAMPS de découpage (inspirés du
// découpage ciné) qui guident l'écriture d'un prompt système. Chaque champ est
// vide au départ (le cahier des charges, pas rempli) et accepte des {trous}.
// Schéma générique (clé → texte) pour l'étendre sans migration côté stockage.

export interface ShotField {
  key: string
  label: string
  placeholder: string
  multiline?: boolean
}

export interface ShotSection {
  title: string
  hint: string
  fields: ShotField[]
}

export const SHOT_SCHEMA: ShotSection[] = [
  {
    title: "Visuel",
    hint: "Décrit l'image / la première frame",
    fields: [
      { key: "decor", label: "Décor / lieu", placeholder: "un tunnel de métro abandonné, {détail_lieu}", multiline: true },
      { key: "sujet", label: "Sujet à l'écran", placeholder: "personnage / paysage / objet / POV" },
      { key: "cadrage", label: "Cadrage", placeholder: "gros plan · plan large · plongée · POV" },
      { key: "lumiere", label: "Lumière & ambiance", placeholder: "sombre, néons vacillants, contre-jour" },
    ],
  },
  {
    title: "Mouvement",
    hint: "Vidéo uniquement",
    fields: [
      { key: "action", label: "Action", placeholder: "il court, {réaction}", multiline: true },
      { key: "camera", label: "Mouvement caméra", placeholder: "fixe · travelling avant · tilt · à l'épaule" },
    ],
  },
  {
    title: "Son",
    hint: "Voix / dialogue",
    fields: [
      { key: "narration", label: "Narration (FR)", placeholder: "texte du conteur…", multiline: true },
      { key: "dialogue", label: "Dialogue", placeholder: "Personnage : réplique… (multi-perso)", multiline: true },
    ],
  },
]
