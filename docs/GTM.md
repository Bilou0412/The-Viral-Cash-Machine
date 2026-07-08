# GTM — Go-to-market (flagship d'abord)

> Stratégie de mise sur le marché. Direction tranchée : **flagship créable d'abord**,
> monétisation ensuite. Ce document est la carte ; l'exécution vit dans `ROADMAP.md`.

## La thèse

**VCM = une usine à moules viraux.** Pas un éditeur générique de plus : un petit nombre de
**formats ultra-niche** (moules), où la **STRUCTURE est fixe** (portée par le code) et le
**CONTENU est rempli par les agents**. L'humain arrive avec une idée, choisit un moule, les
agents construisent le template, il ne révise que ce qui compte, et il publie.

Le **flagship** est le format **horreur à choix multiple (CYOA)** : un compagnon, des manches,
des choix qui peuvent tuer, POV immersif. Forme identique, contenu variable → produit
reproductible et calibrable par les perfs réelles (le moat, cf. `features/performance`).

## Endgame (la boucle qui vend)

`Idée → moule → 3 variantes → prédiction → publication.` L'humain **n'approuve que le
gagnant** ; la découpe, la cohérence et le choix du hook sont portés par les agents et
calibrés par les perfs réelles. (cf. `scripts/endgame_demo.py`, `features/virality`.)

## Phases (flagship-first)

1. **Flagship créable** *(en cours)* — je viens, je choisis « Horreur-CYOA », les agents le
   construisent, je le vois **en entier en texte** (`describe_document`), je révise en briques.
   Rail unique v5 (cf. `.claude/rules/architecture.md`). C'est le cœur : *rien à vendre tant
   que le moule phare n'est pas créable proprement de bout en bout.*
2. **Boucle virale** — 3 variantes de hook → prédiction → publication du gagnant ; calibrage
   par perfs réelles. Le produit devient « une machine à itérer », pas « un éditeur ».
3. **2ᵉ et 3ᵉ moules** — un 2ᵉ format (ex. love-CYOA) valide la séparation structure/contenu ;
   au **3ᵉ**, on extrait le schéma de slots générique (règle de trois), pas avant.
4. **Monétisation** *(différé — Lot 4)* — crédits + paiement (Lemon Squeezy) + tier gratuit
   **watermarké** + landing/pricing. Le rendu coûte : le pricing suit le coût par génération
   (idempotence = on ne repaie jamais un asset `ready`).

## Cible & wedge

- **Wedge** : créateurs TikTok/Shorts/Reels sur les niches à fort replay (horreur interactive,
  dilemmes). Le format CYOA est *nativement* fait pour le commentaire (« j'aurais pris l'autre
  porte ») → engagement → distribution.
- **Promesse** : « une idée le matin, 3 variantes prêtes à poster le soir, sans monter ».
- **Différenciation** : pas un canvas vide (l'IA écrit, l'humain révise en briques) ; la
  qualité est **structurelle** (moule + compile_shot + discipline durée), pas au petit bonheur.

## Ce qui doit être vrai avant de vendre (definition of ready)

- [ ] Le flagship CYOA se crée depuis « Créer » (format aventure) de bout en bout.
- [ ] Les agents (casting/DA/dialoguiste/réalisateur) raffinent le CYOA v5.
- [ ] La vidéo est **visible en entier en texte** avant toute génération payante.
- [ ] La boucle 3-variantes → prédiction → publication tourne sur le flagship.
- [ ] Coût par vidéo mesuré → grille de crédits calée dessus.

## Non-objectifs (pour l'instant)

- Pas de branchement interactif réel (un short posté est linéaire ; le CYOA *met en scène* le
  choix, il ne le rend pas jouable).
- Pas d'éditeur de montage vierge (« l'IA écrit → je révise en briques », pas une timeline nue).
- Pas d'abstraction de format prématurée (< 3 moules → structure codée en dur).
