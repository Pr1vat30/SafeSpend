import styles from "./transactions.module.css";

interface ConfirmDialogProps {
  title: string;
  message: string;
  confirmLabel: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Explicit confirmation before a destructive action. */
export function ConfirmDialog({
  title,
  message,
  confirmLabel,
  busy = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <div className={styles.overlay}>
      <div className={styles.dialog} role="alertdialog" aria-modal="true" aria-label={title}>
        <h2>{title}</h2>
        <p>{message}</p>
        <div className={styles.actions}>
          <button
            type="button"
            className={`${styles.button} ${styles.danger}`}
            onClick={onConfirm}
            disabled={busy}
          >
            {confirmLabel}
          </button>
          <button
            type="button"
            className={`${styles.button} ${styles.secondary}`}
            onClick={onCancel}
            disabled={busy}
          >
            Annulla
          </button>
        </div>
      </div>
    </div>
  );
}
