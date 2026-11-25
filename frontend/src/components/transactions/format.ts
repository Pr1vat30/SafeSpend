/** Formatting and validation helpers shared by the transaction components. */

import type { CategoryType, TransactionType } from "@/services/transaction-service";

const euro = new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" });

export function formatEuro(amount: string | number): string {
  return euro.format(Number(amount));
}

export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split("-");
  return `${day}/${month}/${year}`;
}

/** Today's date as yyyy-mm-dd in the user's time zone. */
export function todayIso(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function normalizeDecimal(raw: string): string {
  return raw.trim().replace(",", ".");
}

/** Accepts "12", "12.5", "12,50": at most two decimals, strictly greater than zero. */
export function parseAmount(raw: string): string | null {
  const value = normalizeDecimal(raw);
  if (!/^\d{1,10}(\.\d{1,2})?$/.test(value)) return null;
  return Number(value) > 0 ? value : null;
}

/** Accepts signed balances ("0", "-12,50", "1250.00"): up to 10 integer digits and 2 decimals. */
export function parseSignedAmount(raw: string): string | null {
  const value = normalizeDecimal(raw);
  return /^-?\d{1,10}(\.\d{1,2})?$/.test(value) ? value : null;
}

export function categoryFitsType(categoryType: CategoryType, type: TransactionType): boolean {
  return categoryType === type || categoryType === "both";
}

export const TYPE_LABELS: Record<TransactionType, string> = {
  income: "Entrata",
  expense: "Uscita",
};

export const CATEGORY_TYPE_LABELS: Record<CategoryType, string> = {
  income: "Entrata",
  expense: "Uscita",
  both: "Entrata e uscita",
};

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Si è verificato un errore";
}
