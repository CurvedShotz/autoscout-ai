export function SearchSkeleton() {
  return (
    <div className="skeleton-list" aria-label="Loading vehicle results">
      {[0, 1, 2].map((item) => (
        <div className="skeleton-card" key={item}>
          <div className="skeleton-image shimmer" />
          <div className="skeleton-content">
            <div className="skeleton-line shimmer skeleton-short" />
            <div className="skeleton-line shimmer skeleton-title" />
            <div className="skeleton-line shimmer skeleton-medium" />
            <div className="skeleton-block shimmer" />
          </div>
        </div>
      ))}
    </div>
  );
}
