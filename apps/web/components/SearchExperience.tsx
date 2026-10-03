"use client";

import { FormEvent, useRef, useState } from "react";
import Link from "next/link";
import { SearchForm } from "@/components/SearchForm";
import { SearchSkeleton } from "@/components/SearchSkeleton";
import { VehicleResultCard } from "@/components/VehicleResultCard";
import { searchNaturally } from "@/lib/natural-search";
import type { RankedVehicleSearchResult } from "@/lib/search-types";

const SUGGESTED_SEARCHES = [
  "Reliable hybrid under $20k",
  "Sporty sedan near Dallas",
  "Low-mileage SUV for a family",
];

export function SearchExperience() {
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [results, setResults] = useState<RankedVehicleSearchResult[] | null>(
    null,
  );
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const searchLock = useRef(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const searchQuery = query.trim();
    if (!searchQuery || searchLock.current) return;

    searchLock.current = true;
    setIsLoading(true);
    setError("");
    setResults(null);
    setSubmittedQuery(searchQuery);

    try {
      const response = await searchNaturally(searchQuery);
      setResults(response.data);
    } catch (searchError) {
      setError(
        searchError instanceof Error
          ? searchError.message
          : "Something went wrong. Please try your search again.",
      );
    } finally {
      searchLock.current = false;
      setIsLoading(false);
    }
  }

  return (
    <main>
      <header className="site-header">
        <Link className="brand" href="/" aria-label="AutoScout home">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 36 36">
              <path d="M8 25.5 13.5 10h9L28 25.5M11 19h14M16.5 10l-2 15.5m7-15.5 2 15.5" />
            </svg>
          </span>
          <span>auto<span>scout</span></span>
        </Link>
        <div className="header-note">
          <span className="status-dot" />
          A clearer way to find your next car
        </div>
      </header>

      <section className="hero-section" aria-labelledby="hero-title">
        <div className="hero-copy">
          <p className="eyebrow">
            <span className="eyebrow-line" />
            Your next car, found with clarity
          </p>
          <h1 id="hero-title">
            The right car
            <br />
            <span>starts with a feeling.</span>
          </h1>
          <p className="hero-description">
            Tell us what matters to you. We’ll search real listings and surface
            the details that make each one worth a closer look.
          </p>
        </div>

        <div className="search-shell">
          <div className="search-shell-label">
            <span className="search-orbit" aria-hidden="true">
              <svg viewBox="0 0 20 20">
                <circle cx="8.8" cy="8.8" r="5.8" />
                <path d="m13.2 13.2 4 4" />
              </svg>
            </span>
            <span>Describe your ideal car</span>
            <span className="natural-language-tag">Natural language</span>
          </div>
          <SearchForm
            query={query}
            isLoading={isLoading}
            onQueryChange={setQuery}
            onSubmit={handleSubmit}
          />
          <div className="suggestions" aria-label="Suggested searches">
            <span className="suggestions-label">Try</span>
            {SUGGESTED_SEARCHES.map((suggestion) => (
              <button
                className="suggestion-chip"
                key={suggestion}
                type="button"
                onClick={() => setQuery(suggestion)}
                disabled={isLoading}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
        <div className="hero-footnote">
          <span aria-hidden="true">✳</span>
          Real listings. Thoughtful matches. A little more peace of mind.
        </div>
      </section>

      <section className="results-section" aria-live="polite" aria-busy={isLoading}>
        {isLoading && (
          <>
            <div className="results-heading">
              <div>
                <p className="eyebrow">A moment while we look</p>
                <h2>Finding your matches</h2>
                <p className="results-query">“{submittedQuery}”</p>
              </div>
              <span className="loading-label">
                <span className="loading-pulse" />
                Searching live listings
              </span>
            </div>
            <SearchSkeleton />
          </>
        )}

        {!isLoading && error && (
          <div className="message-card error-card" role="alert">
            <span className="message-icon" aria-hidden="true">!</span>
            <div>
              <h2>We couldn’t complete that search</h2>
              <p>{error}</p>
            </div>
            <button
              className="retry-button"
              type="button"
              onClick={() => void handleSubmitFromButton()}
            >
              Try again
            </button>
          </div>
        )}

        {!isLoading && !error && results && results.length === 0 && (
          <div className="message-card empty-card">
            <span className="empty-car-icon" aria-hidden="true">
              <svg viewBox="0 0 48 32">
                <path d="m6 21 4-11c.6-1.5 2-2.5 3.7-2.5h20.6c1.7 0 3.1 1 3.7 2.5l4 11" />
                <path d="M4 20h40v7H4z" />
                <circle cx="13" cy="27" r="3" />
                <circle cx="35" cy="27" r="3" />
              </svg>
            </span>
            <p className="eyebrow">A quiet moment in the market</p>
            <h2>No matches just yet</h2>
            <p>
              Try broadening your budget, location, or vehicle description and
              we’ll take another look.
            </p>
          </div>
        )}

        {!isLoading && !error && results && results.length > 0 && (
          <>
            <div className="results-heading">
              <div>
                <p className="eyebrow">Your shortlist</p>
                <h2>
                  {results.length} {results.length === 1 ? "car" : "cars"} worth
                  a look
                </h2>
                <p className="results-query">For “{submittedQuery}”</p>
              </div>
              <span className="results-live-tag">
                <span className="status-dot" />
                Live listings
              </span>
            </div>
            <div className="result-list">
              {results.map((result) => (
                <VehicleResultCard
                  key={`${result.listing.vin ?? "vehicle"}-${result.rank}`}
                  result={result}
                />
              ))}
            </div>
          </>
        )}
      </section>

      <footer className="site-footer">
        <span>AutoScout</span>
        <span>Make the next one a good one.</span>
        <a
          href="https://www.openstreetmap.org/copyright"
          target="_blank"
          rel="noopener noreferrer"
        >
          Geocoding data © OpenStreetMap contributors
        </a>
      </footer>
    </main>
  );

  async function handleSubmitFromButton() {
    if (!submittedQuery || searchLock.current) return;
    setQuery(submittedQuery);
    searchLock.current = true;
    setIsLoading(true);
    setError("");
    setResults(null);
    try {
      const response = await searchNaturally(submittedQuery);
      setResults(response.data);
    } catch (searchError) {
      setError(
        searchError instanceof Error
          ? searchError.message
          : "Something went wrong. Please try your search again.",
      );
    } finally {
      searchLock.current = false;
      setIsLoading(false);
    }
  }
}
