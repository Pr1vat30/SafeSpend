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

export const EMPTY_FILTERS: TransactionFilters = {
  dateFrom: "",
  dateTo: "",
  type: "",
  idCategory: "",
};

/**
 * TEMPORARY: until the authentication module is merged, the backend identifies the user through
 * the `X-User-Id` header. Set NEXT_PUBLIC_DEV_USER_ID to an existing user id (default: 1).
 * When authentication lands, replace this function and nothing else.
 */
function authHeaders(): Record<string, string> {
  return { "X-User-Id": process.env.NEXT_PUBLIC_DEV_USER_ID ?? "1" };
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
};
