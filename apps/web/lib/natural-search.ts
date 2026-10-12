import {
  isNaturalSearchResponse,
  type NaturalSearchResponse,
} from "@/lib/search-types";

const LOCAL_API_BASE_URL = "http://127.0.0.1:8000";

export async function searchNaturally(
  query: string,
): Promise<NaturalSearchResponse> {
  const configuredBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  const baseUrl = configuredBaseUrl
    ? configuredBaseUrl.replace(/\/+$/, "")
    : process.env.NODE_ENV === "development"
      ? LOCAL_API_BASE_URL
      : "";

  if (!baseUrl) {
    throw new Error("The search service is not configured. Please try again later.");
  }

  let response: Response;
  try {
    response = await fetch(`${baseUrl}/search/natural`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
  } catch {
    throw new Error(
      "We couldn’t reach AutoScout right now. Check that the search service is running and try again.",
    );
  }

  if (!response.ok) {
    throw new Error(
      "Your search couldn’t be completed right now. Please try again.",
    );
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new Error("The search service returned an unreadable response.");
  }

  if (!isNaturalSearchResponse(payload)) {
    throw new Error("The search service returned results in an unexpected format.");
  }

  return payload;
}
