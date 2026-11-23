"""User-facing messages of the transaction module."""

CATEGORY_NOT_FOUND = "Categoria non trovata"
CATEGORY_TYPE_MISMATCH = "La categoria scelta non è valida per questo tipo di transazione"
CATEGORY_DUPLICATE = "Esiste già una categoria con questo nome"
CATEGORY_DEFAULT_PROTECTED = "Le categorie predefinite non possono essere modificate o eliminate"
CATEGORY_FALLBACK_MISSING = "La categoria predefinita «Altro» non è disponibile"
CATEGORY_CREATED = "Categoria creata"
CATEGORY_RENAMED = "Categoria rinominata"
CATEGORY_DELETED = "Categoria eliminata"

TRANSACTION_NOT_FOUND = "Transazione non trovata"
TRANSACTION_NOT_EDITABLE = "Le rettifiche di saldo non possono essere modificate o eliminate qui"
TRANSACTION_CREATED = "Transazione registrata"
TRANSACTION_UPDATED = "Transazione aggiornata"
TRANSACTION_DELETED = "Transazione eliminata"
INVALID_PERIOD = "La data di inizio non può essere successiva alla data di fine"


def category_in_use(name: str, rules: int, planned: int) -> str:
    """Why a category cannot be deleted: other modules still use it."""
    parts = []
    if rules:
        label = "regola ricorrente" if rules == 1 else "regole ricorrenti"
        parts.append(f"{rules} {label}")
    if planned:
        label = "transazione pianificata" if planned == 1 else "transazioni pianificate"
        parts.append(f"{planned} {label}")
    used_by = " e da ".join(parts)
    return (
        f"La categoria «{name}» non può essere eliminata perché è usata da {used_by}. "
        "Cambia la categoria di questi elementi o rimuovili, poi riprova."
    )
