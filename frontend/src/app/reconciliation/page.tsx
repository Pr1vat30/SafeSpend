"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ReconciliationPanel } from "@/components/transactions/ReconciliationPanel";
import { errorMessage, todayIso } from "@/components/transactions/format";
import styles from "@/components/transactions/transactions.module.css";
import {
  transactionService,
  type Reconciliation,
  type ReconciliationInput,
} from "@/services/transaction-service";

export default function ReconciliationPage() {
  const [reconciliationDate, setReconciliationDate] = useState(todayIso);
  const [calculatedBalance, setCalculatedBalance] = useState<string | null>(null);
  const [history, setHistory] = useState<Reconciliation[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    Promise.all([
      transactionService.previewReconciliation(reconciliationDate),
      transactionService.listReconciliations(),
    ])
      .then(([preview, hist]) => {
        if (active) {
          setCalculatedBalance(preview.calculated_balance);
          setHistory(hist.items);
          setError(null);
        }
      })
      .catch((e: unknown) => {
        if (active) setError(errorMessage(e));
      });
    return () => {
      active = false;
    };
  }, [reconciliationDate, version]);

  async function handleSubmit(input: ReconciliationInput) {
    setSubmitting(true);
    setSubmitError(null);
    setStatusMessage(null);
    try {
      const created = await transactionService.reconcileBalance(input);
      const diff = Number(created.difference);
      setStatusMessage(
        diff === 0
          ? "Saldo già allineato: snapshot registrato."
          : "Saldo riconciliato e rettifica registrata.",
      );
      // CASH FLOW: refresh balance / STS / projections here when the Cash Flow screens exist.
      setVersion((v) => v + 1);
    } catch (e) {
      setSubmitError(errorMessage(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className={styles.page}>
      <h1>Riconciliazione saldo</h1>
      <nav className={styles.nav}>
        <Link href="/transactions">← Transazioni</Link>
        <Link href="/categories">Categorie →</Link>
      </nav>
      {error && <p className={styles.error}>{error}</p>}
      {calculatedBalance !== null && history !== null ? (
        <ReconciliationPanel
          calculatedBalance={calculatedBalance}
          reconciliationDate={reconciliationDate}
          history={history}
          submitting={submitting}
          serverError={submitError}
          statusMessage={statusMessage}
          onDateChange={(nextDate) => {
            if (nextDate) setReconciliationDate(nextDate);
          }}
          onSubmit={(input) => void handleSubmit(input)}
        />
      ) : (
        !error && <p className={styles.muted}>Caricamento…</p>
      )}
    </main>
  );
}
