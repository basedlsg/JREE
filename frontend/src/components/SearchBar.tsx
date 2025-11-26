import { useState, FormEvent } from 'react';

interface SearchBarProps {
  onSearch: (query: string) => void;
  isLoading: boolean;
}

export function SearchBar({ onSearch, isLoading }: SearchBarProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSearch(query.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search for quotes..."
            disabled={isLoading}
            className="w-full px-4 py-3 bg-jre-dark border border-gray-700 rounded-lg
                       text-gray-100 placeholder-gray-500
                       focus:outline-none focus:border-jre-accent focus:ring-1 focus:ring-jre-accent
                       disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors"
          />
          {/* Search icon */}
          <svg
            className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>

        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="px-6 py-3 bg-jre-accent text-white font-medium rounded-lg
                     hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-jre-accent focus:ring-offset-2 focus:ring-offset-jre-darker
                     disabled:opacity-50 disabled:cursor-not-allowed
                     transition-colors"
        >
          {isLoading ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              Searching
            </span>
          ) : (
            'Search'
          )}
        </button>
      </div>
    </form>
  );
}
