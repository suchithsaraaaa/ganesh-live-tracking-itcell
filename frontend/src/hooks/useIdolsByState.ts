import { useEffect, useState, useCallback } from 'react';
import { Idol, ProcessionState } from '../types';
import { fetchIdols } from '../api/client';

const MAX_PAGES = 20; // safety cap (20 x 50 = 1000 rows) for jurisdiction-filtered state slices

export function useIdolsByState(state: ProcessionState) {
  const [idols, setIdols] = useState<Idol[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const all: Idol[] = [];
      let page = 1;
      let totalCount = 0;
      while (page <= MAX_PAGES) {
        const data = await fetchIdols({ procession_state: state, page });
        all.push(...data.results);
        totalCount = data.count;
        if (!data.next) break;
        page += 1;
      }
      setIdols(all);
      if (totalCount > all.length) {
        console.warn(`useIdolsByState(${state}): only loaded ${all.length} of ${totalCount} matching idols (safety cap reached)`);
      }
    } catch (err: any) {
      setError(err.message || `Failed to load ${state} idols`);
    } finally {
      setLoading(false);
    }
  }, [state]);

  useEffect(() => {
    load();
  }, [load]);

  return { idols, loading, error, reload: load };
}
