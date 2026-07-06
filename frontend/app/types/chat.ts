export interface Message {
  id: string;
  sender: "user" | "bot";
  type: "factual" | "refusal" | "security" | "error";
  text: string;
  citations?: string[];
  sourceUrl?: string;
  timestamp: string;
}

export interface HealthStatus {
  status: "healthy" | "offline" | "checking";
  engine: string;
}
