"use client";

import { useState, type FormEvent } from "react";

import {
  transactionService,
  type Category,
  type CategoryType,
} from "@/services/transaction-service";

import { ConfirmDialog } from "./ConfirmDialog";
import { CATEGORY_TYPE_LABELS, errorMessage } from "./format";
import styles from "./transactions.module.css";

interface CategoryManagerProps {
  categories: Category[];
  /** Called after every successful change so the parent reloads the list. */
  onChanged: () => void;
}

export function CategoryManager({ categories, onChanged }: CategoryManagerProps) {
  const [name, setName] = useState("");
  const [type, setType] = useState<CategoryType>("expense");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState("");
  const [deleting, setDeleting] = useState<Category | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      onChanged();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (name.trim() === "") {
      setError("Il nome della categoria è obbligatorio");
      return;
    }
    void run(async () => {
      await transactionService.createCategory(name.trim(), type);
      setName("");
    });
  }

  function handleRename(category: Category) {
    if (editingName.trim() === "") {
      setError("Il nome della categoria è obbligatorio");
      return;
    }
    void run(async () => {
      await transactionService.renameCategory(category.id_category, editingName.trim());
      setEditingId(null);
    });
  }

  function handleDelete(category: Category) {
    void run(async () => {
      const result = await transactionService.removeCategory(category.id_category);
      setDeleting(null);
      setNotice(
        `Categoria eliminata. Transazioni riassegnate a «Altro»: ${result.reassigned_transactions}.`,
      );
    });
  }

  return (
    <div>
      <form className={styles.panel} onSubmit={handleCreate} noValidate>
        <h2>Nuova categoria</h2>
        <div className={styles.fields}>
          <label className={styles.field}>
            Nome
            <input type="text" value={name} maxLength={100} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className={styles.field}>
            Tipologia
            <select value={type} onChange={(e) => setType(e.target.value as CategoryType)}>
              <option value="expense">{CATEGORY_TYPE_LABELS.expense}</option>
              <option value="income">{CATEGORY_TYPE_LABELS.income}</option>
              <option value="both">{CATEGORY_TYPE_LABELS.both}</option>
            </select>
          </label>
        </div>
        <div className={styles.actions}>
          <button type="submit" className={styles.button} disabled={busy}>
            Crea categoria
          </button>
        </div>
      </form>

      {error && <p className={styles.error}>{error}</p>}
      {notice && <p className={styles.income}>{notice}</p>}

      <div className={styles.panel}>
        <ul className={styles.list}>
          {categories.map((category) => (
            <li key={category.id_category} className={styles.listItem}>
              {editingId === category.id_category ? (
                <div className={styles.inline}>
                  <input
                    type="text"
                    value={editingName}
                    maxLength={100}
                    aria-label="Nuovo nome"
                    onChange={(e) => setEditingName(e.target.value)}
                  />
                  <button
                    type="button"
                    className={styles.button}
                    disabled={busy}
                    onClick={() => handleRename(category)}
                  >
                    Salva
                  </button>
                  <button
                    type="button"
                    className={`${styles.button} ${styles.secondary}`}
                    onClick={() => setEditingId(null)}
                  >
                    Annulla
                  </button>
                </div>
              ) : (
                <>
                  <span>
                    {category.name}{" "}
                    <span className={styles.muted}>
                      · {CATEGORY_TYPE_LABELS[category.type]}
                      {category.is_default ? " · predefinita" : ""}
                    </span>
                  </span>
                  {!category.is_default && (
                    <div className={styles.inline}>
                      <button
                        type="button"
                        className={`${styles.button} ${styles.secondary}`}
                        onClick={() => {
                          setEditingId(category.id_category);
                          setEditingName(category.name);
                        }}
                      >
                        Rinomina
                      </button>
                      <button
                        type="button"
                        className={`${styles.button} ${styles.danger}`}
                        onClick={() => setDeleting(category)}
                      >
                        Elimina
                      </button>
                    </div>
                  )}
                </>
              )}
            </li>
          ))}
        </ul>
      </div>

      {deleting && (
        <ConfirmDialog
          title="Eliminare la categoria?"
          message={`Le transazioni di «${deleting.name}» non verranno cancellate: saranno spostate nella categoria «Altro».`}
          confirmLabel="Elimina categoria"
          busy={busy}
          onConfirm={() => handleDelete(deleting)}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
