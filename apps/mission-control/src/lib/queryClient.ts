import type { MissionControlDataSource } from "./api";

export interface QueryResult<T> {
  data: T;
  source: MissionControlDataSource;
}

export interface QueryClient {
  fetch<T>(key: string, loader: () => Promise<T>, fallbackData: T): Promise<QueryResult<T>>;
  clear(): void;
}

export function createQueryClient(): QueryClient {
  const cache = new Map<string, QueryResult<unknown>>();

  return {
    async fetch<T>(key: string, loader: () => Promise<T>, fallbackData: T): Promise<QueryResult<T>> {
      const cached = cache.get(key);
      if (cached) {
        return cached as QueryResult<T>;
      }

      try {
        const result: QueryResult<T> = {
          data: await loader(),
          source: "api",
        };
        cache.set(key, result as QueryResult<unknown>);
        return result;
      } catch {
        const result: QueryResult<T> = {
          data: fallbackData,
          source: "fixture",
        };
        cache.set(key, result as QueryResult<unknown>);
        return result;
      }
    },
    clear(): void {
      cache.clear();
    },
  };
}

export const queryClient = createQueryClient();
