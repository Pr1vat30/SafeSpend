/** Mirrors the backend response envelope (backend/app/api/dto/common/response.py). */
export interface APIResponse<T> {
  success: boolean;
  message: string | null;
  error: string | null;
  data: T | null;
}
