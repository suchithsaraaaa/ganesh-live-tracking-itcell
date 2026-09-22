import React, { useEffect, useState } from 'react';
import { Search, FileDown, FileText } from 'lucide-react';
import { Idol } from '../types';
import { fetchIdols, getReportDownloadUrl } from '../api/client';
import { LoadingState, EmptyState, ErrorState } from '../components/shared/States';

export const ReportsPage: React.FC = () => {
  const [search, setSearch] = useState('');
  const [results, setResults] = useState<Idol[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    if (!search.trim()) {
      setResults([]);
      setSearched(false);
      return;
    }
    const timeout = setTimeout(() => {
      setLoading(true);
      setError(null);
      setSearched(true);
      fetchIdols({ search: search.trim() })
        .then((data) => setResults(data.results.slice(0, 20)))
        .catch((err) => setError(err.message || 'Failed to search GPID registry'))
        .finally(() => setLoading(false));
    }, 350);
    return () => clearTimeout(timeout);
  }, [search]);

  return (
    <div className="h-full flex flex-col overflow-hidden animate-fade-in-up">
      <div className="px-6 pt-6 pb-4">
        <h1 className="text-lg font-semibold text-text-primary">Reports</h1>
        <p className="text-xs text-text-tertiary mt-0.5">
          Generate the official operational PDF report for any registered GPID.
        </p>
      </div>

      <div className="px-6 pb-4">
        <div className="relative max-w-xl">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by GPID, idol name, association, police station…"
            autoFocus
            className="w-full pl-9 pr-3 py-2.5 bg-elevated-2 border border-border-default rounded-md text-text-primary text-sm mono focus:outline-none focus:border-accent"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 pb-6">
        {!searched && (
          <EmptyState
            title="Search for a GPID to generate its report"
            hint="Each report is generated live from the authoritative registry and tracking history."
          />
        )}
        {searched && loading && <LoadingState label="Searching registry…" />}
        {searched && !loading && error && <ErrorState message={error} />}
        {searched && !loading && !error && results.length === 0 && (
          <EmptyState title="No matching GPIDs found" />
        )}
        {searched && !loading && !error && results.length > 0 && (
          <div className="bg-elevated border border-border-subtle rounded-lg overflow-hidden max-w-3xl">
            {results.map((idol, i) => (
              <div
                key={idol.id}
                className={`flex items-center gap-3 px-4 py-3 ${i > 0 ? 'border-t border-border-subtle' : ''}`}
              >
                <FileText className="w-4 h-4 text-status-visarjan shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-text-primary mono">{idol.gpid}</div>
                  <div className="text-xs text-text-secondary truncate">
                    {idol.name} &bull; {idol.police_station}
                  </div>
                </div>
                <a
                  href={getReportDownloadUrl(idol.gpid)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-elevated-2 border border-border-default text-text-secondary hover:text-text-primary hover:border-accent/40 transition-colors shrink-0"
                >
                  <FileDown className="w-3.5 h-3.5" />
                  Download PDF
                </a>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
