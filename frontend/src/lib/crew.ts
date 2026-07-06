// Le casting du studio — miroir de `src/features/crew/roster.py`.
// Les 5 phases du cinéma + les agents-métiers de chacune, pour la salle de
// production (PhaseRail + CrewPanel). Vocabulaire hybride : titre ciné + sous-titre créateur.

import {
  PenLine,
  Palette,
  Clapperboard,
  Mic,
  Video,
  Scissors,
  AudioLines,
  Megaphone,
  type LucideIcon,
} from "lucide-react"

export type PhaseKey =
  | "developpement"
  | "preproduction"
  | "tournage"
  | "postproduction"
  | "distribution"

export interface Phase {
  key: PhaseKey
  title: string // mot ciné
  subtitle: string // créateur
}

export const PHASES: Phase[] = [
  { key: "developpement", title: "Développement", subtitle: "l'idée devient un projet" },
  { key: "preproduction", title: "Préproduction", subtitle: "découpage & storyboard" },
  { key: "tournage", title: "Tournage", subtitle: "on capte les plans" },
  { key: "postproduction", title: "Postproduction", subtitle: "montage & rendu" },
  { key: "distribution", title: "Distribution", subtitle: "titre, hashtags & export" },
]

export interface CrewRole {
  key: string
  phase: PhaseKey
  title: string // métier (ciné)
  subtitle: string // ce qu'il fait
  produces: string
  icon: LucideIcon
}

export const CREW: CrewRole[] = [
  { key: "scenariste", phase: "developpement", title: "Scénariste", subtitle: "transforme l'idée en découpage de scènes", produces: "le découpage", icon: PenLine },
  { key: "directeur_artistique", phase: "preproduction", title: "Directeur artistique", subtitle: "pose l'identité visuelle et les décors", produces: "le storyboard", icon: Palette },
  { key: "chef_operateur", phase: "preproduction", title: "Chef opérateur", subtitle: "découpe chaque scène en plans", produces: "les plans", icon: Clapperboard },
  { key: "dialoguiste", phase: "preproduction", title: "Dialoguiste", subtitle: "écrit la narration et les dialogues", produces: "la narration", icon: Mic },
  { key: "tournage", phase: "tournage", title: "Équipe de tournage", subtitle: "exécute les prompts et capte les prises", produces: "les rushes", icon: Video },
  { key: "monteur", phase: "postproduction", title: "Monteur", subtitle: "assemble les plans et règle le rythme", produces: "le montage", icon: Scissors },
  { key: "inge_son", phase: "postproduction", title: "Ingé son", subtitle: "habille la voix et le son", produces: "le son", icon: AudioLines },
  { key: "attache_presse", phase: "distribution", title: "Attaché de presse", subtitle: "écrit titre, description, hashtags et hook", produces: "la fiche de sortie", icon: Megaphone },
]

export const crewForPhase = (phase: PhaseKey): CrewRole[] =>
  CREW.filter((r) => r.phase === phase)
