"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { CategoryManager } from "@/components/transactions/CategoryManager";
import { errorMessage } from "@/components/transactions/format";
import styles from "@/components/transactions/transactions.module.css";
import { transactionService, type Category } from "@/services/transaction-service";

export default function CategoriesPage() {
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    transactionService
      .listCategories()
      .then((result) => {
        if (active) {
          setCategories(result);
          setError(null);
        }
      })
      .catch((e: unknown) => {
        if (active) setError(errorMessage(e));
      });
    return () => {
      active = false;
    };
  }, [version]);

  return (
    <main className={styles.page}>
      <h1>Categorie</h1>
      <nav className={styles.nav}>
        <Link href="/transactions">← Transazioni</Link>
      </nav>
      {error && <p className={styles.error}>{error}</p>}
      {categories === null && !error && <p className={styles.muted}>Caricamento…</p>}
      {categories && (
        <CategoryManager categories={categories} onChanged={() => setVersion((v) => v + 1)} />
      )}
    </main>
  );
}
