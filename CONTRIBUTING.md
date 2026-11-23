# Guida al flusso di lavoro di SafeSpend

Questa guida spiega come il team sviluppa SafeSpend su GitHub: come si creano i branch, come si apre una
pull request, cosa fa la CI (GitHub Actions) e cosa fare quando qualcosa fallisce. Le regole sono quelle del
Configuration Management Plan (`docx/Planning & Monitoring/2_ConfigurationManagementPlan/C13_CMP.docx`,
§3.3).

> **In una riga:** `main` funziona sempre. Ognuno lavora sul proprio branch, apre una pull request verso
> `main`, la CI controlla il codice, un PM approva e un PM fa il merge.

---

## Indice

1. [Il modello: GitHub Flow](#1-il-modello-github-flow)
2. [Prima di iniziare (una volta sola)](#2-prima-di-iniziare-una-volta-sola)
3. [Requisiti, issue e branch](#3-requisiti-issue-e-branch)
4. [Lavorare sul proprio branch](#4-lavorare-sul-proprio-branch)
5. [File condivisi: regole per evitare conflitti](#5-file-condivisi-regole-per-evitare-conflitti)
6. [Controlli da eseguire in locale](#6-controlli-da-eseguire-in-locale)
7. [La pull request](#7-la-pull-request)
8. [GitHub Actions: come funziona la CI](#8-github-actions-come-funziona-la-ci)
9. [Quando la CI fallisce](#9-quando-la-ci-fallisce)
10. [Test end-to-end con Playwright](#10-test-end-to-end-con-playwright)
11. [CODEOWNERS e revisioni obbligatorie](#11-codeowners-e-revisioni-obbligatorie)
12. [Configurazione di GitHub (a cura dei PM)](#12-configurazione-di-github-a-cura-dei-pm)
13. [Feature freeze, milestone e tag](#13-feature-freeze-milestone-e-tag)
14. [Promemoria dei comandi](#14-promemoria-dei-comandi)
15. [Domande frequenti](#15-domande-frequenti)

---

## 1. Il modello: GitHub Flow

```
main     ──●─────────────●───────────────●────────────●──▶   (sempre funzionante)
            \           ↑ squash merge    \           ↑
             \          │                  \          │
feature/al-…  ●──●──●───┘ (PR + CI + review) ●──●──●──┘
```

- `main` è il ramo ufficiale: contiene solo codice revisionato che ha superato la CI.
- Nessuno scrive direttamente su `main`, nemmeno i PM: ogni modifica passa da una **pull request (PR)**.
- Ogni Team Member lavora su un **branch** dedicato all'insieme di requisiti che gli è assegnato.
- Quando la PR è approvata e la CI è verde, un PM fa lo **squash merge**: tutti i commit del branch
  diventano un solo commit su `main`, e il branch viene cancellato.

Perché funziona bene con la nostra struttura: il backend è organizzato per modulo in ogni strato
(`api/controller/<modulo>`, `service/<modulo>`, `dao/<modulo>`, `models/<modulo>`, `api/dto/<modulo>`) e il
frontend ha un file per modulo in `src/services/`. Se ognuno lavora sul proprio modulo, i branch toccano
cartelle diverse e i conflitti sono rari.

---

## 2. Prima di iniziare (una volta sola)

### Prerequisiti

| Strumento | Versione | A cosa serve |
|---|---|---|
| Git | recente | versionamento |
| Docker Desktop | recente | avviare tutto con `docker compose up` |
| uv | 0.5 o successiva | ambiente Python del backend |
| Python | 3.12 | lo installa uv se manca |
| Node.js | 22 (come nel Dockerfile e nella CI) | frontend |

### Clonare e preparare il progetto

```bash
git clone https://github.com/alphi0m/SafeSpend.git
cd SafeSpend
```

```bash
cd backend && uv sync && cd ..
```

```bash
cd frontend && npm ci && cd ..
```

Le istruzioni complete di avvio sono nel [README](README.md).

### Due sistemazioni da fare su `main` prima di aprire i branch

Le fanno i PM, una volta sola, con una PR `chore/`:

1. **Aggiungere `frontend/` al repository.** Oggi la cartella esiste in locale ma non è ancora su GitHub.
2. **Togliere `.idea/` dal repository.** I file di IntelliJ cambiano su ogni computer e causano conflitti:

   ```bash
   git rm -r --cached .idea
   ```

   e aggiungere `.idea/` al `.gitignore`.

---

## 3. Requisiti, issue e branch

### Assegnazione dei requisiti

Ogni Team Member ha un insieme di requisiti del RAD, che corrisponde a uno o più moduli dell'SDD, e ne sviluppa
backend e frontend (assegnazione del piano finale del 23/11/2026, C13_CMP §3.3):

| Team Member | Modulo (SDD) | Requisiti |
|---|---|---|
| Antonio Lignelli (AL) | profile (SS1), simulation (SS6) | RF_AUT_1–5, RF_CF_3; RF_PRE_2 |
| Francesco Frascogna (FF) | transaction (SS3), riconciliazione (SS2) | RF_TRA_1–6; RF_SAL_1–2 |
| Lucadomenico Chiappetta (LC) | transaction (SS3: ricorrenze e movimenti pianificati), scheduler, alert (SS9) | RF_CF_2, RF_CF_6, RNF_AF_6; RF_CG_3 |
| Luigi Talevi (LT) | cashflow (SS2), dashboard (SS9) | RF_CF_1, RF_CF_4–5, RF_PRE_1, RF_PRE_4, RF_CG_2 |
| Antonio Vuolo (AV) | simulation (SS6: alternative), goal (SS5), achievement (SS4) | RF_PRE_3; RF_OBI_1–2, RF_PRE_6 |
| Daniele Sorgente (DS) | assistant (SS7), calendario (SS9) | RF_PRE_5; RF_CG_1 |

### Una issue per requisito

Ogni requisito (o piccolo gruppo di requisiti) ha una **issue** su GitHub con:

- titolo con l'ID del requisito, ad esempio `RF_PRE_2 – Simulazione di spesa (What-if)`;
- etichetta del modulo (`simulation`, `cashflow`, …);
- assegnatario e milestone (`M1` per il 27/11/2026, `M2` per il 09/12/2026).

Le issue e le schede di Trello seguono il piano finale del 23/11/2026 (task P0–P5 e di gestione, ID come `B-05`).

### Nomi dei branch

Formato: `tipo/<acronimo>-<modulo>-<requisiti>`, tutto in minuscolo, con trattini.

| Tipo | Quando si usa | Esempio |
|---|---|---|
| `feature/` | nuovi requisiti di un modulo | `feature/al-simulation-rf-pre-2-4` |
| `fix/` | correzione di un difetto | `fix/ff-transaction-importo-negativo` |
| `docs/` | documentazione nel repository | `docs/readme-installazione` |
| `chore/` | file condivisi: schema, dipendenze comuni, Docker, CI | `chore/schema-idempotente` |

**Un insieme grande va diviso.** Meglio tre PR da un requisito ciascuna che una PR enorme: si revisiona
prima, si integra prima e i conflitti restano piccoli. Indicativamente, una PR non dovrebbe superare le
400 righe modificate.

---

## 4. Lavorare sul proprio branch

### Creare il branch

```bash
git switch main
```

```bash
git pull
```

```bash
git switch -c feature/al-simulation-rf-pre-2
```

### Creare un modulo nuovo

Ogni strato del backend ha un pacchetto `template/` da copiare (vedi il README, sezione *Adding a module*):

1. copia `template/` in `<modulo>/` in `api/controller`, `api/dto`, `service`, `dao`, `models`;
2. rinomina file e classi;
3. mappa nel modello la tabella definita in `database/schema.sql`;
4. aggiungi una riga in `app/models/__init__.py` e una in `app/api/router.py` (vedi [§5](#5-file-condivisi-regole-per-evitare-conflitti));
5. nel frontend copia `src/services/template-service.ts` in `src/services/<modulo>-service.ts` e aggiungi le
   pagine in `src/app/<rotta>/page.tsx`.

### Commit piccoli e chiari

Usiamo **Conventional Commits**: `tipo(modulo): descrizione (requisito)`.

```text
feat(simulation): calcolo dello scenario in memoria (RF_PRE_2)
fix(cashflow): saldo minimo sbagliato con orizzonte di 90 giorni (RF_CF_1)
test(simulation): casi di test Category Partition per la data della spesa
docs(readme): istruzioni per il seed di esempio
chore(deps): aggiunta di python-multipart per l'upload OCR
```

Tipi più usati: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`.

### Restare allineati a `main`

Almeno **una volta al giorno** porta nel tuo branch le novità di `main`:

```bash
git fetch origin
```

```bash
git merge origin/main
```

Usiamo `merge` e non `rebase` perché non richiede mai `git push --force`: è più semplice e non rischia di
cancellare il lavoro già pubblicato. Tanto, con lo squash merge, la storia di `main` resta pulita.

### Risolvere un conflitto

1. `git merge origin/main` segnala i file in conflitto.
2. Apri ogni file, cerca i marcatori `<<<<<<<`, `=======`, `>>>>>>>` e tieni la versione corretta
   (spesso entrambe le righe, ad esempio in `router.py`).
3. Esegui di nuovo i controlli locali ([§6](#6-controlli-da-eseguire-in-locale)).
4. Concludi:

   ```bash
   git add <file>
   ```

   ```bash
   git commit
   ```

Per i lock file (`uv.lock`, `package-lock.json`) **non** risolvere a mano: rigenerali (vedi §5).

---

## 5. File condivisi: regole per evitare conflitti

Pochi file sono usati da tutti i moduli. Per questi valgono regole precise:

| File o cartella | Regola |
|---|---|
| `database/schema.sql` | Contiene già **tutte** le 11 tabelle del dizionario dei dati dell'SDD (PR #1–#6 del branch `database_sql`). Ogni modifica va fatta nella parte del proprio modulo, con una PR revisionata dai PM. Lo script deve essere idempotente e non deve cancellare dati, perché `db-init` lo riapplica a ogni `docker compose up`: niente `DROP TABLE`, ma `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, ecc. La CI lo applica due volte e fallisce se la seconda volta le tabelle vengono ricreate. |
| `backend/app/api/router.py`, `backend/app/models/__init__.py` | Solo **una riga per modulo**, in ordine alfabetico. Così due PR che aggiungono moduli diversi toccano righe diverse. |
| `backend/app/core/`, `config/`, `constants/`, `api/dto/common/`, `main.py` | Solo in PR `chore/` approvate dai PM. |
| `frontend/src/lib/`, `src/types/`, `src/app/layout.tsx`, `globals.css` | Solo in PR `chore/` approvate dai PM. |
| `backend/pyproject.toml` + `uv.lock` | Aggiungi dipendenze con `uv add <pacchetto>` (dev: `uv add --dev`) e committa **entrambi** i file nella stessa PR. In caso di conflitto su `uv.lock`: tieni la versione di `main` e lancia `uv lock`. |
| `frontend/package.json` + `package-lock.json` | Aggiungi con `npm install <pacchetto>` e committa entrambi. In caso di conflitto sul lock: tieni la versione di `main` e lancia `npm install`. |
| `docker-compose.yml`, `Dockerfile`, `.github/` | Solo in PR `chore/` approvate dai PM. |

Ogni PR verso `main` richiede comunque l'approvazione di un PM, che controlla anche queste regole (vedi
[§11](#11-codeowners-e-revisioni-obbligatorie)).

---

## 6. Controlli da eseguire in locale

Sono gli stessi che esegue la CI. Lanciarli prima del push fa risparmiare tempo a tutti.

**Backend** (dalla cartella `backend/`):

```bash
uv run ruff check .
```

```bash
uv run ruff format --check .
```

```bash
uv run pytest
```

Per correggere automaticamente formattazione e gran parte degli errori di lint:

```bash
uv run ruff format . && uv run ruff check --fix .
```

**Frontend** (dalla cartella `frontend/`):

```bash
npm run lint
```

```bash
npm run typecheck
```

```bash
npm run build
```

**Tutto insieme**, come in produzione (dalla radice), con i dati che hai già nel database locale:

```bash
docker compose up --build
```

I dati restano nel volume `safespend_pgdata` anche dopo `docker compose down` e vengono ricaricati al
riavvio; solo `docker compose down -v` li cancella.

---

## 7. La pull request

### Aprirla presto, in bozza

Appena hai il primo commit, pubblica il branch e apri una **draft pull request** verso `main`:

```bash
git push -u origin feature/al-simulation-rf-pre-2
```

Su GitHub: *Compare & pull request* → *Create draft pull request*. Una PR in bozza:

- fa partire la CI a ogni push, così vedi subito se qualcosa non va;
- mostra agli altri su cosa stai lavorando;
- non può essere unita finché non la segni come pronta.

### Compilare il template

Il testo della PR parte già dal [template](.github/pull_request_template.md). Compila:

- la descrizione e `Closes #<numero issue>` (la issue si chiude da sola al merge);
- i requisiti coperti;
- le caselle dei controlli eseguiti e dei test;
- uno screenshot se hai toccato l'interfaccia.

### Revisione e merge

1. Quando i requisiti sono completi e la CI è verde: **Ready for review**.
2. Serve **l'approvazione di un PM** (`@alphi0m` o `@Pr1vat30`), per ogni PR. GitHub la chiede in automatico
   tramite CODEOWNERS. Anche gli altri Team Member possono revisionare e commentare, ma la loro approvazione
   da sola non basta per il merge. Una PR aperta da un PM va approvata dall'altro PM.
3. Il revisore lascia commenti; tu rispondi, correggi e fai push sullo stesso branch. Ogni nuovo push
   **annulla le approvazioni precedenti** e rilancia la CI.
4. Tutte le discussioni devono essere risolte (*Resolve conversation*).
5. Il branch deve essere aggiornato rispetto a `main`: se GitHub mostra *This branch is out-of-date*, usa
   *Update branch* o fai `git merge origin/main` in locale.
6. Un PM clicca **Squash and merge**. Il branch viene cancellato automaticamente.

Dopo il merge, in locale:

```bash
git switch main && git pull
```

```bash
git branch -d feature/al-simulation-rf-pre-2
```

### Come fare una buona revisione

- Il codice rispetta gli strati (controller senza logica, service con la logica, DAO solo query)?
- Ci sono test per i requisiti dichiarati, con i valori attesi degli scenari del RAD?
- Le simulazioni non scrivono sul database (RNF_AF_1)? Gli importi usano `Decimal` (RNF_IM_2)?
- Nessun segreto nel codice (chiavi API, password): solo in `.env`, mai committato (RNF_SE_4).

---

## 8. GitHub Actions: come funziona la CI

### Cos'è

GitHub Actions è il servizio di GitHub che esegue automaticamente dei comandi su macchine virtuali
(*runner*) quando succede qualcosa nel repository. Le istruzioni sono nei file YAML in
`.github/workflows/`. Il nostro è [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

Vocabolario minimo:

| Termine | Significato |
|---|---|
| **workflow** | il file `ci.yml`: un insieme di job che parte in risposta a un evento |
| **evento** (`on:`) | cosa fa partire il workflow (una PR, un push…) |
| **job** | un gruppo di passi eseguito su una macchina virtuale nuova (Ubuntu) |
| **step** | un singolo comando o una *action* riusabile (es. `actions/checkout`) |
| **service** | un container di supporto avviato accanto al job (per noi PostgreSQL 18) |
| **check** | l'esito di un job, mostrato nella PR con ✓ verde o ✗ rossa |

### Quando parte

```yaml
on:
  pull_request:
    branches: [main]   # a ogni PR verso main, e a ogni nuovo push sul branch della PR
  push:
    branches: [main]   # dopo ogni merge su main
  workflow_dispatch:   # a mano, dalla scheda Actions → CI → Run workflow
```

Se fai due push di fila sulla stessa PR, la prima esecuzione viene annullata e resta solo l'ultima
(`concurrency` con `cancel-in-progress`): non si spreca tempo su codice già superato.

### I job, uno per uno

```
                ┌──────────┐
                │ changes  │  rileva quali cartelle sono cambiate
                └────┬─────┘
   ┌─────────┬───────┼─────────┬──────────┬────────┐
   ▼         ▼       ▼         ▼          ▼        │
backend  frontend database  docker      e2e       │   (partono solo se servono)
   └─────────┴───────┴─────────┴──────────┘        │
                     ▼                             │
                 ┌───────┐                         │
                 │ ci-ok │ ◀───────────────────────┘  riassume l'esito: è il controllo obbligatorio
                 └───────┘
```

| Job | Parte se cambiano… | Cosa fa | Durata indicativa |
|---|---|---|---|
| `changes` | sempre | usa l'action `dorny/paths-filter` per capire quali aree sono state modificate | pochi secondi |
| `backend` | `backend/`, `database/`, `ci.yml` | avvia PostgreSQL 18, applica `schema.sql`, `uv sync --frozen`, `ruff check`, `ruff format --check`, `pytest` | 1–2 min |
| `frontend` | `frontend/`, `ci.yml` | Node 22, `npm ci`, `npm run lint`, `npm run typecheck`, `npm run build` | 2–3 min |
| `database` | `database/schema.sql`, `ci.yml` | applica `schema.sql` **due volte** a un PostgreSQL 18 vuoto: la prima verifica che sia valido, la seconda che sia idempotente e che non ricrei le tabelle, cioè che non cancelli i dati (come succederebbe con `db-init` a ogni avvio) | < 1 min |
| `docker` | `docker-compose.yml`, `Dockerfile`, `.dockerignore`, `database/`, `ci.yml` | `docker compose build`, `docker compose up --wait` (aspetta i controlli di salute), verifica `GET /api/v1/health`, poi `docker compose down -v`; in caso di errore stampa i log dei container | 3–5 min |
| `e2e` | ogni PR | se esiste `frontend/playwright.config.ts`: avvia l'applicazione con Docker Compose ed esegue i test Playwright; altrimenti si salta (vedi [§10](#10-test-end-to-end-con-playwright)) | 4–8 min |
| `ci-ok` | sempre, alla fine | fallisce se almeno uno dei job avviati è fallito o è stato annullato; i job saltati non contano | pochi secondi |

### Perché un solo controllo obbligatorio (`ci-ok`)

Se rendessimo obbligatori tutti i job, una PR che tocca solo il frontend resterebbe bloccata per sempre:
il job `backend` non parte (non serve) e GitHub lo aspetterebbe all'infinito. `ci-ok` invece parte sempre,
guarda gli esiti dei job avviati e risponde con un solo ✓ o ✗. Nella protezione di `main` basta quindi
richiedere **`ci-ok`**.

### Cache

`setup-uv` e `setup-node` salvano le dipendenze scaricate tra un'esecuzione e l'altra (chiave: `uv.lock` e
`package-lock.json`). Finché i lock file non cambiano, l'installazione è molto più veloce.

### Leggere i risultati

1. Nella PR, in fondo, c'è il riquadro dei check: ogni job con ✓, ✗ o *skipped*.
2. Clic su **Details** accanto a un job → si apre il log, diviso per step.
3. Lo step fallito è segnato con ✗: espandilo e leggi le ultime righe, di solito l'errore è lì.
4. Per rilanciare un job fallito per motivi esterni (rete, registro Docker): **Re-run failed jobs** in alto
   a destra nella pagina del workflow.

Lo stesso elenco è nella scheda **Actions** del repository, con lo storico di tutte le esecuzioni.

---

## 9. Quando la CI fallisce

| Job / step | Messaggio tipico | Cosa fare |
|---|---|---|
| backend → ruff format | `Would reformat: app/…` | `uv run ruff format .` e committa |
| backend → ruff check | `F401 imported but unused`, `I001 import block is un-sorted` | `uv run ruff check --fix .`; il resto a mano |
| backend → pytest | `FAILED tests/…::test_…` | lancia `uv run pytest -x -vv` in locale e correggi il codice o il test |
| backend → uv sync | `The lockfile … needs to be updated` | hai cambiato `pyproject.toml` senza aggiornare il lock: `uv lock` e committa `uv.lock` |
| backend → applica lo schema | `ERROR: syntax error at or near …` | errore SQL in `schema.sql`: correggilo e provalo con `docker compose up` |
| database → riapplica | `ERROR: relation … already exists` | lo schema non è idempotente: usa `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, ecc. |
| database → riapplica | `Riapplicando lo schema le tabelle vengono cancellate e ricreate…` | lo schema contiene `DROP TABLE`: a ogni `docker compose up` cancellerebbe i dati. Togli i `DROP` e usa `CREATE … IF NOT EXISTS` |
| frontend → npm ci | `package.json and package-lock.json are not in sync` | `npm install` in locale e committa `package-lock.json` |
| frontend → lint | errori ESLint | `npm run lint` in locale; molti si correggono con `npx eslint . --fix` |
| frontend → typecheck | `TS2322: Type … is not assignable…` | correggi i tipi; `npm run typecheck` in locale |
| frontend → build | errore di build di Next.js | `npm run build` in locale per vedere lo stesso errore |
| docker → up --wait | `container … is unhealthy` | apri lo step *Log dei container*: di solito il backend non si avvia per un import mancante o una variabile d'ambiente |
| e2e | test Playwright falliti | scarica l'artifact `playwright-report` dalla pagina del workflow e aprilo con `npx playwright show-report` |
| ci-ok | `Almeno un job è fallito…` | non è un errore a sé: guarda quale job sopra è rosso |

---

## 10. Test end-to-end con Playwright

Il job `e2e` è già pronto ma resta **saltato** finché la suite non esiste. Per attivarlo (task 4.5 della WBS,
06–07/12/2026, coordinato da Antonio Vuolo; la configurazione può arrivare prima, con la base del frontend) basta aggiungere Playwright al frontend, senza cambiare la struttura:

```bash
cd frontend && npm init playwright@latest
```

Rispondi: TypeScript, cartella dei test `e2e`, niente workflow GitHub (lo abbiamo già). Poi in
`playwright.config.ts` usa l'indirizzo passato dalla CI:

```ts
use: { baseURL: process.env.BASE_URL ?? "http://localhost:3000" },
```

Da quel momento ogni PR esegue i test end-to-end sui flussi principali dei 6 casi d'uso (RNF_OP_1). I test
vanno scritti in `frontend/e2e/`, uno o più file per caso d'uso. Aggiungi anche `playwright-report/` e
`test-results/` al `frontend/.gitignore`.

---

## 11. CODEOWNERS e revisioni obbligatorie

[`.github/CODEOWNERS`](.github/CODEOWNERS) assegna **tutti i file** del repository ai Project Manager con
un'unica regola, `*  @alphi0m @Pr1vat30`. Con *Require review from Code Owners* attiva su `main`:

- ogni PR verso `main`, qualunque file tocchi, richiede l'approvazione di un PM;
- all'apertura della PR GitHub aggiunge in automatico i due PM tra i revisori;
- basta l'approvazione di uno dei due, `@alphi0m` (Alfio Marra) o `@Pr1vat30` (Salvatore Nocera);
- l'autore non può approvare la propria PR: una PR aperta da un PM va approvata dall'altro PM;
- l'approvazione di un Team Member resta utile come revisione, ma non sblocca il merge.

Formato di una riga: `percorso  @username`. L'ultima regola che corrisponde a un file vince. I PM devono
avere almeno il permesso *Write* sul repository, altrimenti GitHub ignora la regola.

---

## 12. Configurazione di GitHub (a cura dei PM)

Queste impostazioni non stanno nei file del repository: si attivano una volta dalla pagina di GitHub e
servono un account con permessi di amministratore.

### Impostazioni generali

*Settings → General → Pull Requests*:

- attiva **Allow squash merging**; disattiva *Allow merge commits* e *Allow rebase merging*;
- attiva **Always suggest updating pull request branches**;
- attiva **Automatically delete head branches**.

### Protezione di `main`

*Settings → Rules → Rulesets → New branch ruleset*:

- **Name:** `protezione-main`; **Enforcement status:** Active;
- **Target branches:** *Include default branch*;
- **Bypass list:** vuota (le regole valgono anche per i PM);
- attiva:
  - **Restrict deletions**;
  - **Block force pushes**;
  - **Require a pull request before merging**, con *Required approvals* = 1, *Dismiss stale pull request
    approvals when new commits are pushed*, *Require review from Code Owners* (è questa a rendere
    obbligatoria l'approvazione di un PM), *Require approval of the most recent reviewable push*,
    *Require conversation resolution before merging*, e come metodo di merge consentito solo *Squash*;
  - **Require status checks to pass**, con *Require branches to be up to date before merging*, e come
    check obbligatorio **`ci-ok`** (compare nell'elenco dopo la prima esecuzione della CI).

### Permessi di Actions

*Settings → Actions → General*: *Allow all actions and reusable workflows* (o almeno quelle di GitHub e di
`astral-sh` e `dorny`); *Workflow permissions*: *Read repository contents*.

---

## 13. Feature freeze, milestone e tag

| Data | Evento | Cosa cambia |
|---|---|---|
| 27/11/2026 | Milestone 1: RAD v1.1, SDD v1.0 e backend core in `main` | i PM creano il tag `v0.1.0` sul commit di `main` |
| 29/11/2026 | Feature freeze del backend | sul backend sono accettate solo PR `fix/` e `docs/` |
| 30/11/2026 | ODD v1.0 | l'ODD, scritto dal 26/11 in parallelo al backend, è approvato |
| 07/12/2026 | Feature freeze del frontend | su tutto il repository sono accettate solo PR `fix/` e `docs/` |
| 09/12/2026 | Milestone 2, consegna | i PM creano il tag `v1.0.0` |

Creare un tag (PM, dalla radice del repository aggiornato):

```bash
git switch main && git pull
```

```bash
git tag -a v1.0.0 -m "Consegna finale SafeSpend"
```

```bash
git push origin v1.0.0
```

---

## 14. Promemoria dei comandi

| Cosa | Comando |
|---|---|
| Nuovo branch | `git switch main && git pull && git switch -c feature/<acr>-<modulo>-<rf>` |
| Stato | `git status` |
| Commit | `git add <file> && git commit -m "feat(modulo): descrizione (RF_XX_N)"` |
| Allinearsi a main | `git fetch origin && git merge origin/main` |
| Pubblicare | `git push` (la prima volta `git push -u origin <branch>`) |
| Controlli backend | `uv run ruff check . && uv run ruff format --check . && uv run pytest` |
| Correzioni automatiche backend | `uv run ruff format . && uv run ruff check --fix .` |
| Controlli frontend | `npm run lint && npm run typecheck && npm run build` |
| Avviare tutto | `docker compose up --build` |
| Dopo il merge | `git switch main && git pull && git branch -d <branch>` |

---

## 15. Domande frequenti

**Ho fatto commit su `main` in locale per sbaglio.** Non fare push (sarebbe comunque rifiutato). Sposta i
commit su un branch: `git switch -c feature/<…>`, poi riporta `main` allo stato del remoto con
`git switch main && git reset --hard origin/main`. Controlla prima con `git log` di non perdere nulla.

**Il mio lavoro dipende da un modulo di un collega non ancora unito.** Meglio aspettare il suo merge e
poi fare `git merge origin/main`. Se è urgente, mettetevi d'accordo e fai partire il tuo branch dal suo; la
tua PR si unisce dopo la sua.

**Posso unire io la mia PR?** No: il merge lo fa un PM, dopo l'approvazione di un PM (l'altro PM, se la
PR è di un PM).

**La CI è verde in locale ma rossa su GitHub.** Controlla di aver committato tutti i file (soprattutto i
lock file e i file nuovi: `git status`) e che `main` sia integrato nel branch.

**Devo cambiare il RAD o l'SDD perché il codice si comporta diversamente.** Apri una issue con l'etichetta
`change request`: i PM valutano la modifica e aggiornano i documenti collegati (CMP, §3.3).
