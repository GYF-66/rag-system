/**
 * Shared frontend types.
 */

export interface User {
  user_id: string;
  username: string;
  nickname?: string;
  avatar?: string;
  created_at?: string;
  updated_at?: string;
  last_login?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
  nickname?: string;
  avatar?: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ThinkingStepSummary {
  step_id?: number;
  step_name?: string;
  description?: string;
  reasoning?: string;
  duration_ms?: number;
  input_data?: Record<string, unknown>;
  output_data?: Record<string, unknown>;
}

export interface ReflectionResult {
  status: 'supported' | 'partially_supported' | 'not_supported' | 'skipped';
  confidence: number;
  issues: string[];
  revision_applied: boolean;
  duration_ms?: number;
}

export interface QueryRewriteMetadata {
  original_query?: string;
  normalized_query?: string;
  keywords?: string[];
  intents?: string[];
  variants?: string[];
}

export interface CragEvaluationDetails {
  similarity?: number;
  keyword_coverage?: number;
  diversity?: number;
  completeness?: number;
  reason?: string | null;
}

export interface CragCorrectionMetadata {
  corrected?: boolean;
  actions_taken?: string[];
}

export interface CragThresholdMetadata {
  low?: number;
  high?: number;
}

export interface CragEvaluation {
  mode?: 'online_heuristic';
  quality_score?: number | null;
  action?: 'accept' | 'refine' | 'reject' | 'skipped' | string | null;
  details?: CragEvaluationDetails | null;
  thresholds?: CragThresholdMetadata | null;
  correction_hints?: string[];
  correction?: CragCorrectionMetadata | null;
}

export interface SelfRagMetadata {
  mode?: 'llm_reflection';
  status?: 'waiting' | 'supported' | 'partially_supported' | 'not_supported' | 'skipped' | string | null;
  confidence?: number | null;
  issues_count?: number;
  revision_applied?: boolean;
  evidence_count?: number;
}

export interface ChatMetadata {
  request_id?: string;
  retrieval_method?: string;
  retrieval_variant_count?: number;
  retrieval_variants?: string[];
  query_rewrite?: QueryRewriteMetadata;
  rerank_method?: string;
  adaptive_route?: string;
  is_cross_query?: boolean;
  used_llm?: boolean;
  source_count?: number;
  total_duration_ms?: number;
  crag_evaluation?: CragEvaluation | null;
  hyde_used?: boolean;
  graph_rag_used?: boolean;
  cot_used?: boolean;
  self_rag_reflection?: ReflectionResult['status'] | null;
  self_rag?: SelfRagMetadata | null;
  [key: string]: unknown;
}

export interface ThinkingProcess {
  query_analysis?: ThinkingStepSummary;
  retrieval?: ThinkingStepSummary;
  reranking?: ThinkingStepSummary;
  reasoning?: ThinkingStepSummary;
  reflection?: ThinkingStepSummary | null;
  reflection_result?: ReflectionResult | null;
  summary?: string;
  total_duration_ms?: number;
}

export type ThinkingStepKey =
  | 'query_analysis'
  | 'retrieval'
  | 'reranking'
  | 'reasoning'
  | 'reflection';

export type ThinkingStepRunStatus = 'waiting' | 'streaming' | 'done' | 'warning';

export type ThinkingStepStatusMap = Partial<Record<ThinkingStepKey, ThinkingStepRunStatus>>;

export interface KnowledgeChunk {
  id: string;
  text: string;
  char_count: number;
  similarity?: number;
  rerank_score?: number;
  section?: string;
  title?: string;
  source_path?: string;
  document_id?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt?: string;
  sources?: KnowledgeChunk[];
  thinkingProcess?: ThinkingProcess;
  metadata?: ChatMetadata;
  perspectives?: PerspectiveResult[];
  graphContext?: GraphContext | null;
  streaming?: boolean;
  streamStatus?: 'idle' | 'streaming' | 'done' | 'error';
  thinkingProcessDraft?: Partial<ThinkingProcess>;
  streamedContent?: string;
  thinkingStatusMap?: ThinkingStepStatusMap;
}

export interface ChatHistory {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
}

export type HistoryGroup = {
  label: string;
  items: ChatHistory[];
};

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T = unknown> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  user_id?: string;
  use_rag?: boolean;
  enable_thinking?: boolean;
}

export interface GraphContextCourse {
  name: string;
  code: string;
  semester?: number;
}

export interface GraphContextRelationship {
  source: string;
  target: string;
  type: string;
}

export interface GraphContext {
  related_courses: GraphContextCourse[];
  related_concepts: string[];
  relationships: GraphContextRelationship[];
  node_count: number;
  edge_count: number;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  sources: KnowledgeChunk[];
  timestamp: string;
  message?: string;
  thinking_process?: ThinkingProcess;
  cross_reasoning?: string | null;
  is_cross_query?: boolean;
  graph_context?: GraphContext | null;
  metadata?: ChatMetadata;
}

export interface ChatStreamMetadataEvent {
  request_id?: string;
  contract_version?: number;
  event_types?: string[];
  session_id?: string;
  sources?: KnowledgeChunk[];
  graph_context?: GraphContext | null;
  metadata?: ChatMetadata;
}

export interface ChatStreamReflectionEvent extends ReflectionResult {
  request_id?: string;
}

export interface ChatStreamDoneEvent {
  request_id?: string;
  total_duration_ms?: number;
}

export interface ChatStreamEventMap {
  metadata: ChatStreamMetadataEvent;
  token: { content?: string };
  answer_replace: { content?: string };
  reflection: ChatStreamReflectionEvent;
  thinking: ThinkingProcess;
  done: ChatStreamDoneEvent;
  error: { message?: string; request_id?: string };
}

export interface SearchResult {
  query: string;
  results: KnowledgeChunk[];
  total_results: number;
}

export interface SessionInfo {
  session_id: string;
  user_id?: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface SessionDetail extends SessionInfo {
  messages: Array<{ role: string; content: string; timestamp: string }>;
}

export interface ApiError {
  detail?: string;
  error?: string;
  message?: string;
}

export interface Space {
  id: string;
  name: string;
  description?: string;
  icon: string;
  color: string;
  itemCount: number;
  updatedAt: string;
}

export interface SpaceCreate {
  name: string;
  description?: string;
  icon: string;
  color: string;
}

export interface SpaceListResponse {
  spaces: Space[];
  total: number;
}

export interface Suggestion {
  icon: string;
  text: string;
  description?: string;
}

export interface MessageBubbleProps {
  message: ChatMessage;
  showActions?: boolean;
}

export interface SkeletonProps {
  lines?: number;
  avatar?: boolean;
  animated?: boolean;
}

export interface ErrorBoundaryProps {
  title?: string;
  message?: string;
  retryable?: boolean;
}

// ============ 多视角 Agent 类型 ============

export interface PerspectiveStep {
  step: string;
  description: string;
  duration_ms?: number;
  output?: unknown;
}

export interface SupplementalSource {
  id: string;
  text: string;
  section: string;
  similarity?: number;
}

export interface PerspectiveResult {
  perspective: string;
  name: string;
  icon: string;
  tagline: string;
  response: string;
  duration_ms?: number;
  error?: string;
  steps?: PerspectiveStep[];
  supplemental_sources?: SupplementalSource[];
}

export interface PerspectiveChatRequest {
  message: string;
  session_id?: string;
  user_id?: string;
  use_rag?: boolean;
  perspectives?: string[];
}

export interface PerspectiveChatResponse {
  perspectives: PerspectiveResult[];
  session_id: string;
  sources: KnowledgeChunk[];
  timestamp: string;
  total_duration_ms: number;
  metadata?: ChatMetadata;
}

// ============ GraphRAG 知识图谱类型 ============

export interface GraphNode {
  id: string;
  label: string;
  type: 'course' | 'concept' | 'requirement' | 'indicator' | 'skill' | 'experiment' | string;
  community?: number;
  is_seed?: boolean;
  code?: string;
  semester?: string;
  category?: string;
  credits?: number;
  bloom_level?: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  label: string;
  weight?: number;
}

export interface GraphVisualizationData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  communities: Record<number, string>;
  stats: {
    node_count: number;
    edge_count: number;
    community_count: number;
    node_types: Record<string, number>;
  };
}

export interface GraphSearchResult {
  nodes: GraphNode[];
  edges: GraphEdge[];
  summary: string;
  paths: Array<{ from: string; to: string; path: string; length: number }>;
  seed_count: number;
  total_nodes: number;
  total_edges: number;
}

export interface LearningPathResult {
  path: Array<{
    id: string;
    name: string;
    code: string;
    semester: string;
    is_target: boolean;
  }>;
  description: string;
}

export interface AlignmentAnalysis {
  total_courses: number;
  total_concepts: number;
  total_requirements: number;
  requirement_coverage: Record<string, string[]>;
  gaps: Array<{ type: string; requirement: string; supporting_courses: string[]; severity: string; suggestion: string }>;
  overlaps: Array<{ type: string; concept: string; courses: string[]; count: number; suggestion: string }>;
  orphans: Array<{ type: string; course: string; suggestion: string }>;
  gap_count: number;
  overlap_count: number;
}
