"use client";

import { useState, type FormEvent } from "react";

import type { Reconciliation, ReconciliationInput } from "@/services/transaction-service";

import { formatDate, formatEuro, parseSignedAmount, todayIso } from "./format";
import styles from "./transactions.module.css";

interface ReconciliationPanelProps {
  calculatedBalance: string;
  reconciliationDate: string;
  history: Reconciliation[];
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
  submitting,
  serverError,
  statusMessage,
  onDateChange,
  onSubmit,
}: ReconciliationPanelProps) {
  const [today] = useState(todayIso);
  const [realBalance, setRealBalance] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const parsedReal = parseSignedAmount(realBalance);
  const previewDiff =
    parsedReal !== null ? Number(parsedReal) - Number(calculatedBalance) : null;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const parsed = parseSignedAmount(realBalance);
    if (parsed === null) {
      setError("Inserisci un saldo reale valido con al massimo due decimali (es. 1250,00)");
      return;
    }
    if (!reconciliationDate) {
      setError("La data di riconciliazione è obbligatoria");
      return;
    }
    if (reconciliationDate > todayIso()) {
      setError("La data non può essere futura");
      return;
    }
    if (description.length > 140) {
      setError("La descrizione può contenere al massimo 140 caratteri");
      return;
    }
    setError(null);
    onSubmit({
      real_balance: parsed,
      reconciliation_date: reconciliationDate,
      description: description.trim() === "" ? null : description.trim(),
    });
  }

  return (
    <>
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
              onChange={(e) => setRealBalance(e.target.value)}
              placeholder="0,00"
            />
          </label>
          <label className={styles.field}>
            Data riconciliazione
            <input
              type="date"
              value={reconciliationDate}
              max={today}
              onChange={(e) => onDateChange(e.target.value)}
            />
          </label>
          <label className={styles.field}>
            Nota (facoltativa)
            <input
              type="text"
              value={description}
              maxLength={140}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Es. Verifica saldo bancario"
            />
          </label>
        </div>
        {previewDiff === 0 && (
          <p className={styles.muted}>
            Il saldo reale coincide con quello calcolato: verrà registrato lo snapshot senza
            transazioni di rettifica.
          </p>
        )}
        {(error ?? serverError) && <p className={styles.error}>{error ?? serverError}</p>}
        {statusMessage && !error && !serverError && (
          <p className={styles.income}>{statusMessage}</p>
        )}
        <div className={styles.actions}>
          <button type="submit" className={styles.button} disabled={submitting}>
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
