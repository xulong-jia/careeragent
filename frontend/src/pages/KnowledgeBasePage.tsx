import { useEffect, useState } from "react";

import { MarkBadCasePanel } from "../components/MarkBadCasePanel";
import {
  answerRag,
  createRagDocument,
  deleteRagDocument,
  getRagAnswerRun,
  getRagDocument,
  indexRagDocument,
  listRagAnswerRuns,
  listRagChunks,
  listRagDocuments,
  searchRag,
} from "../api/rag";
import type {
  RagAnswerResult,
  RagAnswerRunRecord,
  RagCitation,
  RagChunkRecord,
  RagDocumentRecord,
  RagSearchResult,
  RagSearchSource,
  RagSourceRef,
} from "../types/api";

const sourceTypes = [
  "manual",
  "markdown",
  "text",
  "jd",
  "interview",
  "project",
  "learning",
  "company",
];

type KnowledgeBasePageProps = {
  onDocumentsChanged?: (documents: RagDocumentRecord[]) => void;
};

type GroundedFilter = "all" | "grounded" | "ungrounded";

type AnswerContractView = {
  answer_run_id?: string | null;
  answer: string;
  answer_type: string;
  grounded: boolean;
  uncertainty: string | null;
  evidence_summary: string[];
  citations: RagCitation[];
  source_refs: RagSourceRef[];
  retrieval_debug: Record<string, unknown>;
};

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

function previewText(value: string, maxLength = 120) {
  if (value.length <= maxLength) {
    return value;
  }
  return `${value.slice(0, maxLength - 3).trim()}...`;
}

function formatMetadata(metadata: Record<string, unknown>) {
  return JSON.stringify(metadata, null, 2);
}

function parseMetadata(value: string): Record<string, unknown> {
  const parsed = JSON.parse(value) as unknown;
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error("Metadata must be a JSON object.");
  }
  return parsed as Record<string, unknown>;
}

function SourceList({ sources }: { sources: RagSearchSource[] }) {
  if (!sources.length) {
    return (
      <div className="empty-state compact">
        <strong>暂无 sources</strong>
        <span>没有可展示的 citation。</span>
      </div>
    );
  }

  return (
    <div className="source-list">
      {sources.map((source) => (
        <article className="source-card" key={source.chunk_id}>
          <div className="source-card-header">
            <strong>{source.title}</strong>
            <span className="status-pill muted">score {source.score.toFixed(3)}</span>
          </div>
          <p className="snippet-text">{source.snippet}</p>
          <ul className="compact-list">
            <li>doc: {source.doc_id}</li>
            <li>chunk: {source.chunk_id}</li>
            <li>section: {source.section ?? "none"}</li>
          </ul>
          <pre className="json-preview compact">
            {formatMetadata(source.metadata)}
          </pre>
        </article>
      ))}
    </div>
  );
}

function CitationList({ citations }: { citations: RagCitation[] }) {
  if (!citations.length) {
    return (
      <div className="empty-state compact">
        <strong>暂无 citations</strong>
        <span>证据不足时不会生成引用。</span>
      </div>
    );
  }

  return (
    <div className="source-list">
      {citations.map((citation) => (
        <article className="source-card" key={citation.chunk_id}>
          <div className="source-card-header">
            <strong>{citation.label}</strong>
            <span className="status-pill muted">
              {citation.score === null ? "score n/a" : `score ${citation.score.toFixed(3)}`}
            </span>
          </div>
          <p className="snippet-text">{citation.snippet}</p>
          <ul className="compact-list">
            <li>document: {citation.document_id}</li>
            <li>chunk: {citation.chunk_id}</li>
            <li>source: {citation.source_type}</li>
          </ul>
          <pre className="json-preview compact">
            {formatMetadata(citation.metadata_preview)}
          </pre>
        </article>
      ))}
    </div>
  );
}

function SourceRefList({ sourceRefs }: { sourceRefs: RagSourceRef[] }) {
  if (!sourceRefs.length) {
    return (
      <div className="empty-state compact">
        <strong>暂无 source refs</strong>
        <span>证据不足时不会生成可复用引用。</span>
      </div>
    );
  }

  return (
    <div className="source-list">
      {sourceRefs.map((sourceRef) => (
        <article className="source-card" key={sourceRef.source_id}>
          <div className="source-card-header">
            <strong>{sourceRef.label}</strong>
            <span className="status-pill muted">{sourceRef.field}</span>
          </div>
          <p className="snippet-text">{sourceRef.preview}</p>
          <ul className="compact-list">
            <li>source: {sourceRef.source_type}</li>
            <li>source_id: {sourceRef.source_id}</li>
            <li>document: {sourceRef.document_id ?? "none"}</li>
            <li>chunk: {sourceRef.chunk_id ?? "none"}</li>
          </ul>
        </article>
      ))}
    </div>
  );
}

function AnswerContractPanel({
  result,
}: {
  result: AnswerContractView;
}) {
  return (
    <>
      <ul className="activity-list">
        <li>
          <strong>Grounded</strong>
          <span className={result.grounded ? "status-pill" : "status-pill muted"}>
            {result.grounded ? "grounded" : "ungrounded"}
          </span>
        </li>
        <li>
          <strong>Uncertainty</strong>
          <span>{result.uncertainty ?? "none"}</span>
        </li>
        <li>
          <strong>Answer Type</strong>
          <span>{result.answer_type}</span>
        </li>
        <li>
          <strong>Answer Run</strong>
          <span>{result.answer_run_id ?? "not persisted"}</span>
        </li>
        <li>
          <strong>Citations</strong>
          <span>{result.citations.length}</span>
        </li>
        <li>
          <strong>Source Refs</strong>
          <span>{result.source_refs.length}</span>
        </li>
      </ul>
      <pre className="json-preview text-preview">
        {result.answer || "没有找到足够来源。"}
      </pre>
      {result.evidence_summary.length ? (
        <>
          <h4>Evidence Summary</h4>
          <ul className="compact-list">
            {result.evidence_summary.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      ) : (
        <div className="empty-state compact">
          <strong>暂无 evidence summary</strong>
          <span>证据不足或无来源时不会生成摘要。</span>
        </div>
      )}
      <h4>Citations</h4>
      <CitationList citations={result.citations} />
      <h4>Source Refs</h4>
      <SourceRefList sourceRefs={result.source_refs} />
      <details className="json-details">
        <summary>Retrieval debug</summary>
        <pre className="json-preview compact">
          {JSON.stringify(result.retrieval_debug, null, 2)}
        </pre>
      </details>
    </>
  );
}

export function KnowledgeBasePage({
  onDocumentsChanged,
}: KnowledgeBasePageProps) {
  const [documents, setDocuments] = useState<RagDocumentRecord[]>([]);
  const [selectedDocument, setSelectedDocument] =
    useState<RagDocumentRecord | null>(null);
  const [chunks, setChunks] = useState<RagChunkRecord[]>([]);
  const [title, setTitle] = useState("Synthetic Career Notes");
  const [sourceType, setSourceType] = useState("manual");
  const [rawText, setRawText] = useState(
    "FastAPI services need stable contracts, pytest coverage, and source-backed interview preparation.",
  );
  const [metadataText, setMetadataText] = useState(
    '{\n  "tags": ["synthetic", "backend"],\n  "topic": "interview",\n  "domain": "career"\n}',
  );
  const [searchQuery, setSearchQuery] = useState("FastAPI interview");
  const [searchTopK, setSearchTopK] = useState(5);
  const [searchSourceType, setSearchSourceType] = useState("");
  const [searchResult, setSearchResult] = useState<RagSearchResult | null>(null);
  const [question, setQuestion] = useState("How should I prepare for FastAPI interviews?");
  const [answerTopK, setAnswerTopK] = useState(5);
  const [answerSourceType, setAnswerSourceType] = useState("");
  const [answerResult, setAnswerResult] = useState<RagAnswerResult | null>(null);
  const [answerRuns, setAnswerRuns] = useState<RagAnswerRunRecord[]>([]);
  const [selectedAnswerRun, setSelectedAnswerRun] =
    useState<RagAnswerRunRecord | null>(null);
  const [groundedFilter, setGroundedFilter] = useState<GroundedFilter>("all");
  const [uncertaintyFilter, setUncertaintyFilter] = useState("");
  const [retrievalModeFilter, setRetrievalModeFilter] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  const refreshDocuments = async () => {
    const response = await listRagDocuments();
    setDocuments(response.items);
    onDocumentsChanged?.(response.items);
    return response.items;
  };

  const loadDocument = async (docId: string) => {
    const [document, chunkList] = await Promise.all([
      getRagDocument(docId),
      listRagChunks({ docId }),
    ]);
    setSelectedDocument(document);
    setChunks(chunkList.items);
  };

  const refreshAnswerRuns = async () => {
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const response = await listRagAnswerRuns({
        grounded:
          groundedFilter === "all" ? null : groundedFilter === "grounded",
        uncertainty: uncertaintyFilter || null,
        retrievalMode: retrievalModeFilter || null,
      });
      setAnswerRuns(response.items);
      if (
        selectedAnswerRun &&
        !response.items.some(
          (item) => item.answer_run_id === selectedAnswerRun.answer_run_id,
        )
      ) {
        setSelectedAnswerRun(null);
      }
      return response.items;
    } catch (error) {
      setHistoryError(
        error instanceof Error ? error.message : "Answer history 加载失败。",
      );
      return [];
    } finally {
      setHistoryLoading(false);
    }
  };

  const loadAnswerRunDetail = async (answerRunId: string) => {
    setDetailLoading(true);
    setDetailError(null);
    try {
      const detail = await getRagAnswerRun(answerRunId);
      setSelectedAnswerRun(detail);
    } catch (error) {
      setDetailError(
        error instanceof Error ? error.message : "Answer run detail 加载失败。",
      );
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const items = await refreshDocuments();
        if (items[0]) {
          await loadDocument(items[0].doc_id);
        }
        await refreshAnswerRuns();
      } catch (error) {
        setErrorMessage(
          error instanceof Error ? error.message : "Knowledge Base 加载失败。",
        );
      }
    };
    void loadInitialData();
  }, []);

  const handleCreate = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const metadata = parseMetadata(metadataText);
      const document = await createRagDocument({
        title,
        source_type: sourceType,
        source_uri: null,
        raw_text: rawText,
        metadata,
      });
      const items = await refreshDocuments();
      setSelectedDocument(document);
      setChunks([]);
      onDocumentsChanged?.(items);
      setStatusMessage("Document created. Index it before search or answer.");
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Document 创建失败。",
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleIndex = async () => {
    if (!selectedDocument) {
      setErrorMessage("请先选择 document。");
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const result = await indexRagDocument(selectedDocument.doc_id, {
        max_chars: 1200,
        overlap_chars: 0,
      });
      await refreshDocuments();
      await loadDocument(selectedDocument.doc_id);
      setStatusMessage(`Indexed ${result.chunk_count} chunks.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Index 失败。");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!window.confirm("Delete this RAG document and its chunks?")) {
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      await deleteRagDocument(docId);
      const items = await refreshDocuments();
      if (selectedDocument?.doc_id === docId) {
        const nextDocument = items[0] ?? null;
        setSelectedDocument(nextDocument);
        if (nextDocument) {
          await loadDocument(nextDocument.doc_id);
        } else {
          setChunks([]);
        }
      }
      setStatusMessage("Document deleted. Existing answer runs keep safe refs only.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Document 删除失败。");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const result = await searchRag({
        query: searchQuery,
        top_k: searchTopK,
        filters: searchSourceType ? { source_type: searchSourceType } : null,
      });
      setSearchResult(result);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Search 失败。");
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnswer = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const result = await answerRag({
        question,
        top_k: answerTopK,
        filters: answerSourceType ? { source_type: answerSourceType } : null,
      });
      setAnswerResult(result);
      const items = await refreshAnswerRuns();
      if (result.answer_run_id) {
        const persisted = items.find(
          (item) => item.answer_run_id === result.answer_run_id,
        );
        if (persisted) {
          setSelectedAnswerRun(persisted);
        }
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Answer 失败。");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="page-stack" aria-labelledby="knowledge-title">
      <div className="page-heading">
        <p className="eyebrow">RAG</p>
        <h2 id="knowledge-title">Knowledge Base</h2>
        <p>阶段 3F 前端最小 UI：创建 synthetic document、index chunks、search sources，并查看 deterministic answer。</p>
      </div>

      <article className="panel warning-panel">
        <div>
          <h3>安全边界</h3>
          <p>当前仅建议输入 synthetic text。不要输入真实简历、真实 JD、投递记录、面试复盘或 API Key。</p>
          <p>当前 RAG 是 deterministic lexical retrieval + deterministic answer，不接真实 LLM、embedding 或 vector store。</p>
        </div>
        <span className="status-pill">Preview only</span>
      </article>

      {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
      {statusMessage ? <p className="hint-text">{statusMessage}</p> : null}

      <div className="two-column wide-left">
        <article className="panel">
          <div className="panel-header">
            <h3>Create Document</h3>
            <span className="status-pill muted">POST /api/rag/documents</span>
          </div>
          <div className="form-stack">
            <label>
              Title
              <input value={title} onChange={(event) => setTitle(event.target.value)} />
            </label>
            <label>
              Source Type
              <select value={sourceType} onChange={(event) => setSourceType(event.target.value)}>
                {sourceTypes.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Raw text
              <textarea
                className="jd-textarea"
                value={rawText}
                onChange={(event) => setRawText(event.target.value)}
              />
            </label>
            <label>
              Metadata JSON
              <textarea
                className="metadata-textarea"
                value={metadataText}
                onChange={(event) => setMetadataText(event.target.value)}
              />
            </label>
            <button className="primary-action" disabled={isLoading} onClick={handleCreate} type="button">
              Create document
            </button>
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Documents</h3>
            <span className="status-pill">{documents.length} items</span>
          </div>
          {documents.length ? (
            <ul className="activity-list rag-document-list">
              {documents.map((document) => (
                <li
                  className={
                    selectedDocument?.doc_id === document.doc_id ? "selected-row" : undefined
                  }
                  key={document.doc_id}
                >
                  <div>
                    <strong>{document.title}</strong>
                    <small>{document.doc_id}</small>
                  </div>
                  <span>{document.source_type}</span>
                  <span>{document.index_status}</span>
                  <span>{document.chunk_count} chunks</span>
                  <button
                    className="ghost-action"
                    onClick={() => void loadDocument(document.doc_id)}
                    type="button"
                  >
                    Select
                  </button>
                  <button
                    className="ghost-action"
                    disabled={isLoading}
                    onClick={() => void handleDeleteDocument(document.doc_id)}
                    type="button"
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty-state">
              <strong>暂无 documents</strong>
              <span>创建 synthetic document 后会显示在这里。</span>
            </div>
          )}
        </article>
      </div>

      <div className="two-column">
        <article className="panel">
          <div className="panel-header">
            <h3>Document Detail</h3>
            <span className="status-pill muted">{selectedDocument?.index_status ?? "None"}</span>
          </div>
          {selectedDocument ? (
            <>
              <ul className="activity-list">
                <li>
                  <strong>Title</strong>
                  <span>{selectedDocument.title}</span>
                </li>
                <li>
                  <strong>Source Type</strong>
                  <span>{selectedDocument.source_type}</span>
                </li>
                <li>
                  <strong>Created</strong>
                  <span>{formatDate(selectedDocument.created_at)}</span>
                </li>
              </ul>
              <pre className="json-preview text-preview">{selectedDocument.raw_text_preview}</pre>
              <pre className="json-preview compact">{formatMetadata(selectedDocument.metadata)}</pre>
              <MarkBadCasePanel
                defaultCategory="irrelevant_rag_source"
                defaultTitle="RAG document review"
                key={selectedDocument.doc_id}
                sourceId={selectedDocument.doc_id}
                sourceType="rag_document"
              />
              <p className="hint-text">
                Document 和 chunk 仅展示短 preview；删除 document 会移除 chunks，answer history 只保留安全 refs。
              </p>
              <button className="primary-action" disabled={isLoading} onClick={handleIndex} type="button">
                Index document
              </button>
            </>
          ) : (
            <div className="empty-state">
              <strong>未选择 document</strong>
              <span>选择 document 后查看 preview 和 metadata。</span>
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Chunks</h3>
            <span className="status-pill">{chunks.length} items</span>
          </div>
          {chunks.length ? (
            <div className="source-list">
              {chunks.map((chunk) => (
                <article className="source-card" key={chunk.chunk_id}>
                  <div className="source-card-header">
                    <strong>{chunk.section ?? `Chunk ${chunk.chunk_index}`}</strong>
                    <span className="status-pill muted">{chunk.token_count} tokens</span>
                  </div>
                  <p className="snippet-text">{chunk.text_preview}</p>
                  <pre className="json-preview compact">{formatMetadata(chunk.metadata)}</pre>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <strong>暂无 chunks</strong>
              <span>Index document 后会显示 text preview。</span>
            </div>
          )}
        </article>
      </div>

      <div className="two-column">
        <article className="panel">
          <div className="panel-header">
            <h3>Search</h3>
            <span className="status-pill muted">POST /api/rag/search</span>
          </div>
          <div className="form-stack">
            <label>
              Query
              <input value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} />
            </label>
            <label>
              Top K
              <input
                min="1"
                max="20"
                type="number"
                value={searchTopK}
                onChange={(event) => setSearchTopK(Number(event.target.value))}
              />
            </label>
            <label>
              Source Type Filter
              <select value={searchSourceType} onChange={(event) => setSearchSourceType(event.target.value)}>
                <option value="">Any</option>
                {sourceTypes.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <button className="primary-action" disabled={isLoading} onClick={handleSearch} type="button">
              Search
            </button>
          </div>
          {searchResult ? (
            <>
              <p className="hint-text">
                {searchResult.uncertainty ?? `${searchResult.sources.length} sources`}
              </p>
              <SourceList sources={searchResult.sources} />
            </>
          ) : null}
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Answer</h3>
            <span className="status-pill muted">Deterministic</span>
          </div>
          <div className="form-stack">
            <label>
              Question
              <input value={question} onChange={(event) => setQuestion(event.target.value)} />
            </label>
            <label>
              Top K
              <input
                min="1"
                max="20"
                type="number"
                value={answerTopK}
                onChange={(event) => setAnswerTopK(Number(event.target.value))}
              />
            </label>
            <label>
              Source Type Filter
              <select value={answerSourceType} onChange={(event) => setAnswerSourceType(event.target.value)}>
                <option value="">Any</option>
                {sourceTypes.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <button className="primary-action" disabled={isLoading} onClick={handleAnswer} type="button">
              Answer
            </button>
          </div>
          {answerResult ? (
            <>
              <AnswerContractPanel result={answerResult} />
              <MarkBadCasePanel
                defaultCategory="unsupported_answer"
                defaultTitle="RAG answer review"
                key={answerResult.answer_run_id ?? answerResult.sources[0]?.doc_id ?? "rag_answer_no_source"}
                sourceId={answerResult.answer_run_id ?? answerResult.sources[0]?.doc_id ?? "rag_answer_no_source"}
                sourceType={answerResult.answer_run_id ? "rag_answer" : answerResult.sources[0] ? "rag_document" : "other"}
              />
              <SourceList sources={answerResult.sources} />
            </>
          ) : null}
        </article>
      </div>

      <div className="two-column wide-left">
        <article className="panel">
          <div className="panel-header">
            <h3>Answer History</h3>
            <span className="status-pill muted">GET /api/rag/answers</span>
          </div>
          <div className="form-grid">
            <label>
              Grounded
              <select
                value={groundedFilter}
                onChange={(event) => setGroundedFilter(event.target.value as GroundedFilter)}
              >
                <option value="all">All</option>
                <option value="grounded">Grounded</option>
                <option value="ungrounded">Ungrounded</option>
              </select>
            </label>
            <label>
              Uncertainty
              <select
                value={uncertaintyFilter}
                onChange={(event) => setUncertaintyFilter(event.target.value)}
              >
                <option value="">All</option>
                <option value="grounded">grounded</option>
                <option value="no_relevant_source">no_relevant_source</option>
                <option value="insufficient_evidence">insufficient_evidence</option>
              </select>
            </label>
            <label>
              Retrieval Mode
              <select
                value={retrievalModeFilter}
                onChange={(event) => setRetrievalModeFilter(event.target.value)}
              >
                <option value="">All</option>
                <option value="deterministic_lexical">lexical</option>
              </select>
            </label>
          </div>
          <button
            className="ghost-action"
            disabled={historyLoading}
            onClick={() => void refreshAnswerRuns()}
            type="button"
          >
            Refresh history
          </button>
          {historyError ? <p className="error-text">{historyError}</p> : null}
          {historyLoading ? <p className="hint-text">Loading answer history...</p> : null}
          {!historyLoading && answerRuns.length ? (
            <ul className="activity-list rag-document-list">
              {answerRuns.map((answerRun) => (
                <li
                  className={
                    selectedAnswerRun?.answer_run_id === answerRun.answer_run_id
                      ? "selected-row"
                      : undefined
                  }
                  key={answerRun.answer_run_id}
                >
                  <div>
                    <strong>{answerRun.answer_run_id}</strong>
                    <small>{previewText(answerRun.question)}</small>
                  </div>
                  <span>{answerRun.grounded ? "grounded" : "ungrounded"}</span>
                  <span>{answerRun.uncertainty}</span>
                  <span>{answerRun.retrieval_mode}</span>
                  <span>{answerRun.citations.length} citations</span>
                  <span>{formatDate(answerRun.created_at)}</span>
                  <button
                    className="ghost-action"
                    disabled={detailLoading}
                    onClick={() => void loadAnswerRunDetail(answerRun.answer_run_id)}
                    type="button"
                  >
                    Detail
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          {!historyLoading && !answerRuns.length ? (
            <div className="empty-state">
              <strong>暂无 answer runs</strong>
              <span>运行 persisted answer 后会显示历史记录。</span>
            </div>
          ) : null}
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>Answer Run Detail</h3>
            <span className="status-pill muted">
              {selectedAnswerRun?.answer_run_id ?? "None"}
            </span>
          </div>
          {detailError ? <p className="error-text">{detailError}</p> : null}
          {detailLoading ? <p className="hint-text">Loading answer run detail...</p> : null}
          {selectedAnswerRun ? (
            <>
              <ul className="activity-list">
                <li>
                  <strong>Question</strong>
                  <span>{selectedAnswerRun.question}</span>
                </li>
                <li>
                  <strong>Created</strong>
                  <span>{formatDate(selectedAnswerRun.created_at)}</span>
                </li>
                <li>
                  <strong>Top K</strong>
                  <span>{selectedAnswerRun.top_k}</span>
                </li>
              </ul>
              <AnswerContractPanel result={selectedAnswerRun} />
            </>
          ) : (
            <div className="empty-state">
              <strong>未选择 answer run</strong>
              <span>选择历史记录后查看 grounded answer contract。</span>
            </div>
          )}
        </article>
      </div>
    </section>
  );
}
