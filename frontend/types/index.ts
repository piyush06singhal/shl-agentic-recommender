export interface Recommendation {
  name: string;
  test_type: string;
  duration_mins: number;
  target_role?: string;
  target_level?: string[];
  skills?: string[];
  languages?: string[];
  competencies?: string[];
  description: string;
  url: string;
  reasoning?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  recommendations?: Recommendation[];
  isFailed?: boolean;
}

export interface HealthStatus {
  status: string;
  vector_db: string;
  catalog: string;
  llm: string;
  responseTime: number;
  environment: string;
}

export interface DebugInfo {
  conversationState: string;
  intent: string;
  extractedContext: string;
  decision: string;
  retrievedAssessments: string;
  similarityScores: string;
  metadataFilters: string;
  tokens: string;
  latency: number;
  rawResponse: string;
}
