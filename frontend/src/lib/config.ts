/**
 * Dynamically resolves the API base URL depending on the environment.
 * If running on a deployed site (not localhost/127.0.0.1), it redirects to the Render backend.
 * Checks for process.env.NEXT_PUBLIC_API_URL and ignores the placeholder in render.yaml if present.
 */
export function getApiBaseUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  const isPlaceholder = envUrl && envUrl.includes("your-backend-service-url");

  if (envUrl && !isPlaceholder) {
    return envUrl;
  }

  // Check if we are running in the browser and not on localhost/127.0.0.1
  if (typeof window !== "undefined") {
    const hostname = window.location.hostname;
    const isLocal = 
      hostname === "localhost" || 
      hostname === "127.0.0.1" || 
      hostname.startsWith("192.168.") || 
      hostname.startsWith("10.") || 
      hostname.endsWith(".local");

    if (!isLocal) {
      return "https://tournai-backend.onrender.com/api";
    }
  }

  return "http://localhost:8000/api";
}
