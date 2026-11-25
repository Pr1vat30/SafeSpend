/**
 * Transaction service: wraps the backend endpoints of the transaction module
 * (`/transactions` and `/categories`), so components never build URLs themselves.
 */

import { apiFetch } from "@/lib/api-client";

export type TransactionType = "income" | "expense";
export type CategoryType = TransactionType | "both";

export interface Category {
  id_category: number;
  name: string;
  type: CategoryType;
  is_default: boolean;
  created_at: string;
}

/** Amounts are decimal strings (e.g. "12.50"), exactly as the backend sends them. */
export interface Transaction {
  id_transaction: number;
  type: string;
  amount: string;
  transaction_date: string;
  id_category: number | null;
  category_name: string | null;
  description: string | null;
  origin: string;
  created_at: string;
}

export interface TransactionInput {
  type: TransactionType;
  amount: string;
  transaction_date: string;
  id_category: number;
  description: string | null;
}

export interface TransactionFilters {
  dateFrom: string;
  dateTo: string;
  type: TransactionType | "";
  idCategory: number | "";
}

export interface TransactionList {
  items: Transaction[];
  totals: { income: string; expense: string };
  count: number;
}

export interface Reconciliation {
  id_snapshot: number;
  real_balance: string;
  calculated_balance: string;
  difference: string;
  reconciliation_date: string;
  id_adjustment_transaction: number | null;
  created_at: string;
}

export interface ReconciliationInput {
  real_balance: string;
  reconciliation_date: string;
  description: string | null;
}

export interface ReconciliationPreview {
  reconciliation_date: string;
  calculated_balance: string;
  last_reconciliation: Reconciliation | null;
  days_since_last_reconciliation: number | null;
  reconciliation_reminder: boolean;
}

export interface ReconciliationHistory {
  items: Reconciliation[];
  count: number;
  current_calculated_balance: string;
}

export const EMPTY_FILTERS: TransactionFilters = {
  dateFrom: "",
  dateTo: "",
  type: "",
  idCategory: "",
};

/**
 * Uses the JWT issued by the Profile module (stored in localStorage as `safespend_token`, or
 * `NEXT_PUBLIC_DEV_TOKEN` during local development before login UI is wired).
 */
function authHeaders(): Record<string, string> {
  const token =
    (typeof window !== "undefined" ? window.localStorage.getItem("safespend_token") : null) ??
    process.env.NEXT_PUBLIC_DEV_TOKEN;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function json(method: string, body: unknown): RequestInit {
  return { method, headers: authHeaders(), body: JSON.stringify(body) };
}

export const transactionService = {
  list(filters: TransactionFilters = EMPTY_FILTERS): Promise<TransactionList> {
    const params = new URLSearchParams();
    if (filters.dateFrom) params.set("date_from", filters.dateFrom);
    if (filters.dateTo) params.set("date_to", filters.dateTo);
    if (filters.type) params.set("type", filters.type);
    if (filters.idCategory !== "") params.set("id_category", String(filters.idCategory));
    const query = params.toString();
    return apiFetch<TransactionList>(`/transactions${query ? `?${query}` : ""}`, {
      headers: authHeaders(),
    });
  },

  create(input: TransactionInput): Promise<Transaction> {
    return apiFetch<Transaction>("/transactions", json("POST", input));
  },

  update(id: number, input: TransactionInput): Promise<Transaction> {
    return apiFetch<Transaction>(`/transactions/${id}`, json("PUT", input));
  },

  remove(id: number): Promise<null> {
    return apiFetch<null>(`/transactions/${id}`, { method: "DELETE", headers: authHeaders() });
  },

  listCategories(): Promise<Category[]> {
    return apiFetch<Category[]>("/categories", { headers: authHeaders() });
  },

  createCategory(name: string, type: CategoryType): Promise<Category> {
    return apiFetch<Category>("/categories", json("POST", { name, type }));
  },

  renameCategory(id: number, name: string): Promise<Category> {
    return apiFetch<Category>(`/categories/${id}`, json("PUT", { name }));
  },

  removeCategory(id: number): Promise<{ reassigned_transactions: number }> {
    return apiFetch<{ reassigned_transactions: number }>(`/categories/${id}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
  },

  previewReconciliation(reconciliationDate?: string): Promise<ReconciliationPreview> {
    const query = reconciliationDate
      ? `?reconciliation_date=${encodeURIComponent(reconciliationDate)}`
      : "";
    return apiFetch<ReconciliationPreview>(`/reconciliations/preview${query}`, {
      headers: authHeaders(),
    });
  },

  listReconciliations(): Promise<ReconciliationHistory> {
    return apiFetch<ReconciliationHistory>("/reconciliations", { headers: authHeaders() });
  },

  reconcileBalance(input: ReconciliationInput): Promise<Reconciliation> {
    return apiFetch<Reconciliation>("/reconciliations", json("POST", input));
  },
};
