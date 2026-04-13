export type RecommendationItem = {
  rank: number;
  restaurant_id: string;
  restaurant_name: string;
  cuisine: string[];
  rating: number;
  estimated_cost: number;
  currency: string;
  ai_explanation: string;
  cautions?: string | null;
};

export type RecommendationResponse = {
  request_id: string;
  summary?: string;
  top_recommendations: RecommendationItem[];
};

export type HistoryEntry = {
  created_at: string;
  request_id: string;
  location: string;
  budget_amount?: number;
  budget?: string;
  cuisine: string[];
  result_count: number;
  summary?: string;
};

export const STORAGE_KEY_HISTORY = "zomato_request_history";
