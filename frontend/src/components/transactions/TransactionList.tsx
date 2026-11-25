import type { Transaction } from "@/services/transaction-service";

import { formatDate, formatEuro } from "./format";
import styles from "./transactions.module.css";

interface TransactionListProps {
  items: Transaction[];
  onEdit: (transaction: Transaction) => void;
  onDelete: (transaction: Transaction) => void;
}

export function TransactionList({ items, onEdit, onDelete }: TransactionListProps) {
  if (items.length === 0) {
    return <p className={styles.muted}>Nessuna transazione trovata.</p>;
  }
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Data</th>
            <th>Categoria</th>
            <th>Descrizione</th>
            <th className={styles.amount}>Importo</th>
            <th>Azioni</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const editable = item.type === "income" || item.type === "expense";
            const amountNum = Number(item.amount);
            const positive =
              item.type === "income" || (item.type === "adjustment" && amountNum > 0);
            const sign =
              item.type === "income"
                ? "+"
                : item.type === "expense"
                  ? "−"
                  : amountNum > 0
                    ? "+"
                    : "";
            return (
              <tr key={item.id_transaction}>
                <td>{formatDate(item.transaction_date)}</td>
                <td>{item.category_name ?? "Rettifica saldo"}</td>
                <td>{item.description ?? ""}</td>
                <td className={`${styles.amount} ${positive ? styles.income : styles.expense}`}>
                  {sign}
                  {formatEuro(item.amount)}
                </td>
                <td>
                  {editable && (
                    <div className={styles.inline}>
                      <button
                        type="button"
                        className={`${styles.button} ${styles.secondary}`}
                        onClick={() => onEdit(item)}
                      >
                        Modifica
                      </button>
                      <button
                        type="button"
                        className={`${styles.button} ${styles.danger}`}
                        onClick={() => onDelete(item)}
                      >
                        Elimina
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
