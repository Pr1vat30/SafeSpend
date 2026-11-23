"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ConfirmDialog } from "@/components/transactions/ConfirmDialog";
import { TransactionFilters } from "@/components/transactions/TransactionFilters";
import { TransactionForm } from "@/components/transactions/TransactionForm";
import { TransactionList } from "@/components/transactions/TransactionList";
import { errorMessage, formatEuro } from "@/components/transactions/format";
import styles from "@/components/transactions/transactions.module.css";
import {
  EMPTY_FILTERS,
  transactionService,
  type Category,
  type Transaction,
  type TransactionFilters as Filters,
  type TransactionInput,
  type TransactionList as TransactionListData,
} from "@/services/transaction-service";

function hasActiveFilters(filters: Filters): boolean {
  return Boolean(filters.dateFrom || filters.dateTo || filters.type || filters.idCategory !== "");
}

export default function TransactionsPage() {
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [categories, setCategories] = useState<Category[]>([]);
  const [data, setData] = useState<TransactionListData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  // "new" = insertion form, a Transaction = edit form, null = form closed.
  const [formTarget, setFormTarget] = useState<"new" | Transaction | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [toDelete, setToDelete] = useState<Transaction | null>(null);

  useEffect(() => {
    let active = true;
    transactionService
      .listCategories()
      .then((result) => {
        if (active) setCategories(result);
      })
      .catch((e: unknown) => {
        if (active) setError(errorMessage(e));
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    transactionService
      .list(filters)
      .then((result) => {
        if (active) {
          setData(result);
          setError(null);
        }
      })
      .catch((e: unknown) => {
        if (active) setError(errorMessage(e));
      });
    return () => {
      active = false;
    };
  }, [filters, version]);

  async function handleSubmit(input: TransactionInput) {
    setSubmitting(true);
    setFormError(null);
    try {
      if (formTarget && formTarget !== "new") {
        await transactionService.update(formTarget.id_transaction, input);
      } else {
        await transactionService.create(input);
      }
      setFormTarget(null);
      setVersion((v) => v + 1);
    } catch (e) {
      setFormError(errorMessage(e));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleConfirmDelete() {
    if (!toDelete) return;
    setSubmitting(true);
    try {
      await transactionService.remove(toDelete.id_transaction);
      setToDelete(null);
      setVersion((v) => v + 1);
    } catch (e) {
      setError(errorMessage(e));
      setToDelete(null);
    } finally {
      setSubmitting(false);
    }
  }

  const filtered = hasActiveFilters(filters);
  const balance = data ? Number(data.totals.income) - Number(data.totals.expense) : 0;

  return (
    <main className={styles.page}>
      <div className={styles.header}>
        <h1>Transazioni</h1>
        <button
          type="button"
          className={styles.button}
          onClick={() => {
            setFormError(null);
            setFormTarget("new");
          }}
        >
          Nuova transazione
        </button>
      </div>
      <nav className={styles.nav}>
        <Link href="/categories">Gestisci categorie →</Link>
      </nav>

      {formTarget && (
        <TransactionForm
          key={formTarget === "new" ? "new" : formTarget.id_transaction}
          categories={categories}
          transaction={formTarget === "new" ? null : formTarget}
          submitting={submitting}
          serverError={formError}
          onSubmit={(input) => void handleSubmit(input)}
          onCancel={() => setFormTarget(null)}
        />
      )}

      <TransactionFilters
        filters={filters}
        categories={categories}
        onChange={setFilters}
        onReset={() => setFilters(EMPTY_FILTERS)}
      />

      {error && <p className={styles.error}>{error}</p>}

      {data && (
        <>
          <div className={styles.totals} aria-label="Totali">
            <div className={styles.total}>
              <span>{filtered ? "Entrate (filtri applicati)" : "Entrate"}</span>
              <strong className={styles.income}>{formatEuro(data.totals.income)}</strong>
            </div>
            <div className={styles.total}>
              <span>{filtered ? "Uscite (filtri applicati)" : "Uscite"}</span>
              <strong className={styles.expense}>{formatEuro(data.totals.expense)}</strong>
            </div>
            <div className={styles.total}>
              <span>Differenza</span>
              <strong>{formatEuro(balance)}</strong>
            </div>
          </div>
          <TransactionList
            items={data.items}
            onEdit={(transaction) => {
              setFormError(null);
              setFormTarget(transaction);
            }}
            onDelete={setToDelete}
          />
        </>
      )}
      {!data && !error && <p className={styles.muted}>Caricamento…</p>}

      {toDelete && (
        <ConfirmDialog
          title="Eliminare la transazione?"
          message="L'operazione non si può annullare: la transazione sarà rimossa e i calcoli verranno aggiornati."
          confirmLabel="Elimina"
          busy={submitting}
          onConfirm={() => void handleConfirmDelete()}
          onCancel={() => setToDelete(null)}
        />
      )}
    </main>
  );
}
