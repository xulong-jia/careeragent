import { useEffect, useState } from "react";

import {
  answerRag,
  createRagDocument,
  getRagDocument,
  indexRagDocument,
  listRagChunks,
  listRagDocuments,
  searchRag,
} from "../api/rag";
import type {
  RagAnswerResult,
  RagChunkRecord,
  RagDocumentRecord,
  RagSearchResult,
  RagSearchSource,
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

function formatDate(value: string) {
  return new Date(value).toLocaleString();
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
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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

  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const items = await refreshDocuments();
        if (items[0]) {
          await loadDocument(items[0].doc_id);
        }
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
              <ul className="activity-list">
                <li>
                  <strong>Grounded</strong>
                  <span>{answerResult.grounded ? "true" : "false"}</span>
                </li>
                <li>
                  <strong>Uncertainty</strong>
                  <span>{answerResult.uncertainty ?? "none"}</span>
                </li>
                <li>
                  <strong>Answer Type</strong>
                  <span>{answerResult.answer_type}</span>
                </li>
              </ul>
              <pre className="json-preview text-preview">
                {answerResult.answer || "没有找到足够来源。"}
              </pre>
              <SourceList sources={answerResult.sources} />
            </>
          ) : null}
        </article>
      </div>
    </section>
  );
}
