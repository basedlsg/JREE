import { useState, FormEvent, useRef, useEffect } from 'react';

interface SearchBarProps {
  onSearch: (query: string) => void;
  isLoading: boolean;
}

export function SearchBar({ onSearch, isLoading }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Focus input on mount
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSearch(query.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative">
      {/* Glow effect behind input */}
      <div
        className={`absolute inset-0 rounded-2xl transition-opacity duration-500 ${
          isFocused ? 'opacity-100' : 'opacity-0'
        }`}
        style={{
          background: 'radial-gradient(ellipse at center, rgba(255,68,68,0.15) 0%, transparent 70%)',
          filter: 'blur(20px)',
          transform: 'translateY(10px)',
        }}
      />

      {/* Main input container */}
      <div
        className={`relative glass-card p-2 transition-all duration-300 ${
          isFocused
            ? 'border-jre-accent/30 shadow-glow-sm'
            : 'border-white/[0.08]'
        }`}
      >
        <div className="flex items-center gap-3">
          {/* Search icon */}
          <div className="pl-4 flex items-center">
            <svg
              className={`w-5 h-5 transition-colors duration-200 ${
                isFocused ? 'text-jre-accent' : 'text-gray-500'
              }`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>

          {/* Input field */}
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder="Search for quotes, topics, or ideas..."
            disabled={isLoading}
            className="flex-1 py-4 bg-transparent border-none outline-none
                       text-lg text-white placeholder-gray-500
                       disabled:opacity-50 disabled:cursor-not-allowed"
          />

          {/* Clear button */}
          {query && !isLoading && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="p-2 rounded-lg hover:bg-white/5 text-gray-500 hover:text-gray-300 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}

          {/* Submit button */}
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="relative px-6 py-3 rounded-xl font-medium overflow-hidden
                       disabled:opacity-40 disabled:cursor-not-allowed
                       transition-all duration-300 group"
          >
            {/* Button background gradient */}
            <div className="absolute inset-0 bg-gradient-to-r from-jre-accent to-jre-purple opacity-100 group-hover:opacity-90 transition-opacity" />

            {/* Button glow on hover */}
            <div className="absolute inset-0 bg-gradient-to-r from-jre-accent to-jre-purple opacity-0 group-hover:opacity-50 blur-xl transition-opacity" />

            {/* Button content */}
            <span className="relative flex items-center gap-2 text-white">
              {isLoading ? (
                <>
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
                  <span>Searching</span>
                </>
              ) : (
                <>
                  <span>Search</span>
                  <svg
                    className="w-4 h-4 group-hover:translate-x-0.5 transition-transform"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M14 5l7 7m0 0l-7 7m7-7H3"
                    />
                  </svg>
                </>
              )}
            </span>
          </button>
        </div>
      </div>

      {/* Keyboard hint */}
      <div className="absolute -bottom-6 left-0 right-0 flex justify-center">
        <span className="text-xs text-gray-600 flex items-center gap-1.5">
          Press
          <kbd className="px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-gray-500 font-mono text-[10px]">
            Enter
          </kbd>
          to search
        </span>
      </div>
    </form>
  );
}
