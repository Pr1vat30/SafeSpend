import type {
  Category,
  TransactionFilters as Filters,
  TransactionType,
} from "@/services/transaction-service";

import { TYPE_LABELS } from "./format";
import styles from "./transactions.module.css";

interface TransactionFiltersProps {
  filters: Filters;
  categories: Category[];
  onChange: (filters: Filters) => void;
  onReset: () => void;
}

export function TransactionFilters({
  filters,
  categories,
  onChange,
  onReset,
}: TransactionFiltersProps) {
  return (
    <div className={styles.panel}>
      <div className={styles.fields}>
        <label className={styles.field}>
          Dal
          <input
            type="date"
            value={filters.dateFrom}
            onChange={(e) => onChange({ ...filters, dateFrom: e.target.value })}
          />
        </label>
        <label className={styles.field}>
          Al
          <input
            type="date"
            value={filters.dateTo}
            onChange={(e) => onChange({ ...filters, dateTo: e.target.value })}
          />
        </label>
        <label className={styles.field}>
          Tipologia
          <select
            value={filters.type}
            onChange={(e) => onChange({ ...filters, type: e.target.value as TransactionType | "" })}
          >
            <option value="">Tutte</option>
            <option value="income">{TYPE_LABELS.income}</option>
            <option value="expense">{TYPE_LABELS.expense}</option>
          </select>
        </label>
        <label className={styles.field}>
          Categoria
          <select
            value={filters.idCategory}
            onChange={(e) =>
              onChange({
                ...filters,
                idCategory: e.target.value === "" ? "" : Number(e.target.value),
              })
            }
          >
            <option value="">Tutte</option>
            {categories.map((category) => (
              <option key={category.id_category} value={category.id_category}>
                {category.name} ({category.type === "income" ? "entrata" : "uscita"})
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className={styles.actions}>
        <button type="button" className={`${styles.button} ${styles.secondary}`} onClick={onReset}>
          Azzera filtri
        </button>
      </div>
    </div>
  );
}
