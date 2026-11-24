"""User-facing messages of SS1 (account and profile), in Italian (RNF_IN_2)."""

# Routes
AUTH_TAG = "Autenticazione"
AUTH_PREFIX = "/auth"
PROFILE_TAG = "Profilo"
PROFILE_PREFIX = "/profile"

# Registration (RF_AUT_1, RNF_LE_1)
EMAIL_ALREADY_REGISTERED = "Esiste già un account con questa email"
PASSWORD_TOO_WEAK = "La password deve avere almeno 8 caratteri, con almeno una lettera e una cifra"
MUST_ACCEPT_PRIVACY = "È necessario accettare l'informativa sulla privacy"
MUST_ACCEPT_DISCLAIMER = "È necessario accettare l'avviso di non consulenza finanziaria"
MUST_BE_ADULT = "SafeSpend è riservato agli utenti maggiorenni"
FIELD_REQUIRED = "Il campo è obbligatorio"
REGISTERED = "Registrazione completata"

# Login and session (RF_AUT_2, RF_AUT_3)
INVALID_CREDENTIALS = "Email o password non corretti"
ACCOUNT_LOCKED = "Troppi tentativi falliti: l'accesso è bloccato fino alle {until}"
NOT_AUTHENTICATED = "Accesso richiesto: effettua il login"
LOGGED_IN = "Accesso effettuato"
LOGGED_OUT = "Disconnessione effettuata"

# Profile (RF_AUT_4, RF_AUT_5, RF_CF_3, RNF_PV_2–3)
WRONG_PASSWORD = "Password non corretta"
ACCOUNT_DELETED = "Account e dati eliminati definitivamente"
PROFILE_UPDATED = "Profilo aggiornato"
PROFILE_NOT_FOUND = "Profilo finanziario non trovato"
SETUP_COMPLETED = "Configurazione iniziale completata"
SETUP_ALREADY_DONE = (
    "Il saldo iniziale è già stato inserito: per aggiornarlo usa la riconciliazione del saldo"
)
AMOUNT_NOT_NEGATIVE = "L'importo deve essere maggiore o uguale a zero"
AMOUNT_TWO_DECIMALS = "L'importo può avere al massimo due decimali"
HORIZON_NOT_ALLOWED = "L'orizzonte deve essere di 30, 60 o 90 giorni"
