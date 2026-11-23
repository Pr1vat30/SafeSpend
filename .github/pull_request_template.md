## Descrizione

<!-- Cosa cambia questa pull request e perché, in poche righe. -->

Closes #<!-- numero della sub-issue; una riga per ogni sub-issue chiusa, ad esempio: Closes #12, closes #13. Non indicare la issue madre. -->

## Requisiti coperti

<!-- Requisiti del RAD implementati o modificati, ad esempio RF_PRE_2, RF_PRE_4. -->

- 

## Tipo di modifica

- [ ] feature/ – nuovi requisiti di un modulo
- [ ] fix/ – correzione di un difetto
- [ ] docs/ – documentazione nel repository
- [ ] chore/ – file condivisi (schema, dipendenze, Docker, CI)

<!-- Ogni PR verso main richiede l'approvazione di un PM (@alphi0m o @Pr1vat30), assegnati in automatico. -->

## Controlli eseguiti in locale

- [ ] `uv run ruff check .`, `uv run ruff format --check .` e `uv run pytest` in `backend/`
- [ ] `npm run lint` e `npm run typecheck` in `frontend/`
- [ ] main integrato nel branch (`git fetch` e `git merge origin/main`) senza conflitti aperti

## Test

- [ ] Ho aggiunto o aggiornato i test di unità (Category Partition) per i requisiti coperti
- [ ] Ho verificato i valori attesi degli scenari del RAD, se la modifica riguarda il motore di calcolo

## Interfaccia

<!-- Screenshot o breve descrizione, se la modifica riguarda il frontend. Altrimenti scrivi "Nessuna". -->

## File condivisi e documenti

- [ ] La pull request non modifica file condivisi, oppure le modifiche sono limitate a quanto previsto dal CMP (§3.3.1)
- [ ] Se il comportamento cambia rispetto a RAD o SDD, ho aperto una change request per aggiornarli
