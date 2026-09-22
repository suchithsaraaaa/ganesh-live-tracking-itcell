import { useEffect, useState, useCallback } from 'react';
import { Assignment } from '../types';
import { fetchAssignments } from '../api/client';

const MAX_PAGES = 10; // safety cap — jurisdiction-filtered lists are expected to be small

export function useAssignments() {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const all: Assignment[] = [];
      let page = 1;
      // The list endpoint isn't jurisdiction-scoped down to a handful of rows for
      // MAIN_OFFICER/ACP, so page through it (bounded) rather than assuming one page.
      // eslint-disable-next-line no-constant-condition
      while (page <= MAX_PAGES) {
        const data = await fetchAssignments(page);
        all.push(...data.results);
        if (!data.next) break;
        page += 1;
      }
      setAssignments(all);
    } catch (err: any) {
      setError(err.message || 'Failed to load assignment records');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { assignments, loading, error, reload: load };
}
