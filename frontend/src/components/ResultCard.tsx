import { useState } from 'react';
import type { QuoteResult } from '../types';

interface ResultCardProps {
  result: QuoteResult;
  rank: number;
}

export function ResultCard({ result, rank }: ResultCardProps) {
  const [showContext, setShowContext] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const scorePercent = Math.round(result.score * 100);

  // Use highlight if available, otherwise use the first 150 chars of text
  const displayQuote = result.highlight || result.text.slice(0, 150) + (result.text.length > 150 ? '...' : '');

  // Check if there's additional context to show
  const hasMoreContext = result.text.length > (result.highlight?.length || 150);

  // Score color based on percentage
  const getScoreColor = () => {
    if (scorePercent >= 70) return 'from-green-500 to-emerald-500';
    if (scorePercent >= 50) return 'from-yellow-500 to-orange-500';
    return 'from-gray-500 to-gray-600';
  };

  const getScoreTextColor = () => {
    if (scorePercent >= 70) return 'text-green-400';
    if (scorePercent >= 50) return 'text-yellow-400';
    return 'text-gray-400';
  };

  return (
    <div
      className={`glass-card p-5 hover-lift transition-all duration-300 ${
        isHovered ? 'border-white/[0.15]' : ''
      }`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Top section with rank, episode info, and score */}
      <div className="flex items-start gap-4 mb-4">
        {/* Rank badge */}
        <div className="relative flex-shrink-0">
          <div
            className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold text-lg transition-all duration-300 ${
              rank === 1
                ? 'bg-gradient-to-br from-jre-accent to-jre-purple text-white shadow-glow-sm'
                : rank <= 3
                ? 'bg-gradient-to-br from-white/10 to-white/5 text-white border border-white/10'
                : 'bg-white/5 text-gray-400 border border-white/5'
            }`}
          >
            {rank}
          </div>
          {rank === 1 && (
            <div className="absolute -top-1 -right-1 w-4 h-4 bg-jre-gold rounded-full flex items-center justify-center">
              <svg className="w-2.5 h-2.5 text-black" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
            </div>
          )}
        </div>

        {/* Episode info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {result.episode_number > 0 ? (
              <h3 className="font-semibold text-white">
                Episode #{result.episode_number}
              </h3>
            ) : (
              <h3 className="font-medium text-gray-400">
                Episode Unknown
              </h3>
            )}
          </div>
          <p className="text-sm text-gray-400 flex items-center gap-2">
            <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            <span className="truncate">{result.guest}</span>
          </p>
        </div>

        {/* Score indicator */}
        <div className="flex-shrink-0 text-right">
          <div className={`text-lg font-bold ${getScoreTextColor()}`}>
            {scorePercent}%
          </div>
          <div className="mt-1 w-16 h-1.5 rounded-full bg-white/10 overflow-hidden">
            <div
              className={`h-full rounded-full bg-gradient-to-r ${getScoreColor()} transition-all duration-500`}
              style={{ width: `${scorePercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Quote section */}
      <div className="relative">
        {/* Quote icon */}
        <div className="absolute -left-1 -top-2 text-jre-accent/20 text-4xl font-serif">
          "
        </div>

        {/* Main quote */}
        <blockquote className="relative pl-6 py-3 border-l-2 border-gradient-to-b from-jre-accent to-jre-purple">
          <div
            className="absolute left-0 top-0 bottom-0 w-0.5 rounded-full"
            style={{
              background: 'linear-gradient(to bottom, #ff4444, #a855f7)',
            }}
          />
          <p className="text-gray-100 text-lg leading-relaxed font-light">
            {displayQuote}
          </p>
        </blockquote>
      </div>

      {/* Expandable context */}
      {hasMoreContext && (
        <div className="mt-3 ml-6">
          <button
            onClick={() => setShowContext(!showContext)}
            className="group flex items-center gap-2 text-sm text-gray-500 hover:text-gray-300 transition-colors"
          >
            <svg
              className={`w-4 h-4 transition-transform duration-200 ${
                showContext ? 'rotate-180' : ''
              }`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
            <span>{showContext ? 'Hide context' : 'Show full context'}</span>
          </button>

          {showContext && (
            <div className="mt-3 p-4 rounded-xl bg-white/[0.02] border border-white/5 animate-fade-in">
              <p className="text-sm text-gray-400 leading-relaxed">
                {result.text}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Footer with metadata and actions */}
      <div className="mt-4 pt-4 border-t border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span
            className="max-w-[200px] truncate"
            title={result.episode_title}
          >
            {result.episode_title !== `JRE - ${result.youtube_id}` ? result.episode_title : ''}
          </span>
          {result.timestamp && (
            <>
              <span className="text-gray-700">•</span>
              <span className="flex items-center gap-1">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {result.timestamp}
              </span>
            </>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          {result.youtube_id && (
            <a
              href={`https://www.youtube.com/watch?v=${result.youtube_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                       bg-white/5 hover:bg-white/10 border border-white/5 hover:border-white/10
                       text-xs text-gray-400 hover:text-white transition-all duration-200"
            >
              <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
              </svg>
              <span>Watch</span>
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
