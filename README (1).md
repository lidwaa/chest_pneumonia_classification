# Pipeline de tri de pages financières — README

Ce projet identifie automatiquement, dans des PDF financiers (numériques ou
scannés), les pages pertinentes (états financiers) et produit :
1. un **nouveau PDF par fichier source**, ne contenant que les pages pertinentes ;
2. un **fichier Excel global unique**, listant pour chaque PDF les pages gardées.

---

## 1. Contenu de la livraison

Vous recevez **2 notebooks** :

| Fichier | Contenu | À faire |
|---|---|---|
| `modules.ipynb` | Les 5 fichiers `.py` du pipeline, un par cellule | À exécuter **une seule fois** pour recréer les fichiers `.py` sur disque |
| `pipeline.ipynb` | Le notebook principal que vous utilisez à chaque traitement | À ouvrir et exécuter pour traiter vos PDF |

**Pourquoi deux notebooks et pas un seul fichier `.py` ?**
Le pipeline est volontairement découpé en modules indépendants (voir section 3)
pour que vous puissiez, par exemple, changer de moteur OCR sans toucher au
reste du code. `modules.ipynb` sert uniquement à transporter facilement ces
5 fichiers sous forme d'un seul notebook envoyable par email/Slack/etc. Une
fois exécuté, il "déplie" ces fichiers sur votre disque et vous travaillez
ensuite normalement avec `pipeline.ipynb`.

---

## 2. Installation

### 2.1 Dépendances Python
```bash
pip install pdfplumber pdf2image pytesseract pypdf pandas openpyxl
```

### 2.2 Dépendances système (OCR)
```bash
# Debian/Ubuntu
apt-get install tesseract-ocr tesseract-ocr-fra poppler-utils
```
- `tesseract-ocr` + `tesseract-ocr-fra` : moteur OCR (anglais + français)
- `poppler-utils` : fournit `pdftoppm`, utilisé pour rasteriser les PDF avant OCR

### 2.3 (Optionnel) Classification zero-shot
Uniquement si vous activez `use_zero_shot = True` dans la config :
```bash
pip install transformers torch
```

---

## 3. Mise en route pas à pas

### Étape 1 — Recréer les fichiers `.py`
1. Placez `modules.ipynb` et `pipeline.ipynb` **dans le même dossier**.
2. Ouvrez `modules.ipynb`.
3. Exécutez **toutes les cellules** (menu *Run → Run All Cells*, ou Kernel → Restart & Run All).
   → Chaque cellule utilise `%%writefile <nom>.py` pour écrire le fichier
   correspondant sur le disque, dans le dossier courant.
4. Une cellule de vérification à la fin confirme que les 5 fichiers ont bien
   été créés :
   ```
   config.py                 OK
   text_extraction.py        OK
   relevance.py              OK
   pdf_processor.py          OK
   report.py                 OK
   ```
   Vous n'avez besoin de refaire cette étape que si vous supprimez les
   fichiers `.py` ou changez de dossier de travail.

### Étape 2 — Traiter vos PDF
1. Ouvrez `pipeline.ipynb` (dans le même dossier).
2. Section 2 du notebook : déposez vos PDF financiers dans le dossier
   `input_pdfs/` (créé automatiquement), ou changez `INPUT_DIR` pour pointer
   vers un autre dossier.
3. Exécutez les cellules dans l'ordre (Run All).
4. Résultats produits :
   - **`output_pdfs/`** : un PDF par fichier source, avec uniquement les pages
     jugées pertinentes (même nom de fichier que l'original).
   - **`rapport_global.xlsx`** (à la racine, en dehors de `output_pdfs/`) :
     - onglet **Résumé** : une ligne par PDF traité (nombre de pages total,
       nombre et numéros des pages pertinentes, statut, erreur éventuelle).
     - onglet **Détail_pages** : une ligne par page traitée (pertinente ou
       non, score composite, mots-clés trouvés, méthode d'extraction
       utilisée — natif ou OCR). Utile pour auditer et ajuster les seuils.

---

## 4. Détail des fichiers `.py` (contenus dans `modules.ipynb`)

### `config.py` — Configuration centrale
Contient :
- `KEYWORDS_EN` / `KEYWORDS_FR` : toutes les variantes de titres d'états
  financiers à rechercher (Income Statement, Balance Sheet, Cash Flow
  Statement, Statement of Changes in Equity, Statement of Comprehensive
  Income, et leurs équivalents français : Compte de résultat, Bilan, Tableau
  des flux de trésorerie, etc.).
- `EXCLUDED_WORDS` : mots qui **excluent automatiquement** une page si
  présents, quel que soit le reste (mots-clés, densité) — par défaut
  "consolidated" / "consolidé" (voir section 6 ci-dessous).
- `DEFAULT_SETTINGS` : tous les seuils et poids réglables (voir section 5).

**C'est le seul fichier à modifier si vous voulez ajouter/retirer des
mots-clés ou changer les seuils par défaut.**

### `text_extraction.py` — Extraction du texte des pages
Définit une interface abstraite `TextExtractor` avec une seule méthode :
`extract_page_texts(pdf_path) -> List[PageText]`.

Trois implémentations :
- `NativeTextExtractor` : lit le texte déjà encodé dans le PDF (via
  `pdfplumber`). Rapide, mais renvoie du texte vide/quasi-vide sur les pages
  scannées (images).
- `TesseractOCRExtractor` : rasterise chaque page (`pdf2image` + `poppler`)
  puis applique l'OCR Tesseract (`pytesseract`). Fonctionne sur les PDF
  scannés.
- `HybridTextExtractor` (recommandé, utilisé par défaut dans `pipeline.ipynb`) :
  essaie d'abord l'extraction native, page par page ; si le texte natif d'une
  page est trop court (`native_text_min_chars`), bascule automatiquement sur
  l'OCR pour **cette page uniquement**. Cela permet de traiter dans un même
  document des pages numériques et des pages scannées, sans faire d'OCR
  inutilement sur les pages déjà en texte (plus rapide).

**Pour changer de moteur OCR** (EasyOCR, PaddleOCR, une API cloud comme Azure
Document Intelligence ou Google Vision, etc.) : créez une nouvelle classe qui
hérite de `TextExtractor` et respecte la même signature de méthode. Branchez
cette classe à la place de `TesseractOCRExtractor` dans la section 4 de
`pipeline.ipynb`. **Aucun autre fichier n'a besoin d'être modifié.**

### `relevance.py` — Scoring de pertinence
Définit une interface `RelevanceScorer` et plusieurs implémentations :

- `KeywordScorer` (règle 1) : normalise le texte (minuscules, sans accents,
  mots ignorés retirés) puis cherche chaque mot-clé de `config.py`. Renvoie
  la liste des mots-clés trouvés sur la page.
- `NumericDensityScorer` (règle 2) : calcule la proportion de caractères
  numériques dans le texte de la page (`nombre_de_chiffres / longueur_du_texte`),
  comparée à `numeric_density_threshold`. Les états financiers étant denses
  en chiffres, une page avec une forte densité numérique reçoit un score
  plus élevé.
- `ZeroShotScorer` (règle 3, optionnel) : classification zero-shot via un
  modèle Hugging Face local (désactivé par défaut). Le modèle par défaut
  proposé est `joeddav/xlm-roberta-large-xnli` — un modèle NLI multilingue
  (anglais/français) adapté à la classification zero-shot, plus approprié
  qu'un LLM génératif type "Gemma" pour cette tâche de classification binaire
  sans entraînement. Peut être remplacé par n'importe quel modèle compatible
  `pipeline("zero-shot-classification", ...)`.
- `CompositeScorer` : calcule **2 méthodes de décision en parallèle** pour
  chaque page (voir `settings["methods"]`) :
  1. **`density_only`** : pertinente si la densité numérique (+ zero-shot
     éventuel) dépasse `confirmation_threshold`, que le mot-clé matche ou non.
  2. **`keyword_and_density`** : pertinente seulement si un mot-clé matche
     **ET** que la densité confirme (mot-clé = condition d'entrée
     obligatoire, densité = confirmation).

  Les deux sont toujours calculées ; `settings["methods"]` décide
  lesquelles sont utilisées pour produire un/des PDF filtré(s). Par défaut,
  les deux sont actives, ce qui permet de comparer directement où elles
  sont d'accord et où elles divergent (typiquement : une page dense en
  chiffres mais sans mot-clé — continuation de tableau ou tableau non
  financier selon le cas).

### `pdf_processor.py` — Traitement d'un PDF / d'un dossier
- `process_single_pdf(...)` : extrait le texte de chaque page (via un
  `TextExtractor`), évalue sa pertinence (via un `CompositeScorer`), et
  écrit un nouveau PDF ne contenant que les pages pertinentes.
- `process_folder(...)` : applique `process_single_pdf` à tous les PDF d'un
  dossier, avec suivi console (nom du fichier, nombre de pages gardées).

Ce module ne connaît ni le détail de l'OCR ni celui du scoring : il dépend
uniquement des interfaces `TextExtractor` et `CompositeScorer`.

### `report.py` — Génération du rapport Excel
- `build_summary_dataframe(...)` : une ligne par PDF.
- `build_detail_dataframe(...)` : une ligne par page traitée.
- `write_excel_report(...)` : écrit les deux tableaux dans un seul fichier
  `.xlsx` (feuilles "Résumé" et "Détail_pages"), avec largeur de colonnes
  ajustée automatiquement.

---

## 5. Paramètres réglables (`config.py` → `DEFAULT_SETTINGS`)

| Paramètre | Rôle | Valeur par défaut |
|---|---|---|
| `extraction_mode` | `"hybrid"` (natif + OCR en secours), `"ocr_only"` (force l'OCR partout — à utiliser si le mode hybride lit mal vos PDF), ou `"native_only"` | `"hybrid"` |
| `ocr_lang` | Langues Tesseract | `"eng+fra"` |
| `ocr_dpi` | Résolution de rasterisation pour l'OCR | `300` |
| `ocr_psm` | Page Segmentation Mode Tesseract (`None`=auto ; essayez `6` ou `4` si l'OCR lit mal vos tableaux) | `None` |
| `native_text_min_chars` | Seuil (en caractères) sous lequel une page est considérée scannée et bascule sur l'OCR | `40` |
| `native_min_valid_char_ratio` | Proportion minimale de caractères "normaux" dans le texte natif ; en dessous, on suppose un problème d'encodage de police et on bascule sur l'OCR même si le texte est assez long | `0.85` |
| `methods` | Méthode(s) utilisée(s) pour filtrer : `["density_only", "keyword_and_density"]` (les deux, pour comparer) ou une liste à un seul élément | les deux |
| `exclude_pages_with_excluded_words` | Rejette automatiquement toute page contenant un mot de `EXCLUDED_WORDS` (ex: "consolidated"), pour les 2 méthodes | `True` |
| `excluded_words` | Liste personnalisée à la place de `EXCLUDED_WORDS` de `config.py` (`None` = utilise la liste par défaut) | `None` |
| `require_keyword_match` | *(obsolète, retiré)* — remplacé par `methods` ci-dessus | — |
| `fuzzy_word_presence` | Tolère un mot-clé à plusieurs mots cassé par l'OCR (mots présents séparément, même non adjacents) | `True` |
| `weight_numeric_density` | Poids de la densité numérique dans le score de confirmation | `0.7` |
| `weight_zero_shot` | Poids du zero-shot dans le score de confirmation (ignoré si désactivé) | `0.3` |
| `numeric_density_threshold` | Densité numérique (ratio) à partir de laquelle une page est jugée "riche en chiffres" | `0.06` |
| `numeric_min_digit_count` | Nombre minimal de chiffres en valeur absolue exigé (évite qu'un texte court avec juste une numérotation "1. 2. 3." fausse le ratio) | `15` |
| `confirmation_threshold` | Score de confirmation minimal pour garder une page **où un mot-clé a matché** | `0.5` |
| `enable_continuation_detection` | Garde automatiquement une page sans mot-clé mais dense en chiffres si elle suit une page pertinente (suite d'un tableau sur plusieurs pages) | `True` |
| `continuation_threshold` | Seuil de densité pour qu'une page de continuation soit acceptée | `0.6` |
| `review_margin` | Marge autour des seuils pour marquer une page "à vérifier" dans le rapport (n'affecte pas la décision) | `0.15` |
| `use_zero_shot` | Active/désactive le scorer zero-shot | `False` |
| `zero_shot_model` | Modèle Hugging Face utilisé si activé | `joeddav/xlm-roberta-large-xnli` |
| `enable_checkpoint` | Écrit une sauvegarde après chaque PDF ; relancer reprend où on s'était arrêté en cas de plantage | `True` |
| `checkpoint_path` | Chemin de la sauvegarde (`None` = `<output_dir>/.pipeline_checkpoint.json`) | `None` |
| `retry_errors` | Retente automatiquement au run suivant les fichiers qui avaient échoué | `True` |
| `parallel_workers` | Nombre de PDF traités en parallèle (1 = séquentiel) ; augmentez une fois les réglages validés | `1` |

Vous pouvez soit modifier `config.py` directement (avant de le "déplier" via
`modules.ipynb`, ou après), soit surcharger ponctuellement ces valeurs dans
la section 3 de `pipeline.ipynb` sans toucher au fichier.

---

## 6. Gros volumes : reprise et parallélisation

- **Le pipeline plante au milieu d'un gros lot** : relancez simplement la
  même cellule/commande. Grâce à `enable_checkpoint = True` (par défaut),
  les PDF déjà traités avec succès sont automatiquement ignorés ; seuls les
  fichiers restants (et ceux qui avaient échoué) sont retraités.
- **Accélérer sur beaucoup de PDF** : `settings["parallel_workers"] = N`
  (ex: `os.cpu_count() - 1`) traite N fichiers simultanément. Restez en
  séquentiel (`N=1`) tant que vous validez vos réglages sur de vrais
  documents, puis augmentez une fois satisfait. Ne fonctionne pas avec
  `use_zero_shot=True` (retombe automatiquement en séquentiel).
- **Un fichier corrigé après une erreur n'est pas repris** : vérifiez que
  `retry_errors = True` (par défaut) — sinon, supprimez son entrée dans
  `<output_dir>/.pipeline_checkpoint.json` ou repartez avec un
  `output_dir` vide.

## 7. Dépannage

- **`ModuleNotFoundError` dans `pipeline.ipynb`** : vous n'avez pas exécuté
  `modules.ipynb` au préalable, ou les deux notebooks ne sont pas dans le même
  dossier.
- **Le mode hybride "loupe" des pages ou en garde des mauvaises** : c'est
  souvent le signe que l'extraction native de vos PDF renvoie du texte
  corrompu (problème d'encodage de police) que le pipeline croit fiable à
  tort. Deux solutions : baissez `native_min_valid_char_ratio` (ex. 0.7)
  pour être plus strict sur ce qui est jugé "fiable", ou passez carrément
  `settings["extraction_mode"] = "ocr_only"` pour forcer l'OCR sur toutes
  les pages (plus lent, mais évite ce problème).
- **Des pages d'un même bilan/compte de résultat sont ratées** (le titre
  n'est que sur la première page) : vérifiez que
  `enable_continuation_detection = True` (par défaut). Si des pages de
  continuation manquent encore, baissez `continuation_threshold`.
- **Un mot-clé n'est pas détecté à cause d'une erreur d'OCR** (mot coupé en
  fin de ligne, caractère parasite entre deux mots) : ces cas sont déjà
  gérés automatiquement (fusion des mots coupés par un tiret + `fuzzy_word_presence`).
  Si un cas persiste, consultez l'onglet "Détail_pages" du rapport Excel
  (colonne "À vérifier") pour repérer la page concernée, et envisagez
  d'augmenter `ocr_dpi` ou de forcer `extraction_mode = "ocr_only"`.
- **Pages scannées mal détectées / texte OCR de mauvaise qualité** :
  augmentez `ocr_dpi` (ex. 400) dans les settings, essayez `ocr_psm = 6` ou
  `4`, ou vérifiez que `tesseract-ocr-fra` est bien installé pour les
  documents en français.
- **Trop de pages gardées / pas assez** : ajustez `confirmation_threshold`
  (exigence après mot-clé), `numeric_density_threshold` /
  `numeric_min_digit_count` (exigence de richesse numérique), ou
  ajoutez/retirez des mots-clés dans `config.py`.
- **`ZeroShotScorer` lève une `ImportError`** : installez `transformers` et
  `torch`, ou laissez `use_zero_shot = False`.
