export type RiskLevel = "low" | "medium" | "high";

export interface VehicleListing {
  vin: string | null;
  year: number | null;
  make: string | null;
  model: string | null;
  trim: string | null;
  body_style: string | null;
  drivetrain: string | null;
  engine: string | null;
  transmission: string | null;
  exterior_color: string | null;
  fuel: string | null;
  price: number | null;
  mileage: number | null;
  city: string | null;
  state: string | null;
  zip: string | null;
  dealer: string | null;
  primary_image: string | null;
  listing_url: string | null;
  carfax_url: string | null;
  accident_count: number | null;
  has_accidents: boolean | null;
  owner_count: number | null;
  one_owner: boolean | null;
  usage_type: string | null;
  created_at: string | null;
}

export interface ListingRiskAssessment {
  vin: string;
  risk_score: number;
  risk_level: RiskLevel;
  signals: string[];
  explanation: string;
}

export interface RankedVehicleSearchResult {
  rank: number;
  score: number;
  reason: string;
  risk: ListingRiskAssessment;
  listing: VehicleListing;
}

export interface NaturalSearchResponse {
  data: RankedVehicleSearchResult[];
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const isNullableNumber = (value: unknown): value is number | null =>
  value === null || (typeof value === "number" && Number.isFinite(value));

const isNullableString = (value: unknown): value is string | null =>
  value === null || typeof value === "string";

function isVehicleListing(value: unknown): value is VehicleListing {
  if (!isRecord(value)) return false;
  const stringFields: (keyof VehicleListing)[] = [
    "vin",
    "make",
    "model",
    "trim",
    "body_style",
    "drivetrain",
    "engine",
    "transmission",
    "exterior_color",
    "fuel",
    "city",
    "state",
    "zip",
    "dealer",
    "primary_image",
    "listing_url",
    "carfax_url",
    "usage_type",
    "created_at",
  ];
  const numberFields: (keyof VehicleListing)[] = [
    "year",
    "price",
    "mileage",
    "accident_count",
    "owner_count",
  ];
  return (
    stringFields.every((field) => isNullableString(value[field])) &&
    numberFields.every((field) => isNullableNumber(value[field])) &&
    (value.has_accidents === null || typeof value.has_accidents === "boolean") &&
    (value.one_owner === null || typeof value.one_owner === "boolean")
  );
}

function isRiskAssessment(value: unknown): value is ListingRiskAssessment {
  return (
    isRecord(value) &&
    typeof value.vin === "string" &&
    typeof value.risk_score === "number" &&
    Number.isFinite(value.risk_score) &&
    value.risk_score >= 0 &&
    value.risk_score <= 100 &&
    (value.risk_level === "low" ||
      value.risk_level === "medium" ||
      value.risk_level === "high") &&
    Array.isArray(value.signals) &&
    value.signals.every((signal) => typeof signal === "string") &&
    typeof value.explanation === "string"
  );
}

export function isNaturalSearchResponse(
  value: unknown,
): value is NaturalSearchResponse {
  return (
    isRecord(value) &&
    Array.isArray(value.data) &&
    value.data.every(
      (item) =>
        isRecord(item) &&
        Number.isInteger(item.rank) &&
        typeof item.score === "number" &&
        Number.isFinite(item.score) &&
        typeof item.reason === "string" &&
        isRiskAssessment(item.risk) &&
        isVehicleListing(item.listing),
    )
  );
}
