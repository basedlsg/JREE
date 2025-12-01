import { useState } from 'react';
import { SearchBar } from './components/SearchBar';
import { ResultCard } from './components/ResultCard';
import type { QuoteResult, SearchResponse } from './types';

function App() {
  const [results, setResults] = useState<QuoteResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTime, setSearchTime] = useState<number | null>(null);
  const [lastQuery, setLastQuery] = useState<string>('');
  const [totalIndexed] = useState(743046);

  const handleSearch = async (query: string) => {
    if (!query.trim()) return;

    setIsLoading(true);
    setError(null);
    setLastQuery(query);

    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query,
          top_k: 10,
        }),
      });

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }

      const data: SearchResponse = await response.json();
      setResults(data.results);
      setSearchTime(data.search_time_ms);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Animated background orbs */}
      <div className="bg-orb bg-orb-1" />
      <div className="bg-orb bg-orb-2" />
      <div className="bg-orb bg-orb-3" />

      {/* Noise overlay for texture */}
      <div className="noise-overlay" />

      {/* Main content */}
      <div className="relative z-10">
        {/* Hero Header */}
        <header className="pt-16 pb-8 px-4">
          <div className="max-w-4xl mx-auto text-center">
            {/* Logo/Icon */}
            <div className="mb-6 inline-flex items-center justify-center">
              <div className="relative">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-jre-accent to-jre-purple flex items-center justify-center shadow-glow">
                  <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                  </svg>
                </div>
                <div className="absolute -inset-1 bg-gradient-to-r from-jre-accent to-jre-purple rounded-2xl blur opacity-30 animate-pulse-slow" />
              </div>
            </div>

            {/* Title */}
            <h1 className="text-5xl md:text-6xl font-bold mb-4 tracking-tight">
              <span className="gradient-text">JRE</span>{' '}
              <span className="text-white">Quote Search</span>
            </h1>

            {/* Subtitle */}
            <p className="text-lg text-gray-400 max-w-xl mx-auto leading-relaxed">
              Semantic search through{' '}
              <span className="text-white font-medium">{totalIndexed.toLocaleString()}</span>{' '}
              moments from Joe Rogan Experience podcasts
            </p>

            {/* Stats badges */}
            <div className="mt-6 flex items-center justify-center gap-4 flex-wrap">
              <div className="glass-card px-4 py-2 flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-sm text-gray-300">2,327 Episodes</span>
              </div>
              <div className="glass-card px-4 py-2 flex items-center gap-2">
                <svg className="w-4 h-4 text-jre-accent" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
                </svg>
                <span className="text-sm text-gray-300">AI-Powered</span>
              </div>
            </div>
          </div>
        </header>

        {/* Search Section */}
        <main className="max-w-4xl mx-auto px-4 pb-16">
          {/* Search Bar */}
          <div className="mb-8">
            <SearchBar onSearch={handleSearch} isLoading={isLoading} />
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-6 glass-card p-4 border-red-500/30 bg-red-500/10 animate-scale-in">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center flex-shrink-0">
                  <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="font-medium text-red-300">Search Error</p>
                  <p className="text-sm text-red-400/80">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Results Info */}
          {!isLoading && lastQuery && !error && (
            <div className="mb-6 flex items-center justify-between animate-fade-in">
              <div className="flex items-center gap-3">
                {results.length > 0 ? (
                  <>
                    <div className="flex items-center gap-2 text-gray-400">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span>
                        <span className="text-white font-medium">{results.length}</span> results
                      </span>
                    </div>
                    <span className="text-gray-600">•</span>
                    <span className="text-gray-500 text-sm">
                      {(searchTime! / 1000).toFixed(2)}s
                    </span>
                  </>
                ) : (
                  <span className="text-gray-400">No results for "{lastQuery}"</span>
                )}
              </div>
              <div className="text-sm text-gray-500 hidden sm:block">
                Searching: "<span className="text-gray-400">{lastQuery}</span>"
              </div>
            </div>
          )}

          {/* Loading State */}
          {isLoading && (
            <div className="space-y-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="glass-card p-6" style={{ animationDelay: `${i * 100}ms` }}>
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 rounded-xl skeleton" />
                    <div className="flex-1 space-y-3">
                      <div className="h-4 w-1/4 rounded skeleton" />
                      <div className="h-3 w-1/3 rounded skeleton" />
                      <div className="h-16 w-full rounded skeleton mt-4" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Results */}
          {!isLoading && results.length > 0 && (
            <div className="space-y-4">
              {results.map((result, index) => (
                <div key={result.chunk_id} className="result-enter">
                  <ResultCard result={result} rank={index + 1} />
                </div>
              ))}
            </div>
          )}

          {/* Empty State */}
          {!isLoading && !lastQuery && (
            <div className="text-center py-16 animate-fade-in">
              <div className="mb-6 inline-flex items-center justify-center">
                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-white/5 to-white/[0.02] border border-white/10 flex items-center justify-center">
                  <svg className="w-10 h-10 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
              </div>
              <h3 className="text-xl font-medium text-gray-300 mb-2">
                Start exploring
              </h3>
              <p className="text-gray-500 max-w-md mx-auto mb-8">
                Search for topics, ideas, or quotes from thousands of JRE episodes
              </p>

              {/* Suggested searches */}
              <div className="flex flex-wrap items-center justify-center gap-2">
                <span className="text-sm text-gray-600">Try:</span>
                {['consciousness', 'simulation theory', 'discipline', 'comedy', 'aliens'].map((term) => (
                  <button
                    key={term}
                    onClick={() => handleSearch(term)}
                    className="px-3 py-1.5 text-sm glass-card hover:bg-white/[0.08]
                             text-gray-400 hover:text-white transition-all duration-200
                             hover:border-jre-accent/30"
                  >
                    {term}
                  </button>
                ))}
              </div>
            </div>
          )}
        </main>

        {/* Footer */}
        <footer className="py-8 border-t border-white/5">
          <div className="max-w-4xl mx-auto px-4 text-center">
            <p className="text-sm text-gray-600">
              Powered by semantic embeddings and vector search
            </p>
            <div className="mt-3 flex items-center justify-center gap-4">
              <span className="text-xs text-gray-700 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500/50" />
                ChromaDB
              </span>
              <span className="text-xs text-gray-700 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500/50" />
                Sentence Transformers
              </span>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}

export default App;
