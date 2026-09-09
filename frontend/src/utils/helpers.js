import { CATEGORY_CONFIG } from "../constants/categoryConfig.js";

export function getPageTitle(page) {
  if (page === "overview") return "Overview";
  if (page === "digest") return "Daily Digest";
  if (page === "review") return "Review Queue";
  if (page === "evaluation") return "Evaluation";
  return page;
}

export function getCategoryClass(category) {
  const config = CATEGORY_CONFIG.find(
    (item) => item.name === category
  );
  return config?.color || "blue";
}

export function getConfidenceClass(confidence) {
  if (confidence === null || confidence === undefined) {
    return "neutral";
  }
  if (confidence < 60) return "low";
  if (confidence < 80) return "medium";
  return "high";
}

export function formatTime(value) {
  if (!value) return "TIME N/A";

  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return value;
  }
}
