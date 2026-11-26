"use client";

import { useState, type FormEvent } from "react";

import type { Reconciliation, ReconciliationInput } from "@/services/transaction-service";

import { formatDate, formatEuro, parseSignedAmount, todayIso } from "./format";
import styles from "./transactions.module.css";

interface ReconciliationPanelProps {
  calculatedBalance: string;
  reconciliationDate: string;
  history: Reconciliation[];
  daysSinceLast: number | null;
  reconciliationReminder: boolean;
  submitting: boolean;
  serverError: string | null;
  statusMessage: string | null;
  onDateChange: (nextDate: string) => void;
  onSubmit: (input: ReconciliationInput) => void;
}

export function ReconciliationPanel({
  calculatedBalance,
  reconciliationDate,
  history,
  daysSinceLast,
  reconciliationReminder,
  submitting,
  serverError,
  statusMessage,
  onDateChange,
  onSubmit,
}: ReconciliationPanelProps) {
  const [today] = useState(todayIso);
  const [realBalance, setRealBalance] = useState("");
  const [realBalanceTouched, setRealBalanceTouched] = useState(false);
  const [description, setDescription] = useState("");

  const parsedReal = parseSignedAmount(realBalance);
  const realBalanceError =
    realBalanceTouched && parsedReal === null
      ? "Inserisci un saldo reale valido con al massimo due decimali (es. 1250,00)"
      : null;
  const dateError = !reconciliationDate
    ? "La data di riconciliazione è obbligatoria"
    : reconciliationDate > todayIso()
      ? "La data non può essere futura"
      : null;
  const descriptionError =
    description.length > 140 ? "La descrizione può contenere al massimo 140 caratteri" : null;

  const isFormValid = parsedReal !== null && dateError === null && descriptionError === null;
  const previewDiff =
    parsedReal !== null ? Number(parsedReal) - Number(calculatedBalance) : null;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setRealBalanceTouched(true);
    if (!isFormValid || parsedReal === null) return;
    onSubmit({
      real_balance: parsedReal,
      reconciliation_date: reconciliationDate,
      description: description.trim() === "" ? null : description.trim(),
    });
  }

  return (
    <>
      {reconciliationReminder && daysSinceLast !== null && (
        <p className={styles.panel} role="status">
          L&apos;ultima riconciliazione risale a {daysSinceLast} giorni fa: conferma il saldo attuale
          per mantenere allineate le proiezioni.
        </p>
      )}

      <div className={styles.totals} aria-label="Riepilogo saldo">
        <div className={styles.total}>
          <span>Saldo calcolato al {formatDate(reconciliationDate)}</span>
          <strong>{formatEuro(calculatedBalance)}</strong>
        </div>
        {previewDiff !== null && (
          <div className={styles.total}>
            <span>Rettifica prevista</span>
            <strong className={previewDiff >= 0 ? styles.income : styles.expense}>
              {previewDiff > 0 ? "+" : ""}
              {formatEuro(previewDiff)}
            </strong>
          </div>
        )}
      </div>

      <form className={styles.panel} onSubmit={handleSubmit} noValidate>
        <h2>Nuova riconciliazione</h2>
        <div className={styles.fields}>
          <label className={styles.field}>
            Saldo reale (€)
            <input
              type="text"
              inputMode="decimal"
              value={realBalance}
              aria-invalid={realBalanceError !== null}
              onChange={(e) => {
                setRealBalance(e.target.value);
                if (!realBalanceTouched) setRealBalanceTouched(true);
              }}
              onBlur={() => setRealBalanceTouched(true)}
              placeholder="0,00"
            />
            {realBalanceError && (
              <span className={styles.error} role="alert">
                {realBalanceError}
              </span>
            )}
          </label>
          <label className={styles.field}>
            Data riconciliazione
            <input
              type="date"
              value={reconciliationDate}
              max={today}
              aria-invalid={dateError !== null}
              onChange={(e) => onDateChange(e.target.value)}
            />
            {dateError && (
              <span className={styles.error} role="alert">
                {dateError}
              </span>
            )}
          </label>
          <label className={styles.field}>
            Nota (facoltativa)
            <input
              type="text"
              value={description}
              maxLength={140}
              aria-invalid={descriptionError !== null}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Es. Verifica saldo bancario"
            />
            {descriptionError && (
              <span className={styles.error} role="alert">
                {descriptionError}
              </span>
            )}
          </label>
        </div>
        {previewDiff === 0 && (
          <p className={styles.muted}>
            Il saldo reale coincide con quello calcolato: verrà registrato lo snapshot senza
            transazioni di rettifica.
          </p>
        )}
        {serverError && (
          <p className={styles.error} role="alert">
            {serverError}
          </p>
        )}
        {statusMessage && !serverError && (
          <p className={styles.income} role="status">
            {statusMessage}
          </p>
        )}
        <div className={styles.actions}>
          <button type="submit" className={styles.button} disabled={submitting || !isFormValid}>
            Riconcilia saldo
          </button>
        </div>
      </form>

      <section className={styles.panel}>
        <h2>Storico riconciliazioni</h2>
        {history.length === 0 ? (
          <p className={styles.muted}>Nessuna riconciliazione registrata.</p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Data</th>
                  <th className={styles.amount}>Saldo calcolato</th>
                  <th className={styles.amount}>Saldo reale</th>
                  <th className={styles.amount}>Rettifica</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item) => {
                  const diff = Number(item.difference);
                  return (
                    <tr key={item.id_snapshot}>
                      <td>{formatDate(item.reconciliation_date)}</td>
                      <td className={styles.amount}>{formatEuro(item.calculated_balance)}</td>
                      <td className={styles.amount}>{formatEuro(item.real_balance)}</td>
                      <td
                        className={`${styles.amount} ${
                          diff > 0 ? styles.income : diff < 0 ? styles.expense : styles.muted
                        }`}
                      >
                        {diff > 0 ? "+" : ""}
                        {formatEuro(item.difference)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
