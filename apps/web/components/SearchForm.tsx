"use client";

import { FormEvent } from "react";

interface SearchFormProps {
  query: string;
  isLoading: boolean;
  onQueryChange: (query: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

export function SearchForm({
  query,
  isLoading,
  onQueryChange,
  onSubmit,
}: SearchFormProps) {
  return (
    <form className="search-form" onSubmit={onSubmit}>
      <label className="sr-only" htmlFor="vehicle-query">
        Describe the car you’re looking for
      </label>
      <textarea
        id="vehicle-query"
        name="query"
        rows={2}
        maxLength={500}
        placeholder="Find me a reliable sporty sedan near Dallas under $25k with low mileage"
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
        disabled={isLoading}
        required
      />
      <div className="search-form-footer">
        <span className="input-hint">
          Be as specific or as broad as you like
        </span>
        <button
          className="search-button"
          type="submit"
          disabled={isLoading || !query.trim()}
        >
          {isLoading ? (
            <>
              <span className="button-spinner" aria-hidden="true" />
              Searching
            </>
          ) : (
            <>
              Find my car
              <svg viewBox="0 0 20 20" aria-hidden="true">
                <path d="M4 10h11M10 5l5 5-5 5" />
              </svg>
            </>
          )}
        </button>
      </div>
    </form>
  );
}
