import type { QuoteResult } from '../types';

interface ResultCardProps {
  result: QuoteResult;
  rank: number;
}

export function ResultCard({ result, rank }: ResultCardProps) {
  const scorePercent = Math.round(result.score * 100);

  return (
    <div className="bg-jre-dark border border-gray-800 rounded-lg p-4 hover:border-gray-700 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex items-center gap-3">
          {/* Rank badge */}
          <span className="flex-shrink-0 w-7 h-7 bg-jre-accent/20 text-jre-accent text-sm font-bold rounded-full flex items-center justify-center">
            {rank}
          </span>

          {/* Episode info */}
          <div>
            <h3 className="font-medium text-gray-100">
              Episode #{result.episode_number}
            </h3>
            <p className="text-sm text-gray-400">{result.guest}</p>
          </div>
        </div>

        {/* Score badge */}
        <div className="flex-shrink-0 text-right">
          <div
            className={`text-sm font-medium ${
              scorePercent >= 80
                ? 'text-green-400'
                : scorePercent >= 60
                ? 'text-yellow-400'
                : 'text-gray-400'
            }`}
          >
            {scorePercent}% match
          </div>
        </div>
      </div>

      {/* Quote text */}
      <blockquote className="text-gray-300 leading-relaxed pl-4 border-l-2 border-gray-700">
        "{result.text}"
      </blockquote>

      {/* Footer */}
      <div className="mt-3 flex items-center gap-4 text-xs text-gray-500">
        <span className="truncate max-w-xs" title={result.episode_title}>
          {result.episode_title}
        </span>
        {result.timestamp && (
          <span className="flex-shrink-0">@ {result.timestamp}</span>
        )}
      </div>
    </div>
  );
}
