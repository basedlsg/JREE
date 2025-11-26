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
    <div className="min-h-screen bg-jre-darker">
      {/* Header */}
      <header className="bg-jre-dark border-b border-gray-800">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-center">
            <span className="text-jre-accent">JRE</span>{' '}
            <span className="text-gray-100">Quote Search</span>
          </h1>
          <p className="text-gray-400 text-center mt-2">
            Search through Joe Rogan Experience podcast transcripts
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Search Bar */}
        <SearchBar onSearch={handleSearch} isLoading={isLoading} />

        {/* Error Message */}
        {error && (
          <div className="mt-6 p-4 bg-red-900/30 border border-red-800 rounded-lg text-red-200">
            {error}
          </div>
        )}

        {/* Results Info */}
        {!isLoading && lastQuery && !error && (
          <div className="mt-6 text-gray-400 text-sm">
            {results.length > 0 ? (
              <span>
                Found {results.length} results for "{lastQuery}" in{' '}
                {searchTime?.toFixed(0)}ms
              </span>
            ) : (
              <span>No results found for "{lastQuery}"</span>
            )}
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="mt-8 flex justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-jre-accent"></div>
          </div>
        )}

        {/* Results */}
        {!isLoading && results.length > 0 && (
          <div className="mt-6 space-y-4">
            {results.map((result, index) => (
              <ResultCard key={result.chunk_id} result={result} rank={index + 1} />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !lastQuery && (
          <div className="mt-16 text-center text-gray-500">
            <p className="text-lg">Enter a search query to find quotes</p>
            <p className="mt-2 text-sm">
              Try searching for topics like "consciousness", "aliens", or "comedy"
            </p>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-auto py-8 text-center text-gray-600 text-sm">
        <p>Powered by Cohere embeddings and Pinecone vector search</p>
      </footer>
    </div>
  );
}

export default App;
