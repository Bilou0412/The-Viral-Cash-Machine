# Design — Ré-orchestrer la table ronde (crew_room) en boîte de prod qui débat

> **Statut : Phase 1 + 2 IMPLÉMENTÉES (in-house, éco).** Périmètre restreint au `crew_room`
> (le débat d'UNE scène). Décision associée : `docs/DECISIONS.md`.
>
> **Décision d'ingénierie (éco et efficace) :** on réalise l'architecture ci-dessous **en
> Python pur** (fan-out par threads + boucle de superviseur), **sans la dépendance LangGraph**.
> Le graphe actuel est linéaire-avec-une-boucle : un moteur de graphe tiers (deps lourdes,
> friction mypy-strict, courbe) ne se justifie pas encore. **LangGraph reste la cible** dès que
> le graphe deviendra vraiment dynamique (branches conditionnelles multiples, checkpointing,
> human-in-the-loop) — cf. Phase 3. Le contrat de code (ports + Fake offline) est identique, donc
> **basculer vers LangGraph plus tard ne touchera que l'intérieur de `engine.run_scene_room`**.

## 1. But

Orchestrer **les protagonistes de la table ronde** comme une vraie équipe de prod : le
**réalisateur** pose le contrat, les **départements** (directeur artistique, chef opérateur,
casting, dialoguiste) travaillent, puis un **superviseur** relit la scène assemblée et
**renvoie retravailler** ce qui ne va pas — en boucle, jusqu'à ce que ce soit bon. Aujourd'hui
c'est un enchaînement figé ; on veut un **débat piloté** (parallèle + boucles + état partagé).

## 2. État actuel (`src/features/crew_room/engine.py`)

`run_scene_room(brief, scene_brief, memory, *, director, drafters, revision_rounds=1)` :

1. `contract = director.define(...)` — le réalisateur liste les plans.
2. `first = [drafters.fill(dept) for dept in DEPARTMENTS]` — **4 appels EN SÉRIE**.
3. `scene = merge_drafts(contract, first)` — fusion des champs disjoints (`_FIELD_OWNER`).
4. `for _ in range(revision_rounds)` : `revised = [drafters.revise(dept) …]` (**4 appels en série**) → re-merge.
5. `RoomResult(scene, new_characters, transcript)`.

**Limites** (à l'origine du 502 sur `scenes/next`) :

- **Séquentiel** : ~9 appels OpenAI à la file → lent, et **un seul échec fait tout tomber**.
- **Révision aveugle et fixe** : `revision_rounds=1`, chaque département « ajuste » sans qu'un
  responsable décide *quoi* corriger ni *quand s'arrêter*. Pas de vrai jugement d'ensemble.
- **Flux codé en dur** : impossible d'exprimer « refais seulement le casting du plan 2 ».

## 3. Cible : le `crew_room` devient un graphe (LangGraph)

**Choix de moteur : LangGraph** (machine à états/graphe), pas LangChain (couche d'abstraction)
ni CrewAI (trop opinionated pour notre rigueur : coût maîtrisé, sorties structurées, tests
offline). LangGraph modélise nativement ce qu'on veut : **nœuds = protagonistes, arêtes =
handoffs conditionnels, state = mémoire de prod, fan-out = parallélisme, boucles = révision**.

### 3.1 Le contrat EXTERNE ne change pas (invariant clé)

`run_scene_room(...) -> RoomResult` **garde sa signature**. On remplace **l'intérieur** par un
graphe compilé. Le service `build_next_scene` (`services/room.py`) et la route
`POST /documents/{id}/scenes/next` **ne changent pas**. → aucun impact sur le rail v5
(`EditorDocument → compile_shot → document_to_spec → MP4`), ni sur le front.

### 3.2 Les nœuds appellent les PORTS existants (le Fake survit)

Les nœuds du graphe appellent `director.define(...)` / `drafters.fill(...)` / `drafters.revise(...)`
— **les mêmes `Protocol`** (`ContractAgent`, `Drafter`) qu'aujourd'hui. Donc :

- **Offline** : on compile le graphe avec `FakeContractAgent` / `FakeDrafter` → **déterministe,
  sans réseau**. Les tests restent offline (la règle qu'on garde).
- LangGraph n'orchestre que du **contrôle de flux** ; il n'introduit **aucun** couplage OpenAI.

### 3.3 Le state du graphe

```
SceneRoomState (TypedDict, réducteurs annotés) :
  # entrées (constantes)
  brief, scene_brief, memory
  # produits, écrits par les nœuds
  contract:  SceneContract | None
  drafts:    dict[department -> Draft]      # réducteur = merge de clés (écritures //)
  scene:     ScenePlan | None               # après merge
  # boucle de révision
  round:     int
  max_rounds: int
  redo:      dict[department -> notes]       # ce que le superviseur renvoie corriger
  # traçabilité (déjà exploitée par la SceneRoom)
  transcript: list[Turn]                     # réducteur = append (operator.add)
```

Les écritures parallèles (les 4 départements) imposent des **réducteurs** : `drafts` fusionne
les clés, `transcript` concatène. C'est le point technique à soigner.

### 3.4 Les nœuds et les arêtes (le débat)

```
        ┌──────────────┐
        │  contract    │  réalisateur.define()   (retry sur échec transitoire)
        └──────┬───────┘
     fan-out (parallèle) sur les 4 départements
   ┌────────┬────────┬────────┬────────┐
   ▼        ▼        ▼        ▼         (chaque nœud : fill() ou revise() si redo[dept])
  DA     chef_op   casting  dialoguiste
   └────────┴────────┴────────┴────────┘
                    ▼
              ┌──────────┐
              │  merge   │  merge_drafts(contract, drafts) -> scene
              └────┬─────┘
                   ▼
           ┌───────────────┐
           │  superviseur  │  Reviewer.review(scene, …) -> verdict
           └──────┬────────┘
        arête CONDITIONNELLE :
          - verdict OK  OU  round >= max_rounds  → END
          - sinon : round++, redo = depts flaggés → retour au fan-out (revise)
```

**Parallélisme** : les 4 départements tournent **en même temps** → latence ÷ ~4 et surtout
**bien moins de points de rupture séquentiels** (le 502 disparaît structurellement).

**Retries** : politique de retry **par nœud** (transitoire : reset réseau, 5xx, JSON malformé),
ce qui remplace/complète le retry ad-hoc de PR #53.

### 3.5 La nouveauté produit : le SUPERVISEUR

Nouveau port **`Reviewer`** (le réalisateur en 2ᵉ casquette, ou un rôle « superviseur » dédié —
*question ouverte*) :

```
Reviewer.review(*, scene, contract, brief, scene_brief, memory) -> ReviewVerdict
ReviewVerdict(ok: bool, redo: dict[department -> notes])
```

- **Fake** : renvoie `ok=True` déterministe → les tests offline **terminent** (pas de boucle infinie).
- **OpenAI** : critique la scène assemblée (cohérence décor/lumière/jeu/dialogue vs brief +
  continuité) et **flague les départements** à retravailler avec des notes ciblées.

C'est **lui** qui « orchestre les protagonistes » : il décide *quoi* renvoyer et *quand clore*.

## 4. Plan par phases (chaque phase = 1 PR vérifiable, rail intact)

- **Phase 1 — Parallélisme (in-house). ✅ FAIT.**
  `engine.run_scene_room` : les 4 départements remplissent **en parallèle** (`ThreadPoolExecutor`,
  appels LLM I/O-bound). Mêmes champs qu'avant (déterministe côté Fake) → tests existants verts.
  Réduit la latence (~÷4) et la surface d'échec séquentiel (le 502). *Retry par appel : cf. PR #53,
  complémentaire.*
- **Phase 2 — Le superviseur (le vrai débat). ✅ FAIT.**
  Nouveau port `Reviewer` (Fake + OpenAI) + boucle : le réalisateur relit la scène assemblée et
  **renvoie corriger les départements ciblés** (`redo` par département + consigne), en révision
  **parallèle**, jusqu'à validation ou `max_rounds` (=2). Le `transcript` gagne les tours de débat.
  **Bonus livré** : les plans de la table ronde sont désormais **bornés à 5 s** (`split_overlong_shots`
  dans `build_next_scene`) — la hiérarchie « bouts de 5 s » vaut aussi pour ce chemin.
- **Phase 3 — À venir.**
  (a) **Chaînage dernière-frame → init du plan suivant** (continuité i2v) — *absent du rail
  canonique VideoSpec* (n'existe qu'en legacy adventure), à câbler dans `resolve_real.py` /
  `compile_spec.py` ; c'est une feature **couche rendu**, indépendante de l'orchestration.
  (b) Débat **visible en direct** dans la SceneRoom (`transcript` + SSE déjà là).
  (c) *checkpointing* + *human-in-the-loop* (approuver le gagnant) au niveau **production** →
  c'est là que **LangGraph** deviendra pertinent (graphe dynamique + reprise + interrupt).

## 5. Coûts / risques (les yeux ouverts)

- **Deps** : `langgraph` (tire `langchain-core`). Poids acceptable, pur Python (offline OK).
- **mypy strict** : LangGraph n'est pas typé strict → **override tolérant** `langgraph.*` /
  `langchain_core.*` dans `pyproject.toml` (comme `openai.*` aujourd'hui). Notre code reste strict.
- **Coût/latence** : le parallélisme **réduit** la latence ; les boucles de révision **ajoutent**
  des tours → **borne `max_rounds`** (ex. 2) pour plafonner le coût (cohérent avec « ne régénérer
  que ce qu'on touche »).
- **Verrou** : dépendance à l'écosystème LangGraph — atténué car il n'orchestre que le flux,
  derrière nos ports (réversible : on peut revenir à un `engine.py` maison si besoin).
- **Règle d'archi** : `.claude/rules/architecture.md` sera **amendé** (le « zéro framework »
  devient « zéro framework SAUF l'orchestration d'agents, derrière les ports, Fake préservé »).

## 6. Ce qui NE bouge pas

Le document v5, `compile_shot`, `describe_document`, `document_to_spec`, le rendu, les ports
`ContractAgent`/`Drafter`, le service `build_next_scene`, la route, le front. On ne touche
qu'**au cerveau d'orchestration** d'une scène.

## 7. Questions ouvertes (à trancher avant Phase 1)

1. **Superviseur = réalisateur (2ᵉ casquette) ou rôle dédié ?** *(je penche : le réalisateur —
   c'est lui qui possède la scène.)*
2. **`max_rounds` de révision ?** *(je penche : 2.)*
3. **Débat visible dans l'UI dès la Phase 2, ou Phase 3 ?**
4. **Départements en parallèle réel** (threads, car SDK OpenAI synchrone) **ou** async ? *(je
   penche : parallélisme par thread via l'exécuteur LangGraph — pas de réécriture async.)*
5. **On garde le retry de PR #53** en plus du retry par nœud, ou le nœud le remplace ?
