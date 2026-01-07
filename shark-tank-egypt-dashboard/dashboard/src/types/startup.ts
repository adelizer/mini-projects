export interface Startup {
  id: string;
  name: string;
  name_ar?: string;
  episode_number: number;
  description: string;
  industry?: string;

  // Pitch details
  ask_amount?: number;
  ask_equity?: number;
  valuation?: number;

  // Deal outcome
  deal_made: boolean;
  deal_amount?: number;
  deal_equity?: number;
  sharks: string[];

  // Additional info
  website?: string;
  social_media?: Record<string, string>;
  founders: string[];
  screenshot_url?: string;

  // Source reference
  video_id: string;
  video_url: string;
  timestamp_start?: string;
}

export interface StartupFilters {
  search?: string;
  industry?: string;
  dealMade?: boolean | null;
  episode?: number;
}
