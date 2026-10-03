"use client";

import Image from "next/image";
import { useState } from "react";
import type { RankedVehicleSearchResult } from "@/lib/search-types";

interface VehicleResultCardProps {
  result: RankedVehicleSearchResult;
}

function formatPrice(price: number | null): string {
  if (price === null) return "Price not listed";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(price);
}

function formatMileage(mileage: number | null): string | null {
  if (mileage === null) return null;
  return `${new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
  }).format(mileage)} mi`;
}

function safeWebUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:"
      ? url.toString()
      : null;
  } catch {
    return null;
  }
}

function VehicleImage({
  src,
  label,
}: {
  src: string | null;
  label: string;
}) {
  const [failed, setFailed] = useState(false);
  const safeSrc = safeWebUrl(src);

  if (!safeSrc || failed) {
    return (
      <div className="vehicle-image-fallback" role="img" aria-label={label}>
        <svg viewBox="0 0 120 72" aria-hidden="true">
          <path d="m20 47 8-18c1-3 4-5 7-5h43c4 0 7 2 9 6l9 17" />
          <path d="M16 47h87v10H16zM33 24l-6 23m50-23 10 23" />
          <circle cx="34" cy="57" r="8" />
          <circle cx="84" cy="57" r="8" />
        </svg>
        <span>Image unavailable</span>
      </div>
    );
  }

  return (
    <Image
      src={safeSrc}
      alt={label}
      fill
      unoptimized
      sizes="(max-width: 700px) 100vw, 360px"
      className="vehicle-image"
      onError={() => setFailed(true)}
    />
  );
}

export function VehicleResultCard({ result }: VehicleResultCardProps) {
  const { listing, risk } = result;
  const title = [listing.year, listing.make, listing.model]
    .filter((part) => part !== null)
    .join(" ");
  const vehicleTitle = title || "Vehicle details unavailable";
  const location = [listing.city, listing.state].filter(Boolean).join(", ");
  const listingUrl = safeWebUrl(listing.listing_url);
  const carfaxUrl = safeWebUrl(listing.carfax_url);
  const riskClass = `risk-${risk.risk_level}`;

  const details = [
    formatMileage(listing.mileage),
    listing.drivetrain,
    listing.fuel,
    listing.transmission,
    listing.exterior_color,
  ].filter((value): value is string => Boolean(value));

  return (
    <article className="vehicle-card">
      <div className="vehicle-card-topline">
        <span className="rank-label">
          <span className="rank-number">{String(result.rank).padStart(2, "0")}</span>
          Ranked match
        </span>
        {listing.vin && <span className="vin-label">VIN {listing.vin}</span>}
      </div>

      <div className="vehicle-card-main">
        <div className="vehicle-photo">
          <VehicleImage src={listing.primary_image} label={vehicleTitle} />
          {listing.body_style && (
            <span className="photo-tag">{listing.body_style}</span>
          )}
        </div>

        <div className="vehicle-details">
          <div className="vehicle-heading">
            <div>
              <p className="vehicle-kicker">
                {listing.trim || listing.make || "Vehicle"}
              </p>
              <h3>{vehicleTitle}</h3>
            </div>
            <p className="vehicle-price">{formatPrice(listing.price)}</p>
          </div>

          <div className="vehicle-facts">
            {details.length > 0 ? (
              details.map((detail) => (
                <span className="fact-chip" key={detail}>
                  {detail}
                </span>
              ))
            ) : (
              <span className="muted-fact">Additional specifications unavailable</span>
            )}
          </div>

          {(location || listing.dealer) && (
            <div className="dealer-row">
              {location && (
                <span className="dealer-location">
                  <svg viewBox="0 0 16 16" aria-hidden="true">
                    <path d="M13 6.7c0 3.5-5 7.3-5 7.3S3 10.2 3 6.7a5 5 0 1 1 10 0Z" />
                    <circle cx="8" cy="6.5" r="1.6" />
                  </svg>
                  {location}
                </span>
              )}
              {listing.dealer && <span>{listing.dealer}</span>}
            </div>
          )}

          <div className="insight-grid">
            <section className="insight-panel match-panel" aria-label="Match details">
              <div className="insight-heading">
                <span className="insight-icon match-icon" aria-hidden="true">
                  <svg viewBox="0 0 20 20">
                    <path d="m4 10 4 4 8-8" />
                  </svg>
                </span>
                <span>Match</span>
                <strong>{Math.round(result.score)}<small> / 100</small></strong>
              </div>
              <p>{result.reason}</p>
            </section>

            <section
              className={`insight-panel risk-panel ${riskClass}`}
              aria-label="Listing risk assessment"
            >
              <div className="insight-heading">
                <span className="insight-icon risk-icon" aria-hidden="true">
                  <svg viewBox="0 0 20 20">
                    <path d="M10 2.5 17 5v4.8c0 4-2.8 6.6-7 8.2-4.2-1.6-7-4.2-7-8.2V5l7-2.5Z" />
                    <path d="M10 6.5v4m0 2.5h.01" />
                  </svg>
                </span>
                <span>Listing risk</span>
                <strong>
                  {risk.risk_score}
                  <small> / 100 · {risk.risk_level}</small>
                </strong>
              </div>
              {risk.signals.length > 0 && (
                <ul className="risk-signals">
                  {risk.signals.map((signal, index) => (
                    <li key={`${signal}-${index}`}>{signal}</li>
                  ))}
                </ul>
              )}
              <p>{risk.explanation}</p>
            </section>
          </div>

          {(listingUrl || carfaxUrl) && (
            <div className="listing-actions">
              {listingUrl && (
                <a
                  className="view-listing-button"
                  href={listingUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`View ${vehicleTitle} listing in a new tab`}
                >
                  View listing
                  <svg viewBox="0 0 16 16" aria-hidden="true">
                    <path d="M6 3h7v7m0-7L6 10" />
                    <path d="M11 9v4H3V5h4" />
                  </svg>
                </a>
              )}
              {carfaxUrl && (
                <a
                  className="carfax-link"
                  href={carfaxUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`View vehicle history for ${vehicleTitle} in a new tab`}
                >
                  Vehicle history
                  <svg viewBox="0 0 16 16" aria-hidden="true">
                    <path d="M6 3h7v7m0-7L6 10" />
                    <path d="M11 9v4H3V5h4" />
                  </svg>
                </a>
              )}
            </div>
          )}
        </div>
      </div>
    </article>
  );
}
