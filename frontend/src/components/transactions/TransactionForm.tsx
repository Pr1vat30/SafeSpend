"use client";

import { useState, type FormEvent } from "react";

import type {
  Category,
  Transaction,
  TransactionInput,
  TransactionType,
} from "@/services/transaction-service";

import { categoryFitsType, parseAmount, todayIso, TYPE_LABELS } from "./format";
import styles from "./transactions.module.css";

interface TransactionFormProps {
  categories: Category[];
  /** When set, the form edits this transaction; otherwise it creates a new one. */
  transaction?: Transaction | null;
  submitting: boolean;
  serverError: string | null;
  onSubmit: (input: TransactionInput) => void;
  onCancel: () => void;
}

export function TransactionForm({
  categories,
  transaction = null,
  submitting,
  serverError,
  onSubmit,
  onCancel,
}: TransactionFormProps) {
  const [today] = useState(todayIso);
  const [type, setType] = useState<TransactionType>(
    transaction?.type === "income" ? "income" : "expense",
  );
  const [amount, setAmount] = useState(transaction?.amount ?? "");
  const [date, setDate] = useState(transaction?.transaction_date ?? today);
  const [categoryId, setCategoryId] = useState<number | "">(transaction?.id_category ?? "");
  const [description, setDescription] = useState(transaction?.description ?? "");
  const [error, setError] = useState<string | null>(null);

  const available = categories.filter((c) => categoryFitsType(c.type, type));

  function changeType(next: TransactionType) {
    setType(next);
    const current = categories.find((c) => c.id_category === categoryId);
    if (current && !categoryFitsType(current.type, next)) setCategoryId("");
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const parsed = parseAmount(amount);
    if (parsed === null) {
      setError("Inserisci un importo maggiore di zero, con al massimo due decimali");
      return;
    }
    if (!date) {
      setError("La data è obbligatoria");
      return;
    }
    if (date > todayIso()) {
      setError("La data non può essere futura");
      return;
    }
    if (categoryId === "") {
      setError("Seleziona una categoria");
      return;
    }
    if (description.length > 140) {
      setError("La descrizione può contenere al massimo 140 caratteri");
      return;
    }
    setError(null);
    onSubmit({
      type,
      amount: parsed,
      transaction_date: date,
      id_category: categoryId,
      description: description.trim() === "" ? null : description.trim(),
    });
  }

  return (
    <form className={styles.panel} onSubmit={handleSubmit} noValidate>
      <h2>{transaction ? "Modifica transazione" : "Nuova transazione"}</h2>
      <div className={styles.fields}>
        <label className={styles.field}>
          Tipologia
          <select value={type} onChange={(e) => changeType(e.target.value as TransactionType)}>
            <option value="expense">{TYPE_LABELS.expense}</option>
            <option value="income">{TYPE_LABELS.income}</option>
          </select>
        </label>
        <label className={styles.field}>
          Importo (€)
          <input
            type="text"
            inputMode="decimal"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0,00"
          />
        </label>
        <label className={styles.field}>
          Data
          <input type="date" value={date} max={today} onChange={(e) => setDate(e.target.value)} />
        </label>
        <label className={styles.field}>
          Categoria
          <select
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value === "" ? "" : Number(e.target.value))}
          >
            <option value="">Seleziona…</option>
            {available.map((category) => (
              <option key={category.id_category} value={category.id_category}>
                {category.name}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          Descrizione (facoltativa)
          <input
            type="text"
            value={description}
            maxLength={140}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
      </div>
      {(error ?? serverError) && <p className={styles.error}>{error ?? serverError}</p>}
      <div className={styles.actions}>
        <button type="submit" className={styles.button} disabled={submitting}>
          {transaction ? "Salva modifiche" : "Aggiungi"}
        </button>
        <button
          type="button"
          className={`${styles.button} ${styles.secondary}`}
          onClick={onCancel}
          disabled={submitting}
        >
          Annulla
        </button>
      </div>
    </form>
  );
}
